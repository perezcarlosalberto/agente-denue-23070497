"""Pruebas sin red: herramientas, ejecutar, guardia, ciclo con el simulado y bot.

    python -m pruebas.prueba_herramientas

No llama a Gemini ni a Telegram. Si todo pasa, imprime OK al final.
"""
import hashlib

from app import agente
from app.bot import leer_permitidos, partir_mensaje, usuario_anonimo
from app.guardia import cifras_sin_respaldo, numeros, numeros_en
from app.herramientas import ESTRATOS, Herramientas, cargar_datos, normalizar
from app.modelo_simulado import TEXTO_PRESUPUESTO, ModeloSimulado

datos, sectores = cargar_datos("data/denue_tampico_madero.csv", "data/sectores_scian.csv")
h = Herramientas(datos, sectores)


# --------------------------------------------------------------------------
# Parte A · normalizar, cargar_datos y las 4 herramientas sobre el archivo completo
# --------------------------------------------------------------------------

assert normalizar(" Cafeterías,   Neverías") == "cafeterias, neverias"
assert len(datos) == 22900 and datos["codigo_act"].str.len().eq(6).all()  # dtype=str: los codigos no pierden digitos
assert len(sectores) == 20 and sectores["46"] == "Comercio al por menor"

# contar
assert h.contar()["total"] == 22900
r = h.contar(municipio="ciudad madero")
assert r["total"] == 7184 and r["filtros"] == {"municipio": "Ciudad Madero"} and r["fuente"] == "DENUE 05/2026, INEGI"
assert h.contar(municipio="TAMPICO")["total"] == 15716
assert h.contar(codigo_act="464111,464112", municipio="Tampico")["total"] == 154

# buscar_actividades: plurales sencillos, ambos municipios, sin coincidencias = lista vacia
codigos = [a["codigo_act"] for a in h.buscar_actividades("Farmacias")["actividades"]]
assert "464111" in codigos and "464112" in codigos
assert h.buscar_actividades("tacos")["actividades"][0] == {
    "codigo_act": "722514", "actividad": "Restaurantes con servicio de preparación de tacos y tortas",
    "establecimientos": 866}
assert h.buscar_actividades("xyzzy") == {"ok": True, "fuente": "DENUE 05/2026, INEGI", "actividades": []}

# ranking
r = h.ranking(por="municipio", codigo_act="722514")
assert r["filas"] == [{"valor": "Tampico", "total": 570}, {"valor": "Ciudad Madero", "total": 296}]
assert r["total_filtrado"] == 866 and r["por"] == "municipio"
assert h.ranking(por="sector", municipio="Tampico", top=1)["filas"][0]["nombre_sector"] == "Comercio al por menor"
assert len(h.ranking(por="sector", top=99)["filas"]) == 20 and len(h.ranking(por="sector", top=0)["filas"]) == 1
assert "actividad" in h.ranking(por="codigo_act", municipio="Tampico")["filas"][0]

# listar: del estrato mayor al menor y, dentro del estrato, por nombre
r = h.listar(codigo_act="722514", municipio="Tampico", limite=5)
assert r["total"] == 570 and r["mostrados"] == 5 and len(r["establecimientos"]) == 5
orden = [(-ESTRATOS.index(e["estrato"]), e["nombre"]) for e in r["establecimientos"]]
assert orden == sorted(orden)
assert h.listar(municipio="Tampico", limite=500)["mostrados"] == 20

# colonia: igualdad exacta normalizada; si no hay filas, sugerencias que contienen el texto
assert h.contar(colonia="zona centro", municipio="Tampico")["filtros"]["colonia"] == "ZONA CENTRO"
r = agente.ejecutar(h, "contar", {"colonia": "centr", "municipio": "Tampico"})
assert r["ok"] is False and "ZONA CENTRO" in r["valores_validos"] and len(r["valores_validos"]) <= 10


# --------------------------------------------------------------------------
# Parte B · ejecutar: errores estructurados, nunca excepciones
# --------------------------------------------------------------------------

r = agente.ejecutar(h, "contar", {"municipio": "Altamira"})
assert r == {"ok": False, "error": "municipio no válido: 'Altamira'.", "valores_validos": ["Tampico", "Ciudad Madero"]}
r = agente.ejecutar(h, "contar", {"codigo_act": "46A111"})
assert r["ok"] is False and "codigo_act" in r["error"]
r = agente.ejecutar(h, "listar", {})
assert r["ok"] is False and "al menos un filtro" in r["error"]
r = agente.ejecutar(h, "borrar_archivos", {"ruta": ".env"})
assert r["ok"] is False and r["error"] == "herramienta inexistente: borrar_archivos"
r = agente.ejecutar(h, "contar", {"ciudad": "Tampico"})
assert r["ok"] is False and "ciudad" in r["error"] and "municipio" in r["valores_validos"]
assert agente.ejecutar(h, "ranking", {"por": "municipio", "colonia": "CENTRO"})["ok"] is False
assert agente.ejecutar(h, "ranking", {})["error"] == "falta el argumento obligatorio de ranking: por"
assert agente.ejecutar(h, "buscar_actividades", {"texto": "de"})["ok"] is False


# --------------------------------------------------------------------------
# Parte C · la guardia
# --------------------------------------------------------------------------

