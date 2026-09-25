"""Parte H · Bot de Telegram: SOLO recibe y entrega mensajes.

Este archivo NO contiene logica del agente: no llama al modelo, no ejecuta
herramientas y no revisa cifras. Cada mensaje de texto llama al mismo
agente.responder que usa la terminal y devuelve la respuesta.

    python -m app.bot              modelo real (gasta cuota de Gemini)
    python -m app.bot --simulado   modelo falso (no gasta nada)
"""
import asyncio
import hashlib
import logging
import os
import sys

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from app import agente

LIMITE_TELEGRAM = 4096

AVISO_START = (
    "Agente analista del DENUE: negocios de Tampico y Ciudad Madero.\n\n"
    "Puedo responder cuántos establecimientos hay de un giro, en qué municipio, "
    "colonia o sector hay más, cuáles son las actividades más comunes y nombrar "
    "establecimientos por tamaño. Cada cifra sale de una consulta a los datos.\n\n"
    "El DENUE NO tiene el número exacto de empleados (solo rangos), ventas, "
    "ganancias, salarios ni opiniones.\n\n"
    "Una respuesta puede tardar un minuto o más: consulto los datos varias veces.\n\n"
    "Privacidad: no escribas datos personales. Los mensajes pasan por los "
    "servidores de Telegram y de Google.\n\n"
    "Comandos:\n"
    "/fuente - de dónde salen los datos"
)

MENSAJE_PRIVADO = (
    "Este bot es privado. Tu identificador de Telegram es %d.\n"
    "Pide a quien lo administra que lo agregue a TELEGRAM_USUARIOS_PERMITIDOS."
)

MENSAJE_ERROR = "No pude responder en este momento (%s). Intenta de nuevo más tarde."


# --------------------------------------------------------------------------
# Funciones puras, sin red: se prueban en pruebas/prueba_herramientas.py
# --------------------------------------------------------------------------

def leer_permitidos(texto):
    """"111, 222,333" -> {111, 222, 333}. Vacio o ausente -> set(): no atiende a nadie."""
    permitidos = set()
    for parte in (texto or "").split(","):
        parte = parte.strip()
        if parte:
            permitidos.add(int(parte))
    return permitidos


def partir_mensaje(texto, limite=LIMITE_TELEGRAM):
    """Trozos de a lo mas `limite` caracteres, cortando de preferencia en un salto de linea."""
    if len(texto) <= limite:
        return [texto]
    trozos = []
    resto = texto
    while len(resto) > limite:
        corte = resto.rfind("\n", 0, limite)
        if corte <= 0:
            corte = limite  # un renglon mas largo que el limite: se corta ahi
        trozos.append(resto[:corte])
        resto = resto[corte:].lstrip("\n")
    if resto:
        trozos.append(resto)
    return trozos


def usuario_anonimo(user_id):
    """Los primeros 10 caracteres del SHA-256 del identificador. Nunca el id real ni el nombre."""
    return hashlib.sha256(str(user_id).encode()).hexdigest()[:10]


# --------------------------------------------------------------------------
# Manejadores
# --------------------------------------------------------------------------

async def _autorizado(update, context):
    """True si quien escribe esta en la lista; a cualquier otro se le muestra su id."""
    user_id = update.effective_user.id
    if user_id in context.bot_data["permitidos"]:
        return True
    await update.effective_message.reply_text(MENSAJE_PRIVADO % user_id)
    return False


async def _con_escribiendo(chat, funcion, *args):
    """Corre `funcion` (bloqueante) en otro hilo con asyncio.to_thread y muestra
    "escribiendo..." mientras tanto; el aviso dura unos 5 segundos, por eso se
    repite cada 4. Asi el bot no se congela.
    """
    tarea = asyncio.ensure_future(asyncio.to_thread(funcion, *args))
    while not tarea.done():
        await chat.send_action(ChatAction.TYPING)
        await asyncio.wait([tarea], timeout=4)
    return tarea.result()  # si la funcion fallo, aqui se relanza la excepcion


async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start"""
    if await _autorizado(update, context):
        await update.effective_message.reply_text(AVISO_START)


async def fuente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/fuente"""
    if await _autorizado(update, context):
        await update.effective_message.reply_text(context.bot_data["texto_fuente"])


async def pregunta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cualquier texto que no sea comando: se responde con agente.responder."""
    if not await _autorizado(update, context):
        return

    datos = context.bot_data
    datos["contador"] += 1
    bitacora = datos["bitacora"]
    # La libreria atiende los mensajes de uno en uno: el id no se mezcla.
    bitacora.nueva_pregunta("TG-%d" % datos["contador"], canal="telegram",
                            usuario=usuario_anonimo(update.effective_user.id))
    llamar, _ = agente.crear_llamar(datos["simulado"])

    try:
        fin = await _con_escribiendo(update.effective_chat, agente.responder,
                                     update.effective_message.text, datos["herramientas"],
                                     datos["sistema"], llamar, bitacora)
    except Exception as error:
        # Mensaje amable, nunca un traceback. El evento "error" ya lo
        # registro agente.responder en la bitacora.
        await update.effective_message.reply_text(MENSAJE_ERROR % agente.explicar_error(error))
        return

    for trozo in partir_mensaje(fin["respuesta"] or "(el modelo no devolvió texto)"):
        await update.effective_message.reply_text(trozo)


# --------------------------------------------------------------------------
# Arranque
# --------------------------------------------------------------------------

def _texto_fuente(herramientas):
    datos = herramientas.datos
    return (
        "Fuente: INEGI, Directorio Estadístico Nacional de Unidades Económicas "
        "(DENUE), edición 05/2026.\n"
        "Recorte: municipios de Tampico (%d establecimientos) y Ciudad Madero (%d), "
        "Tamaulipas; %d en total.\n"
        "Uso bajo los Términos de Libre Uso de la Información del INEGI." % (
            (datos["municipio"] == "Tampico").sum(),
            (datos["municipio"] == "Ciudad Madero").sum(),
            len(datos))
    )


def main(argv):
    load_dotenv()
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)  # en INFO imprime la URL, que contiene el token

    simulado = "--simulado" in argv
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Falta TELEGRAM_BOT_TOKEN. Cree su bot con @BotFather y escriba el token en .env.")
        return 1

    permitidos = leer_permitidos(os.environ.get("TELEGRAM_USUARIOS_PERMITIDOS", ""))
    if not permitidos:
        print("AVISO: TELEGRAM_USUARIOS_PERMITIDOS está vacío; el bot no atenderá a nadie.")
        print("Escríbale una vez a su bot para ver su identificador y agréguelo al .env.")

    herramientas = agente.cargar_herramientas()
    _, modelo = agente.crear_llamar(simulado)

    app = ApplicationBuilder().token(token).build()
    app.bot_data["permitidos"] = permitidos
    app.bot_data["simulado"] = simulado
    app.bot_data["herramientas"] = herramientas
    app.bot_data["sistema"] = agente.leer_sistema()
    app.bot_data["bitacora"] = agente.Bitacora(modelo)
    app.bot_data["contador"] = 0
    app.bot_data["texto_fuente"] = _texto_fuente(herramientas)

    app.add_handler(CommandHandler("start", inicio))
    app.add_handler(CommandHandler("fuente", fuente))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, pregunta))

    print("Bot corriendo (%s). Bitácora: %s. Ctrl+C para salir." % (modelo, app.bot_data["bitacora"].ruta))
    app.run_polling()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
