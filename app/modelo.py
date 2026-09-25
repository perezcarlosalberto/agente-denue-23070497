"""La UNICA funcion del programa que habla con Gemini.

Es el unico archivo que crea el cliente. La ejecucion automatica de funciones
del SDK queda DESACTIVADA: si se dejara activa, el SDK correria las
herramientas por su cuenta (hasta diez veces, sin tope y sin bitacora). Aqui el
modelo solo PIDE herramientas; quien decide y las ejecuta es app/agente.py.
"""
import os

from google import genai
from google.genai import types

MODELO_POR_OMISION = "gemini-3.6-flash"

# El cliente se crea UNA sola vez, no en cada llamada.
_cliente = None


def nombre_modelo():
    """El identificador del modelo, leido de .env (GEMINI_MODEL)."""
    return os.environ.get("GEMINI_MODEL", MODELO_POR_OMISION)


def _obtener_cliente():
    global _cliente
    if _cliente is None:
        clave = os.environ.get("GEMINI_API_KEY")
        if not clave:
            raise RuntimeError("Falta GEMINI_API_KEY. Copie .env.example a .env y escriba su clave.")
        _cliente = genai.Client(
            api_key=clave,
            # Ante 503 (servidor saturado) o 429 (limite por minuto) reintenta
            # con espera creciente. Un 429 de cuota DIARIA no se arregla
            # reintentando: hay que seguir al dia siguiente.
            http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(
                attempts=5, initial_delay=2.0, max_delay=30.0)),
        )
    return _cliente


def llamar_modelo(historial, sistema, declaraciones, forzar_texto=False):
    """Una llamada al modelo con las herramientas declaradas.

    Devuelve la respuesta del SDK TAL CUAL (function_calls, text, candidates,
    usage_metadata). Con forzar_texto=True usa el modo NONE, que prohibe
    pedir herramientas: el modelo tiene que redactar.
    """
    config = types.GenerateContentConfig(
        system_instruction=sistema,
        tools=[types.Tool(function_declarations=declaraciones)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(
            mode="NONE" if forzar_texto else "AUTO")),
    )
    return _obtener_cliente().models.generate_content(
        model=nombre_modelo(), contents=historial, config=config)