assert numeros("En Madero hay 7,184 negocios y el 5.5 % son cafeterías") == {7184, 5.5}
assert numeros("1. Tampico: 12\n2) Madero: 05\n 3. Otro") == {12, 5}
assert numeros("5.0 y 1,234,567.25 y 464111,464112") == {5, 1234567.25, 464111, 464112}
assert numeros_en({"a": [1, "x 22"], "b": True, "c": None, "d": {"e": 3.5}}) == {1, 22, 3.5}
assert cifras_sin_respaldo("Hay 154 de 200, el 77 %", "¿Cuántas de 200?", [{"total": 154}]) == [77]

# Los casos de la traza E.2 (taquerias)
PREGUNTA_E2 = "¿Dónde hay más taquerías, en Tampico o en Ciudad Madero? Dame la cifra de cada municipio."
RESULTADOS_E2 = [
    {"ok": True, "fuente": "DENUE 05/2026, INEGI",
     "actividades": [{"codigo_act": "722514",
                      "actividad": "Restaurantes con servicio de preparación de tacos y tortas",
                      "establecimientos": 866}]},
    {"ok": True, "fuente": "DENUE 05/2026, INEGI", "por": "municipio",
     "filtros": {"codigo_act": "722514"}, "total_filtrado": 866,
     "filas": [{"valor": "Tampico", "total": 570}, {"valor": "Ciudad Madero", "total": 296}]},
]
G1 = "Tampico tiene 570 taquerías y Ciudad Madero 296."
G2 = "Tampico tiene 570 y Madero 296: una diferencia de 274."
G3 = "En total hay 866; Tampico concentra el 65.8 %."
G4 = "1. Tampico: 570\n2. Ciudad Madero: 296\nClase SCIAN 722514, DENUE 05/2026."
G5 = "Tampico tiene 1,570 taquerías."
G6 = "Ciudad Madero tiene 570 taquerías y Tampico 296."

assert numeros(G1) == {570, 296} and cifras_sin_respaldo(G1, PREGUNTA_E2, RESULTADOS_E2) == []
assert numeros(G2) == {570, 296, 274} and cifras_sin_respaldo(G2, PREGUNTA_E2, RESULTADOS_E2) == [274]
assert numeros(G3) == {866, 65.8} and cifras_sin_respaldo(G3, PREGUNTA_E2, RESULTADOS_E2) == [65.8]
assert numeros(G4) == {570, 296, 722514, 5, 2026} and cifras_sin_respaldo(G4, PREGUNTA_E2, RESULTADOS_E2) == []
assert numeros(G5) == {1570} and cifras_sin_respaldo(G5, PREGUNTA_E2, RESULTADOS_E2) == [1570]
# G6 es falsa (cruza los municipios) y aun asi pasa la guardia: solo revisa que las cifras existan.
assert numeros(G6) == {570, 296} and cifras_sin_respaldo(G6, PREGUNTA_E2, RESULTADOS_E2) == []


# --------------------------------------------------------------------------
# Parte D · el ciclo completo con el simulado (traza E.1)
# --------------------------------------------------------------------------

sistema = agente.leer_sistema()
PREGUNTA_E1 = "¿Cuántas farmacias hay en Tampico?"

bitacora = agente.Bitacora("simulado", carpeta=None)
bitacora.nueva_pregunta("E1")
fin = agente.responder(PREGUNTA_E1, h, sistema, ModeloSimulado(), bitacora)
assert fin["turnos"] == 4 and fin["herramientas"] == 2 and fin["cifras_sin_respaldo"] == []
assert fin["respuesta"].startswith("Respuesta: En Tampico hay 154 farmacias")
assert [e["evento"] for e in bitacora.eventos] == [
    "inicio", "modelo", "herramienta", "modelo", "herramienta", "modelo", "guardia", "modelo", "guardia", "fin"]
guardias = [e for e in bitacora.eventos if e["evento"] == "guardia"]
assert guardias[0]["cifras_sin_respaldo"] == [160] and guardias[0]["corregida"] is False
assert guardias[1]["cifras_sin_respaldo"] == [] and guardias[1]["corregida"] is True
assert all(e["id"] == "E1" and e["modelo"] == "simulado" for e in bitacora.eventos)

# E.1 (3): con MAX_HERRAMIENTAS = 1 el paso 12 fuerza el texto en el turno 2
agente.MAX_HERRAMIENTAS = 1
try:
    bitacora = agente.Bitacora("simulado", carpeta=None)
    fin = agente.responder(PREGUNTA_E1, h, sistema, ModeloSimulado(), bitacora)
finally:
    agente.MAX_HERRAMIENTAS = 6
assert fin["turnos"] == 2 and fin["herramientas"] == 1 and fin["respuesta"] == TEXTO_PRESUPUESTO
assert [e["evento"] for e in bitacora.eventos] == ["inicio", "modelo", "herramienta", "modelo", "guardia", "fin"]
assert bitacora.eventos[3]["forzar_texto"] is True


# --------------------------------------------------------------------------
# Parte H · funciones puras del bot
# --------------------------------------------------------------------------

assert leer_permitidos("111, 222,,333 ") == {111, 222, 333}
assert leer_permitidos("") == set() and leer_permitidos(None) == set()
texto = "\n".join("renglón %d " % i + "x" * 90 for i in range(200))
trozos = partir_mensaje(texto)
assert len(trozos) > 1 and all(len(t) <= 4096 for t in trozos)
assert "\n".join(trozos) == texto and partir_mensaje("hola") == ["hola"]
assert all(len(t) <= 10 for t in partir_mensaje("a" * 35, limite=10))
assert usuario_anonimo(123456789) == hashlib.sha256(b"123456789").hexdigest()[:10]
assert len(usuario_anonimo(987)) == 10 and "987" != usuario_anonimo(987)

print("OK")
