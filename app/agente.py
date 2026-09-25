"""Parte B · El ciclo del agente: percibir, decidir, actuar, observar.

    percibir  la pregunta y, despues, los resultados de las herramientas
    decidir   el MODELO elige que herramienta pedir y con que argumentos
    actuar    el CODIGO la ejecuta sobre los datos (ejecutar)
    observar  el resultado vuelve al historial y se repite

El ciclo es de este archivo, no del SDK: el modelo solo pide. El modelo no
tiene memoria: en cada turno se le reenvia el historial completo.

La terminal (cli.py), el lote (lote.py) y Telegram (bot.py) llaman a este
mismo responder. El ciclo no sabe de donde llego la pregunta.
"""
import inspect
import json
import time
from datetime import datetime
from pathlib import Path

from google.genai import types

from app.guardia import aviso, cifras_sin_respaldo, mensaje_correccion
from app.herramientas import DECLARACIONES, ErrorHerramienta, Herramientas, cargar_datos

MAX_TURNOS = 5          # llamadas al modelo por pregunta
MAX_HERRAMIENTAS = 6    # herramientas ejecutadas por pregunta

RUTA_DENUE = "data/denue_tampico_madero.csv"
RUTA_SECTORES = "data/sectores_scian.csv"
RUTA_SISTEMA = "prompts/sistema.md"

NOMBRES = [d["name"] for d in DECLARACIONES]


# --------------------------------------------------------------------------
# Bitacora: logs/corrida-AAAAMMDD-HHMMSS.jsonl, una linea JSON por evento
# --------------------------------------------------------------------------

