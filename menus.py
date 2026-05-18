# menus.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
import database

# Definición estricta de los estados de la conversación
ESTADO_RAMA, ESTADO_SUBNODO = range(2)

def generar_menu_ramas() -> InlineKeyboardMarkup:
    """Extrae las ramas de Firebase y genera los botones interactivos."""
    mapa = database.obtener_mapa_superficial()
    teclado = []
    
    # Creamos un botón por cada Rama real en la base de datos
    for rama in sorted(mapa.keys()):
        # Mostramos un nombre limpio pero enviamos la clave exacta como callback_data
        nombre_limpio = rama.replace("_", " ").title()
        teclado.append([InlineKeyboardButton(f"📁 {nombre_limpio}", callback_data=f"rama:{rama}")])
        
    teclado.append([InlineKeyboardButton("❌ Cancelar Operación", callback_data="menu:cancelar")])
    return InlineKeyboardMarkup(teclado)

def generar_menu_subnodos(rama: str) -> InlineKeyboardMarkup:
    """Extrae los subnodos de una rama específica y genera sus botones."""
    mapa = database.obtener_mapa_superficial()
    subnodos = mapa.get(rama, [])
    teclado = []
    
    for subnodo in sorted(subnodos):
        nombre_limpio = subnodo.replace("_", " ").title()
        teclado.append([InlineKeyboardButton(f"📄 {nombre_limpio}", callback_data=f"subnodo:{subnodo}")])
        
    teclado.append([InlineKeyboardButton("⬅️ Volver al Índice", callback_data="menu:volver")])
    return InlineKeyboardMarkup(teclado)

async def activar_encuesta_indice(update: Update, context: ContextTypes.DEFAULT_TYPE, texto_alerta: str) -> int:
    """Activa el menú interactivo principal cuando no hay coincidencias."""
    teclado = generar_menu_ramas()
    
    mensaje = (
        f"⚠️ **REGISTRO NO ENCONTRADO**\n"
        f"Comandante, el término `{texto_alerta}` no consta en los archivos de acceso rápido.\n\n"
        f"📋 **ENCUESTA DEL ÍNDICE S-2**\n"
        f"Por favor, seleccione directamente en los botones de la interfaz qué división del conocimiento desea inspeccionar:"
    )
    
    # Verificamos si venimos de un mensaje de texto normal o de una actualización
    if update.message:
        await update.message.reply_text(mensaje, reply_markup=teclado, parse_mode="Markdown")
    return ESTADO_RAMA

async def procesar_seleccion_rama(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el clic sobre una rama y despliega sus subnodos."""
    query = update.callback_query
    await query.answer() # Confirma la recepción del clic a Telegram
    
    datos = query.data
    if datos == "menu:cancelar":
        await query.edit_message_text("📡 Navegación cancelada. Sistema S-2 regresando a modo de guardia táctica.")
        return ConversationHandler.END
        
    if datos.startswith("rama:"):
        rama_seleccionada = datos.split(":")[1]
        context.user_data["rama_seleccionada"] = rama_seleccionada
        
        teclado = generar_menu_subnodos(rama_seleccionada)
        nombre_rama_limpio = rama_seleccionada.replace("_", " ").title()
        
        await query.edit_message_text(
            text=f"📂 **DIVISIÓN SELECCIONADA:** {nombre_rama_limpio}\n\nSeleccione el archivo específico que requiere el análisis de inteligencia:",
            reply_markup=teclado,
            parse_mode="Markdown"
        )
        return ESTADO_SUBNODO
    
    return ESTADO_RAMA

async def procesar_seleccion_subnodo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el clic final sobre el subnodo y fuerza la respuesta analítica."""
    query = update.callback_query
    await query.answer()
    
    datos = query.data
    if datos == "menu:volver":
        teclado = generar_menu_ramas()
        await query.edit_message_text(
            text="📋 **ENCUESTA DEL ÍNDICE S-2**\nSeleccione la división del conocimiento que desea inspeccionar:",
            reply_markup=teclado,
            parse_mode="Markdown"
        )
        return ESTADO_RAMA
        
    if datos.startswith("subnodo:"):
        subnodo_seleccionado = datos.split(":")[1]
        
        # Le pasamos el control al flujo principal simulando que el usuario escribió el nombre exacto
        context.user_data["forzar_subnodo"] = subnodo_seleccionado
        
        await query.edit_message_text(f"⚡ *Extrayendo subnodo '{subnodo_seleccionado}' y analizando con Inteligencia Artificial...*", parse_mode="Markdown")
        
        # Finalizamos la conversación de menús para que el procesador de mensajes normal devuelva la respuesta de la IA
        # Para lograr esto de forma limpia, llamamos a la función encargada de ejecutar la IA en el main.py
        # Pero primero cerramos el estado FSM para liberar el chat.
        return ConversationHandler.END

    return ESTADO_SUBNODO

async def cancelar_navegacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Permite salir del menú interactivo usando el comando /cancelar."""
    await update.message.reply_text("📡 Comando recibido. Abortando encuesta del índice y regresando a escucha activa.")
    return ConversationHandler.END
