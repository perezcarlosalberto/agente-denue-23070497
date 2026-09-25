"""Parte A · Las cuatro herramientas sobre el DENUE.

El modelo NUNCA ve el CSV. Solo ve DECLARACIONES (al final de este archivo) y
puede PEDIR una de estas cuatro herramientas; el codigo de agente.ejecutar la
corre y le devuelve el diccionario que resulte:

    buscar_actividades(texto)                 que clases SCIAN hay para un giro
    contar(**filtros)                         cuantos establecimientos
    ranking(por, top=5, **filtros)            de mayor a menor, agrupando por una columna
    listar(limite=10, **filtros)              algunos establecimientos con nombre

Un argumento invalido lanza ErrorHerramienta; agente.ejecutar la convierte en
{"ok": False, "error": ..., "valores_validos": ...} para que el modelo corrija.
Ninguna excepcion llega al modelo.
"""
import re
import unicodedata

import pandas as pd

FUENTE = "DENUE 05/2026, INEGI"

MUNICIPIOS = ["Tampico", "Ciudad Madero"]

# De menor a mayor: el indice sirve para ordenar "del estrato mayor al menor".
ESTRATOS = [
    "0 a 5 personas",
    "6 a 10 personas",
    "11 a 30 personas",
    "31 a 50 personas",
    "51 a 100 personas",
    "101 a 250 personas",
    "251 y más personas",
]

POR_VALIDOS = ["municipio", "colonia", "sector", "codigo_act", "estrato"]
FILTROS = ["municipio", "codigo_act", "sector", "estrato", "colonia"]

MAX_ACTIVIDADES = 15    # buscar_actividades devuelve a lo mas 15 clases
MAX_SUGERENCIAS = 10    # colonias parecidas cuando la colonia no se encuentra
TOP_MIN, TOP_MAX = 1, 20
LIMITE_MIN, LIMITE_MAX = 1, 20