class Bitacora:
    """Escribe cada evento con ts, corrida, modelo, id y evento.

    Guarda tambien una copia en memoria (self.eventos) para las pruebas. Con
    carpeta=None no escribe ningun archivo.
    """

    def __init__(self, modelo, carpeta="logs"):
        self.corrida = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.modelo = modelo
        self.id = None
        self.extra_inicio = {}
        self.eventos = []
        self.ruta = None
        if carpeta is not None:
            Path(carpeta).mkdir(exist_ok=True)
            self.ruta = Path(carpeta) / ("corrida-%s.jsonl" % self.corrida)

    def nueva_pregunta(self, identificador, **extra_inicio):
        """Fija el id de los eventos siguientes (P01, CLI, TG-3...).

        extra_inicio se agrega solo al evento "inicio" (Telegram pone ahi
        canal y usuario).
        """
        self.id = identificador
        self.extra_inicio = extra_inicio

    def __call__(self, evento, **campos):
        linea = {"ts": datetime.now().isoformat(timespec="seconds"), "corrida": self.corrida,
                 "modelo": self.modelo, "id": self.id, "evento": evento}
        linea.update(campos)
        if evento == "inicio":
            linea.update(self.extra_inicio)
        self.eventos.append(linea)
        if self.ruta is not None:
            with open(self.ruta, "a", encoding="utf-8") as f:
                f.write(json.dumps(linea, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------
# 7.1 ejecutar: ninguna excepcion llega al modelo
# --------------------------------------------------------------------------

def ejecutar(herramientas, nombre, args):
    """Corre la herramienta pedida y SIEMPRE devuelve un diccionario.

    Solo se llaman los cuatro metodos declarados, con getattr sobre una lista
    fija de nombres: el modelo nunca manda codigo que se ejecute.
    """
    if nombre not in NOMBRES:
        return {"ok": False, "error": "herramienta inexistente: %s" % nombre, "valores_validos": NOMBRES}

    funcion = getattr(herramientas, nombre)
    args = dict(args or {})
    try:
        return funcion(**args)
    except ErrorHerramienta as error:
        # Argumento invalido que la propia herramienta detecto.
        return {"ok": False, "error": error.mensaje, "valores_validos": error.valores_validos}
    except TypeError as error:
        # Un argumento que no existe (ciudad="Tampico") o uno obligatorio que falta.
        parametros = inspect.signature(funcion).parameters
        validos = list(parametros)
        sobran = [a for a in args if a not in parametros]
        faltan = [n for n, p in parametros.items() if p.default is inspect.Parameter.empty and n not in args]
        if sobran:
            mensaje = "argumento inexistente en %s: %s" % (nombre, ", ".join(sobran))
        elif faltan:
            mensaje = "falta el argumento obligatorio de %s: %s" % (nombre, ", ".join(faltan))
        else:
            mensaje = "argumentos no válidos para %s: %s" % (nombre, error)
        return {"ok": False, "error": mensaje, "valores_validos": validos}
    except Exception as error:
        # Cualquier otra falla tampoco tumba el programa.
        return {"ok": False, "error": "falló %s: %s" % (nombre, error), "valores_validos": None}


# --------------------------------------------------------------------------
# 7.2 responder: el algoritmo (los numeros de los comentarios son sus pasos)
# --------------------------------------------------------------------------

def responder(pregunta, herramientas, sistema, llamar, bitacora):
    """Una pregunta -> {respuesta, turnos, herramientas, cifras_sin_respaldo, segundos}.

    Si algo falla (la red, la cuota, el modelo), registra el evento "error" y
    relanza la excepcion: quien llama decide como avisar.
    """
    inicio = time.time()
    bitacora("inicio", pregunta=pregunta)
    try:
        # 1
        historial = [types.Content(role="user", parts=[types.Part(text=pregunta)])]
        resultados = []
        usadas = 0
        corregida = False
        forzar_texto = False

        for turno in range(1, MAX_TURNOS + 1):                                  # 2
            if turno == MAX_TURNOS:                                              # 3
                forzar_texto = True

            respuesta = llamar(historial, sistema, DECLARACIONES, forzar_texto)  # 4
            uso = respuesta.usage_metadata  # None en el simulado
            bitacora("modelo", turno=turno, forzar_texto=forzar_texto,
                     tokens_entrada=uso.prompt_token_count if uso else None,
                     tokens_salida=((uso.candidates_token_count or 0) + (uso.thoughts_token_count or 0))
                     if uso else None)

            # 5 El turno del modelo TAL COMO LLEGO: trae firmas internas que
            #   Gemini exige de vuelta. No se reconstruye a mano.
            historial.append(respuesta.candidates[0].content)

            pedidas = respuesta.function_calls or []
            if pedidas:                                                          # 6
                partes = []
                for fc in pedidas:                                               # 7
                    args = dict(fc.args or {})
                    if usadas >= MAX_HERRAMIENTAS:                               # 8
                        resultado = {"ok": False, "valores_validos": None,
                                     "error": "presupuesto agotado: redacta la respuesta con "
                                              "los resultados que ya tienes."}
                    else:                                                        # 9
                        usadas += 1
                        resultado = ejecutar(herramientas, fc.name, args)
                        resultados.append(resultado)
                    bitacora("herramienta", nombre=fc.name, args=args,           # 10
                             ok=resultado["ok"], error=resultado.get("error"))
                    # Cada respuesta lleva el MISMO id que su peticion,
                    # tambien las rechazadas por presupuesto.
                    partes.append(types.Part(function_response=types.FunctionResponse(
                        id=fc.id, name=fc.name, response=resultado)))
                historial.append(types.Content(role="user", parts=partes))      # 11
                if usadas >= MAX_HERRAMIENTAS:                                   # 12
                    forzar_texto = True
                continue                                                         # 13

            texto = respuesta.text or ""                                         # 14
            sin_respaldo = cifras_sin_respaldo(texto, pregunta, resultados)
            bitacora("guardia", cifras_sin_respaldo=sin_respaldo, corregida=corregida)  # 15

            if sin_respaldo and not corregida and turno < MAX_TURNOS:            # 16
                corregida = True                                                 # 17
                historial.append(types.Content(role="user", parts=[             # 18
                    types.Part(text=mensaje_correccion(sin_respaldo))]))
                continue

            if sin_respaldo:                                                     # 19
                texto += "\n\n" + aviso(sin_respaldo)

            fin = {"respuesta": texto, "turnos": turno, "herramientas": usadas,  # 20
                   "cifras_sin_respaldo": sin_respaldo,
                   "segundos": round(time.time() - inicio, 2)}
            bitacora("fin", **fin)
            return fin

        raise RuntimeError("se agotaron los turnos sin texto")                   # 21

    except Exception as error:
        bitacora("error", error=str(error)[:300])
        raise


# --------------------------------------------------------------------------
# Lo que comparten la terminal, el lote y el bot
# --------------------------------------------------------------------------

def cargar_herramientas():
    datos, sectores = cargar_datos(RUTA_DENUE, RUTA_SECTORES)
    return Herramientas(datos, sectores)


def leer_sistema():
    return Path(RUTA_SISTEMA).read_text(encoding="utf-8")


def explicar_error(error):
    """Un mensaje comprensible para la persona, nunca un traceback."""
    texto = str(error)
    if "PerDay" in texto:
        return "se agotó la cuota diaria del modelo; hay que continuar mañana"
    if "429" in texto or "RESOURCE_EXHAUSTED" in texto:
        return "demasiadas peticiones por minuto; espera un momento"
    if "503" in texto or "UNAVAILABLE" in texto:
        return "el servidor del modelo está saturado; inténtalo más tarde"
    if "GEMINI_API_KEY" in texto:
        return texto
    return "hubo un problema al consultar el modelo"


def crear_llamar(simulado):
    """(llamar, nombre del modelo). El simulado se crea nuevo: empieza en el paso 1.

    Se importa aqui y no arriba para que el modo simulado no necesite la clave.
    """
    if simulado:
        from app.modelo_simulado import ModeloSimulado
        return ModeloSimulado(), "simulado"
    from app.modelo import llamar_modelo, nombre_modelo
    return llamar_modelo, nombre_modelo()
