"""Modelo falso: misma firma que modelo.llamar_modelo y sin usar la red.

Devuelve respuestas FABRICADAS del SDK (con function_calls, text y candidates,
como las reales) siguiendo un guion fijo de 4 pasos. Avanza un paso en cada
llamada y vuelve al inicio despues del cuarto:

    1  pide buscar_actividades(texto="farmacia")                     id "sim-1"
    2  pide contar(codigo_act="464111,464112", municipio="Tampico")  id "sim-2"
    3  texto con 160 farmacias: cifra inventada, la guardia la marca
    4  texto con 154 farmacias: la cifra que devuelve contar

Regla adicional: si forzar_texto es verdadero y el paso que toca es una
peticion, devuelve en su lugar el texto de "presupuesto" (y de todos modos
avanza un paso).

Cada instancia empieza en el paso 1: "el simulado recien creado".
"""
from google.genai import types

TEXTO_PRESUPUESTO = "Respuesta: No pude completar la consulta con el presupuesto."

GUION = [
    types.Part(function_call=types.FunctionCall(
        id="sim-1", name="buscar_actividades", args={"texto": "farmacia"})),
    types.Part(function_call=types.FunctionCall(
        id="sim-2", name="contar", args={"codigo_act": "464111,464112", "municipio": "Tampico"})),
    types.Part(text="Respuesta: En Tampico hay 160 farmacias.\nDatos: DENUE 05/2026, INEGI"),
    types.Part(text="Respuesta: En Tampico hay 154 farmacias (clases 464111 y 464112).\n"
                    "Datos: DENUE 05/2026, INEGI"),
]


def respuesta_falsa(partes):
    """Una respuesta del SDK fabricada a mano (Anexo A.6). No trae usage_metadata."""
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=partes))])


class ModeloSimulado:
    def __init__(self):
        self.paso = 0   # indice en GUION del paso que toca (0 = paso 1)

    def __call__(self, historial, sistema, declaraciones, forzar_texto=False):
        parte = GUION[self.paso]
        self.paso = (self.paso + 1) % len(GUION)

        if forzar_texto and parte.function_call is not None:
            parte = types.Part(text=TEXTO_PRESUPUESTO)
        return respuesta_falsa([parte])
