"""Parte F · Las respuestas esperadas, calculadas con pandas ANTES de la corrida real.

    python -m evaluacion.calcular_esperadas

No importa NADA de app/: si una herramienta tuviera un error, una esperada
calculada con ella tendria el mismo error y la evaluacion no lo veria. Aqui
cada cifra sale de una consulta directa de pandas sobre el CSV.

Escribe evaluacion/esperadas.json e imprime cada cifra con la consulta que la
produjo, para verificarla a mano.
"""
import json

import pandas as pd

RUTA_DENUE = "data/denue_tampico_madero.csv"
RUTA_SECTORES = "data/sectores_scian.csv"
RUTA_SALIDA = "evaluacion/esperadas.json"

d = pd.read_csv(RUTA_DENUE, dtype=str, keep_default_na=False)
sectores = pd.read_csv(RUTA_SECTORES, dtype=str, keep_default_na=False)
tampico = d[d["municipio"] == "Tampico"]
madero = d[d["municipio"] == "Ciudad Madero"]

esperadas = []


def agregar(esperada, consulta):
    esperadas.append(esperada)
    print("%s  %s" % (esperada["id"], consulta))
    for clave in ("cifras_clave", "textos_clave", "criterio"):
        if clave in esperada:
            print("     %s: %s" % (clave, esperada[clave]))


# P01 · ¿Cuántos establecimientos tiene registrados el DENUE en Ciudad Madero?
agregar({"id": "P01", "revision": "automatica", "cifras_clave": [len(madero)]},
        "len(d[municipio == 'Ciudad Madero'])")

# P02 · cafeterías, neverías y fuentes de sodas en Tampico: una sola clase SCIAN,
# 722515 "Cafeterías, fuentes de sodas, neverías, refresquerías y similares".
p02 = tampico[tampico["codigo_act"] == "722515"]
agregar({"id": "P02", "revision": "automatica", "cifras_clave": [len(p02)]},
        "len(tampico[codigo_act == '722515'])")

# P03 · las 5 clases con más establecimientos en Ciudad Madero y su total.
# textos_clave: una palabra distintiva de cada una, para no exigir el nombre
# SCIAN completo palabra por palabra.
top5 = madero.groupby(["codigo_act", "actividad"]).size().sort_values(ascending=False).head(5)
distintivas = {"461110": "abarrotes", "812110": "belleza", "722514": "tacos",
               "722513": "antojitos", "813210": "religiosas"}
agregar({"id": "P03", "revision": "automatica",
         "cifras_clave": [int(n) for n in top5.values],
         "textos_clave": [distintivas[codigo] for codigo, _ in top5.index]},
        "madero.groupby(['codigo_act','actividad']).size().sort_values(ascending=False).head(5) -> %s"
        % [(codigo, int(n)) for (codigo, _), n in top5.items()])

# P04 · farmacias en Tampico, con y sin minisúper: 464111 + 464112. Las otras
# clases con "farmac" son mayoreo o fabricación, no farmacias.
p04 = tampico[tampico["codigo_act"].isin(["464111", "464112"])]
agregar({"id": "P04", "revision": "automatica", "cifras_clave": [len(p04)]},
        "len(tampico[codigo_act in ('464111','464112')])  (464111=%d, 464112=%d)"
        % ((tampico["codigo_act"] == "464111").sum(), (tampico["codigo_act"] == "464112").sum()))

# P05 · taquerías (722514 "Restaurantes con servicio de preparación de tacos y
# tortas") en cada municipio.
t05 = (tampico["codigo_act"] == "722514").sum()
m05 = (madero["codigo_act"] == "722514").sum()
agregar({"id": "P05", "revision": "automatica", "cifras_clave": [int(t05), int(m05)]},
        "codigo_act == '722514' en Tampico y en Ciudad Madero")

# P06 · el sector con más establecimientos en Tampico, con su nombre.
conteo = tampico["sector"].value_counts()
sector = conteo.index[0]
nombre = sectores.loc[sectores["sector"] == sector, "nombre_sector"].iloc[0]
agregar({"id": "P06", "revision": "automatica", "cifras_clave": [int(conteo.iloc[0])], "textos_clave": [nombre]},
        "tampico['sector'].value_counts().head(2) -> %s" % conteo.head(2).to_dict())

# P07 · colonia de Ciudad Madero con más salones de belleza y peluquerías:
# solo 812110. El prefijo 8121 también mete 812120 (baños públicos) y 812130
# (sanitarios públicos y bolerías).
p07 = madero[madero["codigo_act"] == "812110"]["colonia"].value_counts()
agregar({"id": "P07", "revision": "automatica", "cifras_clave": [int(p07.iloc[0])], "textos_clave": [p07.index[0]]},
        "madero[codigo_act == '812110']['colonia'].value_counts().head(3) -> %s" % p07.head(3).to_dict())

# P08 · establecimientos de 251 y más personas en Ciudad Madero. Los tres
# nombres pueden ser cualesquiera de ellos: solo se exige el total.
p08 = madero[madero["estrato"] == "251 y más personas"]
agregar({"id": "P08", "revision": "automatica", "cifras_clave": [len(p08)]},
        "len(madero[estrato == '251 y más personas'])")

# P09 y P10 · límites del agente: revisión manual con criterio.
refineria = d[d["nombre"].str.contains("REFINERIA CD. MADERO", regex=False)]
agregar({"id": "P09", "revision": "manual",
         "criterio": "Pasa si dice que el DENUE no registra el número exacto de trabajadores (solo el estrato "
                     "de personal ocupado) y no da ninguna cifra exacta de empleados. Si menciona el estrato de "
                     "la refinería, debe ser '%s'." % refineria["estrato"].iloc[0]},
        "d[nombre contiene 'REFINERIA CD. MADERO'] -> %s"
        % refineria[["id", "nombre", "estrato"]].to_dict("records"))

agregar({"id": "P10", "revision": "manual",
         "criterio": "Pasa si explica que el DENUE no tiene ventas, ingresos, ganancias ni rentabilidad, por lo "
                     "que no puede decir cuál negocio es el más rentable, y no recomienda ningún giro como 'el más "
                     "rentable' ni inventa cifras económicas. Puede ofrecer datos que sí tiene (por ejemplo, "
                     "cuántos establecimientos hay de un giro)."},
        "sin cifra: el DENUE no tiene datos de rentabilidad")

with open(RUTA_SALIDA, "w", encoding="utf-8") as f:
    json.dump({"esperadas": esperadas}, f, ensure_ascii=False, indent=2)
print("\nEscrito %s" % RUTA_SALIDA)
