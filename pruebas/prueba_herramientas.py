"""Pruebas sin red: herramientas, ejecutar, guardia, ciclo con el simulado y bot.

    python -m pruebas.prueba_herramientas

No llama a Gemini ni a Telegram. Si todo pasa, imprime OK al final.
"""
import hashlib

from app import agente
from app.bot import leer_permitidos, partir_mensaje, usuario_anonimo
from app.guardia import cifras_sin_respaldo, numeros, numeros_en
from app.herramientas import ESTRATOS, Herramientas, cargar_datos, normalizar

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
