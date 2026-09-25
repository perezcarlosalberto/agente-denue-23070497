"""Parte F · Compara las respuestas reales con las esperadas.

    python -m app.evaluar logs/corrida-A.jsonl [logs/corrida-B.jsonl ...]

De las bitacoras toma, para cada pregunta del banco, el ULTIMO evento "fin"
REAL (modelo distinto de "simulado"; el mas reciente por ts). Una pregunta
automatica PASA si numeros(respuesta) contiene todas sus cifras_clave y la
respuesta normalizada contiene todos sus textos_clave normalizados. Las
manuales se listan con su criterio y su respuesta: el juicio va en
evaluacion/analisis.md.

Imprime una tabla y escribe evaluacion/resultados.json.
"""
import json
import sys

from app.guardia import numeros
from app.herramientas import normalizar

RUTA_BANCO = "data/preguntas_prueba.json"
RUTA_ESPERADAS = "evaluacion/esperadas.json"
RUTA_RESULTADOS = "evaluacion/resultados.json"


def leer_bitacoras(rutas, ids):
    """(finales, llamadas): el ultimo "fin" real por id y los eventos "modelo" reales por id."""
    finales = {}
    llamadas = {i: 0 for i in ids}
    for ruta in rutas:
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                try:
                    evento = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                if evento.get("modelo") in (None, "simulado") or evento.get("id") not in llamadas:
                    continue
                if evento.get("evento") == "modelo":
                    llamadas[evento["id"]] += 1
                if evento.get("evento") == "fin":
                    anterior = finales.get(evento["id"])
                    if anterior is None or evento["ts"] >= anterior["ts"]:
                        finales[evento["id"]] = evento
    return finales, llamadas


def calificar(esperada, fin):
    """El renglon de resultados de una pregunta."""
    renglon = {"revision": esperada["revision"]}
    if fin is None:
        renglon.update({"resultado": "SIN RESPUESTA", "pasa": False if esperada["revision"] == "automatica" else None,
                        "respuesta": None, "turnos": None, "herramientas": None, "cifras_sin_respaldo": None})
        return renglon

    renglon.update({"respuesta": fin["respuesta"], "turnos": fin["turnos"], "herramientas": fin["herramientas"],
                    "cifras_sin_respaldo": fin["cifras_sin_respaldo"], "corrida": fin["corrida"]})

    if esperada["revision"] == "manual":
        renglon.update({"resultado": "MANUAL", "pasa": None, "criterio": esperada["criterio"]})
        return renglon

    encontradas = numeros(fin["respuesta"])
    texto = normalizar(fin["respuesta"])
    faltan_cifras = [c for c in esperada["cifras_clave"] if c not in encontradas]
    faltan_textos = [t for t in esperada.get("textos_clave", []) if normalizar(t) not in texto]
    pasa = not faltan_cifras and not faltan_textos
    renglon.update({"resultado": "PASA" if pasa else "FALLA", "pasa": pasa,
                    "cifras_clave": esperada["cifras_clave"], "textos_clave": esperada.get("textos_clave", []),
                    "faltan_cifras": faltan_cifras, "faltan_textos": faltan_textos})
    return renglon


def main(argv):
    sys.stdout.reconfigure(errors="replace")
    rutas = [a for a in argv if not a.startswith("--")]
    if not rutas:
        print("Uso: python -m app.evaluar logs/corrida-A.jsonl [logs/corrida-B.jsonl ...]")
        return 2

    with open(RUTA_BANCO, encoding="utf-8") as f:
        banco = json.load(f)["preguntas"]
    with open(RUTA_ESPERADAS, encoding="utf-8") as f:
        esperadas = {e["id"]: e for e in json.load(f)["esperadas"]}

    ids = [p["id"] for p in banco]
    finales, llamadas = leer_bitacoras(rutas, ids)

    preguntas = []
    for p in banco:
        renglon = {"id": p["id"], "tipo": p["tipo"], "pregunta": p["pregunta"]}
        renglon.update(calificar(esperadas[p["id"]], finales.get(p["id"])))
        renglon["llamadas_en_bitacoras"] = llamadas[p["id"]]
        preguntas.append(renglon)

    automaticas = [r for r in preguntas if r["revision"] == "automatica"]
    manuales = [r for r in preguntas if r["revision"] == "manual"]
    totales = {
        "automaticas_aprobadas": sum(1 for r in automaticas if r["pasa"]),
        "automaticas": len(automaticas),
        "manuales": len(manuales),
        "manuales_con_respuesta": sum(1 for r in manuales if r["respuesta"] is not None),
        "turnos_respuestas_evaluadas": sum(r["turnos"] or 0 for r in preguntas),
        "llamadas_modelo_en_bitacoras": sum(llamadas.values()),
    }

    print("%-4s %-11s %-13s %6s %5s  %-12s %s" % ("ID", "TIPO", "RESULTADO", "TURNOS", "HERR", "SIN_RESP", "DETALLE"))
    for r in preguntas:
        if r["resultado"] == "FALLA":
            detalle = "faltan cifras %s, textos %s" % (r["faltan_cifras"], r["faltan_textos"])
        elif r["resultado"] == "MANUAL":
            detalle = "criterio: " + r["criterio"][:60]
        else:
            detalle = ""
        print("%-4s %-11s %-13s %6s %5s  %-12s %s" % (
            r["id"], r["tipo"], r["resultado"],
            "-" if r["turnos"] is None else r["turnos"],
            "-" if r["herramientas"] is None else r["herramientas"],
            "-" if r["cifras_sin_respaldo"] is None else (r["cifras_sin_respaldo"] or "[]"), detalle))

    for r in manuales:
        print("\n%s (manual) · criterio: %s\nRespuesta: %s" % (r["id"], r["criterio"] if "criterio" in r
              else esperadas[r["id"]]["criterio"], r["respuesta"]))

    print("\nAutomáticas aprobadas: %d/%d · manuales para revisar: %d · llamadas al modelo en las bitácoras: %d" % (
        totales["automaticas_aprobadas"], totales["automaticas"], totales["manuales"],
        totales["llamadas_modelo_en_bitacoras"]))

    with open(RUTA_RESULTADOS, "w", encoding="utf-8") as f:
        json.dump({"bitacoras": rutas, "totales": totales, "preguntas": preguntas}, f, ensure_ascii=False, indent=2)
    print("Escrito %s" % RUTA_RESULTADOS)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
