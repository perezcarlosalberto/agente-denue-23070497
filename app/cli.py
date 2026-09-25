"""Una pregunta desde la terminal.

    python -m app.cli "¿Cuántas farmacias hay en Tampico?"              modelo real (gasta cuota)
    python -m app.cli "¿Cuántas farmacias hay en Tampico?" --simulado   modelo falso (no gasta nada)

Los eventos quedan en logs/corrida-AAAAMMDD-HHMMSS.jsonl con id "CLI".
"""
import sys

from dotenv import load_dotenv

from app import agente


def main(argv):
    sys.stdout.reconfigure(errors="replace")  # un caracter raro del modelo no tumba la salida
    load_dotenv()
    simulado = "--simulado" in argv
    pregunta = " ".join(a for a in argv if not a.startswith("--")).strip()
    if not pregunta:
        print('Uso: python -m app.cli "pregunta" [--simulado]')
        return 2

    herramientas = agente.cargar_herramientas()
    sistema = agente.leer_sistema()
    llamar, modelo = agente.crear_llamar(simulado)
    bitacora = agente.Bitacora(modelo)
    bitacora.nueva_pregunta("CLI")

    try:
        fin = agente.responder(pregunta, herramientas, sistema, llamar, bitacora)
    except Exception as error:
        # El evento "error" ya lo registro responder.
        print("No se pudo obtener respuesta: %s" % agente.explicar_error(error))
        print("Bitácora: %s" % bitacora.ruta)
        return 1

    print(fin["respuesta"])
    print()
    print("Turnos: %d | herramientas: %d | segundos: %.2f | modelo: %s" % (
        fin["turnos"], fin["herramientas"], fin["segundos"], modelo))
    print("Bitácora: %s" % bitacora.ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
