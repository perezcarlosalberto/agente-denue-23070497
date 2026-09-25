"""Parte C · La guardia de cifras.

El prompt PIDE que el modelo no calcule; la guardia lo COMPRUEBA: toda cifra
de la respuesta debe aparecer en la pregunta o en algun resultado de las
herramientas de esa misma pregunta. La guardia no oculta nada: avisa.
"""
import re

# Marca de lista al inicio de un renglon: "1. " o "2) ".
_MARCA_LISTA = re.compile(r"^[ \t]*[0-9]+[.)][ \t]", re.MULTILINE)

# Primero los enteros con comas de miles (7,184 o 1,234,567, con decimales
# opcionales); si no, un entero o un decimal con punto (154, 05, 65.8).
_CIFRA = re.compile(r"[0-9]{1,3}(?:,[0-9]{3})+(?![0-9])(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?")


def _a_numero(cifra):
    """"7,184" -> 7184   "05" -> 5   "5.5" -> 5.5   "5.0" -> 5"""
    cifra = cifra.replace(",", "")
    if "." in cifra:
        valor = float(cifra)
        return int(valor) if valor.is_integer() else valor
    return int(cifra)


def numeros(texto):
    """El conjunto de cifras de un texto, como numeros (sin marcas de lista)."""
    texto = _MARCA_LISTA.sub("", texto)
    return {_a_numero(c) for c in _CIFRA.findall(texto)}


def numeros_en(objeto):
    """Todas las cifras dentro de diccionarios (sus valores), listas y textos.

    Un numero de Python se trata como su texto; True, False y None no aportan
    cifras (bool se revisa antes que int porque True tambien es un int).
    """
    if objeto is None or isinstance(objeto, bool):
        return set()
    if isinstance(objeto, dict):
        return numeros_en(list(objeto.values()))
    if isinstance(objeto, (list, tuple)):
        encontrados = set()
        for elemento in objeto:
            encontrados |= numeros_en(elemento)
        return encontrados
    # int, float, str y cualquier otro valor: su texto.
    return numeros(str(objeto))


def cifras_sin_respaldo(respuesta, pregunta, resultados):
    """Cifras de la respuesta que no estan ni en la pregunta ni en los resultados, ordenadas."""
    respaldo = numeros(pregunta) | numeros_en(resultados)
    return sorted(numeros(respuesta) - respaldo)


def mensaje_correccion(sin_respaldo):
    """El mensaje de usuario de la seccion 8.3: una oportunidad de corregir."""
    return (
        "Revisión automática: estas cifras de tu respuesta no aparecen en la pregunta ni en "
        "los resultados de las herramientas: %s. No calcules sumas ni porcentajes: si "
        "necesitas un total, pídelo a una herramienta. Corrige la respuesta." % sin_respaldo
    )


def aviso(sin_respaldo):
    """Lo que se agrega al texto si la respuesta sigue con cifras sin respaldo."""
    return "[Aviso] Cifras sin respaldo en los datos: %s" % sin_respaldo