class ErrorHerramienta(Exception):
    """Argumento invalido. agente.ejecutar la convierte en un error estructurado."""

    def __init__(self, mensaje, valores_validos=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.valores_validos = valores_validos


# --------------------------------------------------------------------------
# 6.1 normalizar y cargar_datos
# --------------------------------------------------------------------------

def normalizar(texto):
    """Minusculas, sin acentos y con los espacios colapsados.

    " Cafeterías, Neverías" -> "cafeterias, neverias"
    NFKD separa cada letra de su acento ("í" -> "i" + acento) y el acento, que
    no es ASCII, se descarta. La "ñ" queda como "n".
    """
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return " ".join(texto.split())


def cargar_datos(ruta_denue, ruta_sectores):
    """Lee los dos CSV como texto y devuelve (DataFrame, {sector: nombre}).

    dtype=str: si pandas convirtiera codigo_act en numero, startswith dejaria
    de funcionar. keep_default_na=False: una celda vacia queda como "" y no
    como NaN. colonia_norm y actividad_norm se calculan UNA vez aqui para no
    normalizar 22,900 filas en cada consulta.
    """
    datos = pd.read_csv(ruta_denue, dtype=str, keep_default_na=False)
    datos["colonia_norm"] = datos["colonia"].map(normalizar)
    datos["actividad_norm"] = datos["actividad"].map(normalizar)

    tabla = pd.read_csv(ruta_sectores, dtype=str, keep_default_na=False)
    sectores = dict(zip(tabla["sector"], tabla["nombre_sector"]))
    return datos, sectores


# --------------------------------------------------------------------------
# Ayudas para buscar_actividades
# --------------------------------------------------------------------------

def _quitar_plural(palabra):
    """Plurales sencillos: hospitales -> hospital, farmacias -> farmacia."""
    if len(palabra) > 5 and palabra.endswith("es"):
        return palabra[:-2]
    if len(palabra) > 4 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def palabras_de_busqueda(texto):
    """Las palabras de 3 letras o mas del texto, normalizadas y sin plural."""
    palabras = re.findall(r"[a-z0-9]+", normalizar(texto))
    return [_quitar_plural(p) for p in palabras if len(p) >= 3]


# --------------------------------------------------------------------------
# Las herramientas
# --------------------------------------------------------------------------

class Herramientas:
    def __init__(self, datos, sectores):
        self.datos = datos
        self.sectores = sectores

    # ------------------------------------------------------ filtros comunes
    def _filtrar(self, municipio=None, codigo_act=None, sector=None, estrato=None, colonia=None):
        """Aplica a la vez (y logico) los filtros que no sean None.

        Devuelve (filas, filtros) donde `filtros` son los valores YA
        corregidos: "Ciudad Madero" aunque haya llegado "ciudad madero".
        La colonia se aplica al final, despues de los demas filtros.
        """
        filas = self.datos
        filtros = {}

        if municipio is not None:
            buscado = normalizar(municipio)
            validos = {normalizar(m): m for m in MUNICIPIOS}
            if buscado not in validos:
                raise ErrorHerramienta("municipio no válido: '%s'." % municipio, MUNICIPIOS)
            filtros["municipio"] = validos[buscado]
            filas = filas[filas["municipio"] == validos[buscado]]

        if codigo_act is not None:
            codigos = [c.strip() for c in str(codigo_act).split(",")]
            for c in codigos:
                if not (c.isdigit() and 2 <= len(c) <= 6):
                    raise ErrorHerramienta(
                        "codigo_act no válido: '%s'. Cada código debe tener solo dígitos, "
                        "de 2 a 6, separados por coma (ej. '464111,464112' o '7225')." % c)
            filtros["codigo_act"] = ",".join(codigos)
            filas = filas[filas["codigo_act"].str.startswith(tuple(codigos))]

        if sector is not None:
            if str(sector) not in self.sectores:
                raise ErrorHerramienta("sector no válido: '%s'." % sector, list(self.sectores))
            filtros["sector"] = str(sector)
            filas = filas[filas["sector"] == str(sector)]

        if estrato is not None:
            buscado = normalizar(estrato)
            validos = {normalizar(e): e for e in ESTRATOS}
            if buscado not in validos:
                raise ErrorHerramienta("estrato no válido: '%s'." % estrato, ESTRATOS)
            filtros["estrato"] = validos[buscado]
            filas = filas[filas["estrato"] == validos[buscado]]

        if colonia is not None:
            buscada = normalizar(colonia)
            coinciden = filas[filas["colonia_norm"] == buscada]
            if coinciden.empty:
                # Sugerencias SOLO entre las filas que ya cumplen los demas
                # filtros: las que mas establecimientos tienen primero.
                parecidas = filas[filas["colonia_norm"].str.contains(buscada, regex=False)]
                conteo = parecidas.groupby("colonia").size().reset_index(name="n")
                conteo = conteo.sort_values(["n", "colonia"], ascending=[False, True])
                raise ErrorHerramienta(
                    "No hay establecimientos en la colonia '%s' que cumplan los demás filtros. "
                    "La colonia puede estar escrita de otra forma: revisa valores_validos "
                    "(colonias que contienen ese texto)." % colonia,
                    conteo["colonia"].head(MAX_SUGERENCIAS).tolist())
            filtros["colonia"] = sorted(set(coinciden["colonia"]))[0]
            filas = coinciden

        return filas, filtros

    # ------------------------------------------------------ buscar_actividades
    def buscar_actividades(self, texto):
        """Hasta 15 clases SCIAN cuyo nombre contiene TODAS las palabras del texto.

        Cuenta en ambos municipios, de mas a menos establecimientos. Sin
        coincidencias devuelve una lista vacia, no un error.
        """
        palabras = palabras_de_busqueda(texto)
        if not palabras:
            raise ErrorHerramienta(
                "texto no válido: '%s'. Escribe al menos una palabra de 3 letras o más "
                "(ej. 'farmacia', 'tacos', 'hotel')." % texto)

        filas = self.datos
        for palabra in palabras:
            filas = filas[filas["actividad_norm"].str.contains(palabra, regex=False)]

        conteo = filas.groupby(["codigo_act", "actividad"]).size().reset_index(name="establecimientos")
        conteo = conteo.sort_values(["establecimientos", "codigo_act"], ascending=[False, True])
        actividades = [
            {"codigo_act": fila.codigo_act, "actividad": fila.actividad,
             "establecimientos": int(fila.establecimientos)}
            for fila in conteo.head(MAX_ACTIVIDADES).itertuples()
        ]
        return {"ok": True, "fuente": FUENTE, "actividades": actividades}

    # ------------------------------------------------------ contar
    def contar(self, municipio=None, codigo_act=None, sector=None, estrato=None, colonia=None):
        """Numero de establecimientos que cumplen los filtros. Sin filtros, todo el archivo."""
        filas, filtros = self._filtrar(municipio, codigo_act, sector, estrato, colonia)
        return {"ok": True, "fuente": FUENTE, "filtros": filtros, "total": int(len(filas))}

    # ------------------------------------------------------ ranking
    def ranking(self, por, top=5, municipio=None, codigo_act=None, sector=None, estrato=None):
        """Agrupa por una columna y ordena de mayor a menor. No acepta colonia como filtro."""
        if por not in POR_VALIDOS:
            raise ErrorHerramienta("por no válido: '%s'." % por, POR_VALIDOS)
        top = _entero_en_rango("top", top, TOP_MIN, TOP_MAX)

        filas, filtros = self._filtrar(municipio, codigo_act, sector, estrato)

        conteo = filas.groupby(por).size().reset_index(name="total")
        conteo = conteo.sort_values(["total", por], ascending=[False, True])

        salida = []
        for valor, total in zip(conteo[por].head(top), conteo["total"].head(top)):
            fila = {"valor": valor, "total": int(total)}
            if por == "codigo_act":
                fila["actividad"] = filas.loc[filas["codigo_act"] == valor, "actividad"].iloc[0]
            if por == "sector":
                fila["nombre_sector"] = self.sectores.get(valor, "")
            salida.append(fila)

        return {"ok": True, "fuente": FUENTE, "por": por, "filtros": filtros,
                "total_filtrado": int(len(filas)), "filas": salida}

    # ------------------------------------------------------ listar
    def listar(self, limite=10, municipio=None, codigo_act=None, sector=None, estrato=None, colonia=None):
        """Algunos establecimientos, del estrato mayor al menor y, dentro del estrato, por nombre."""
        if all(f is None for f in (municipio, codigo_act, sector, estrato, colonia)):
            raise ErrorHerramienta("listar exige al menos un filtro.", FILTROS)
        limite = _entero_en_rango("limite", limite, LIMITE_MIN, LIMITE_MAX)

        filas, filtros = self._filtrar(municipio, codigo_act, sector, estrato, colonia)

        orden = filas.assign(
            _estrato=filas["estrato"].map(ESTRATOS.index),
            _id=filas["id"].astype(int),
        ).sort_values(["_estrato", "nombre", "_id"], ascending=[False, True, True])

        establecimientos = [
            {"id": f.id, "nombre": f.nombre, "actividad": f.actividad,
             "estrato": f.estrato, "colonia": f.colonia, "municipio": f.municipio}
            for f in orden.head(limite).itertuples()
        ]
        return {"ok": True, "fuente": FUENTE, "filtros": filtros, "total": int(len(filas)),
                "mostrados": len(establecimientos), "establecimientos": establecimientos}


def _entero_en_rango(nombre, valor, minimo, maximo):
    """Convierte a entero y, si queda fuera de [minimo, maximo], lo ajusta al limite."""
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        raise ErrorHerramienta("%s debe ser un número entero de %d a %d." % (nombre, minimo, maximo))
    return max(minimo, min(maximo, valor))


# --------------------------------------------------------------------------
# 6.4 Las declaraciones: lo UNICO que el modelo sabe de las herramientas
# --------------------------------------------------------------------------

_MUNICIPIO = {
    "type": "string",
    "enum": MUNICIPIOS,
    "description": "'Tampico' o 'Ciudad Madero'. Omítelo para contar en ambos municipios.",
}
_CODIGO_ACT = {
    "type": "string",
    "description": (
        "Uno o varios códigos SCIAN separados por coma, sin espacios ('464111,464112'). "
        "Cada código funciona como PREFIJO: '7225' incluye todas las clases que empiezan "
        "con 7225. Obtén los códigos con buscar_actividades y pon TODAS las clases del giro "
        "en este mismo argumento; no uses un prefijo corto sin revisar qué clases incluye."
    ),
}
_SECTOR = {
    "type": "string",
    "description": (
        "Sector SCIAN exacto: dos dígitos ('46', '72') o '31-33' y '48-49'. "
        "Para un giro concreto usa codigo_act, no sector."
    ),
}
_ESTRATO = {
    "type": "string",
    "enum": ESTRATOS,
    "description": "Rango de personal ocupado. El DENUE no tiene el número exacto de empleados.",
}
_COLONIA = {
    "type": "string",
    "description": (
        "Nombre exacto de la colonia (sin importar mayúsculas ni acentos). Los nombres se "
        "capturaron a mano: si no existe, el error trae en valores_validos colonias parecidas; "
        "no adivines."
    ),
}

DECLARACIONES = [
    {
        "name": "buscar_actividades",
        "description": (
            "Busca clases de actividad SCIAN por palabras de su nombre. Devuelve hasta 15 "
            "{codigo_act, actividad, establecimientos} de ambos municipios juntos, de más a "
            "menos establecimientos. Úsala SIEMPRE antes de contar un giro para conocer sus "
            "códigos. Busca con palabras del nombre oficial ('farmacia', 'tacos', 'belleza'); "
            "si no hay resultados, prueba sinónimos o una palabra más general. Los "
            "establecimientos que devuelve suman ambos municipios: para un municipio usa contar."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "texto": {"type": "string",
                          "description": "Una o más palabras de 3 letras o más; se exigen todas."},
            },
            "required": ["texto"],
        },
    },
    {
        "name": "contar",
        "description": (
            "Cuenta establecimientos que cumplen TODOS los filtros dados. Sin filtros cuenta "
            "todo el conjunto (ambos municipios). Devuelve total y los filtros aplicados."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "municipio": _MUNICIPIO,
                "codigo_act": _CODIGO_ACT,
                "sector": _SECTOR,
                "estrato": _ESTRATO,
                "colonia": _COLONIA,
            },
        },
    },
    {
        "name": "ranking",
        "description": (
            "Agrupa los establecimientos que cumplen los filtros por una columna y devuelve "
            "los grupos de mayor a menor: filas {valor, total}, más 'actividad' si por es "
            "codigo_act y 'nombre_sector' si por es sector; también total_filtrado. Úsala para "
            "'cuáles son las N...', '¿dónde hay más...?', o para desglosar un total. "
            "No acepta el filtro colonia."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "por": {"type": "string", "enum": POR_VALIDOS,
                        "description": "Columna por la que se agrupa."},
                "top": {"type": "integer",
                        "description": "Cuántos grupos devolver, de 1 a 20 (por omisión 5)."},
                "municipio": _MUNICIPIO,
                "codigo_act": _CODIGO_ACT,
                "sector": _SECTOR,
                "estrato": _ESTRATO,
            },
            "required": ["por"],
        },
    },
    {
        "name": "listar",
        "description": (
            "Lista establecimientos concretos {id, nombre, actividad, estrato, colonia, "
            "municipio}, del estrato mayor al menor y, dentro del estrato, por nombre. Exige al "
            "menos un filtro. Devuelve también total (cuántos cumplen) y mostrados."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limite": {"type": "integer",
                           "description": "Cuántos mostrar, de 1 a 20 (por omisión 10)."},
                "municipio": _MUNICIPIO,
                "codigo_act": _CODIGO_ACT,
                "sector": _SECTOR,
                "estrato": _ESTRATO,
                "colonia": _COLONIA,
            },
        },
    },
]
