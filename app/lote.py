"""Corre el banco de preguntas (data/preguntas_prueba.json).

    python -m app.lote --simulado
    python -m app.lote --desde P01 --hasta P05      dia 1, modelo real
    python -m app.lote --desde P06 --hasta P10      dia 2, modelo real

--desde y --hasta son identificadores del banco (inclusivos). Toda la corrida
queda en UNA bitacora; el id de cada evento es el de la pregunta (P01...).
Entre preguntas reales se esperan 4 segundos. Si una pregunta falla, el error
queda en la bitacora y el lote SIGUE con la siguiente.
"""
import json
import sys
import time

from dotenv import load_dotenv

from app import agente

RUTA_BANCO = "data/preguntas_prueba.json"
PAUSA_REAL = 4  # segundos entre preguntas con el modelo real


def _opcion(argv, nombre):
    """El valor de --desde P01 (o --desde=P01), o None."""
    for i, arg in enumerate(argv):
        if arg == nombre and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith(nombre + "="):
            return arg.split("=", 1)[1]
    return None


def main(argv):
    sys.stdout.reconfigure(errors="replace")  # un caracter raro del modelo no tumba la salida
    load_dotenv()
    simulado = "--simulado" in argv
    desde = _opcion(argv, "--desde")
    hasta = _opcion(argv, "--hasta")

    with open(RUTA_BANCO, encoding="utf-8") as f:
        banco = json.load(f)["preguntas"]
    ids = [p["id"] for p in banco]
    for nombre, valor in (("--desde", desde), ("--hasta", hasta)):
        if valor is not None and valor not in ids:
            print("%s %s no está en el banco. Válidos: %s" % (nombre, valor, ", ".join(ids)))
            return 2
    primero = ids.index(desde) if desde else 0
    ultimo = ids.index(hasta) if hasta else len(ids) - 1
    elegidas = banco[primero:ultimo + 1]

    herramientas = agente.cargar_herramientas()
    sistema = agente.leer_sistema()
    _, modelo = agente.crear_llamar(simulado)
    bitacora = agente.Bitacora(modelo)

    print("Corrida %s | modelo: %s | %d preguntas" % (bitacora.corrida, modelo, len(elegidas)))
    print("Bitácora: %s\n" % bitacora.ruta)

    fallos = 0
    for n, item in enumerate(elegidas):
        if n and not simulado:
            time.sleep(PAUSA_REAL)

        # Un llamar nuevo por pregunta: el simulado vuelve a su paso 1.
        llamar, _ = agente.crear_llamar(simulado)
        bitacora.nueva_pregunta(item["id"])
        try:
            fin = agente.responder(item["pregunta"], herramientas, sistema, llamar, bitacora)
        except Exception as error:
            # responder ya registro el evento "error"; el lote sigue.
            fallos += 1
            print("%-4s ERROR  %s" % (item["id"], agente.explicar_error(error)))
            continue

        primera = fin["respuesta"].splitlines()[0] if fin["respuesta"] else ""
        print("%-4s turnos=%d herramientas=%d sin_respaldo=%s %.1fs | %s" % (
            item["id"], fin["turnos"], fin["herramientas"], fin["cifras_sin_respaldo"] or "-",
            fin["segundos"], primera[:90]))

    print("\n%d preguntas, %d con error." % (len(elegidas), fallos))
    if fallos:
        print("Repita solo las que fallaron con --desde/--hasta y suba todas las bitácoras.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
