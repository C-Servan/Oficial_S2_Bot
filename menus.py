from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
import database
import asyncio

# Definición estricta de los estados de la conversación
ESTADO_RAMA, ESTADO_SUBNODO = range(2)

# DICCIONARIO TÁCTICO
MAPEO_TACTICO = {
    "1_Manuales_tecnicos": "⚙️ CONFIG. SISTEMAS / LIGHT GUNS",
    "2_Ecosistema_software": "🎮 EMULADORES Y SOFTWARE",
}

def generar_menu_ramas() -> InlineKeyboardMarkup:
    mapa = database.obtener_mapa_superficial()
    teclado = []
    
    for rama in sorted(mapa.keys()):
        if rama in MAPEO_TACTICO:
            nombre_elegante = MAPEO_TACTICO[rama]
            teclado.append([InlineKeyboardButton(nombre_elegante, callback_data=f"rama:{rama}")])
        
    teclado.append([InlineKeyboardButton("❌ CANCELAR CONSULTA", callback_data="menu:cancelar")])
    return InlineKeyboardMarkup(teclado)

def generar_menu_subnodos(rama: str) -> InlineKeyboardMarkup:
    mapa = database.obtener_mapa_superficial()
    subnodos = mapa.get(rama, [])
    teclado = []
    
    for subnodo in sorted(subnodos):
        nombre_limpio = subnodo.replace("_", " ").upper()
        teclado.append([InlineKeyboardButton(f"📁 [ {nombre_limpio} ]", callback_data=f"subnodo:{subnodo}")])
        
    teclado.append([InlineKeyboardButton("⬅️ VOLVER AL ÍNDICE", callback_data="menu:volver")])
    return InlineKeyboardMarkup(teclado)

async def activar_encuesta_indice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa el menú principal."""
    teclado = generar_menu_ramas()
    
    user = update.message.from_user if update.message else update.callback_query.from_user
    username = f"@{user.username}" if user.username else user.first_name
    
    rango = "Comandante" if username.lower() == "@carlosfservan" else ("Sargento" if username.lower() in ["@gargarensis76", "@gwyllion16"] else "Recluta")

    mensaje = (
        f"📋 **SISTEMA DE ASISTENCIA DIRECTA S-2**\n"
        f"{rango}, seleccione el sector de inteligencia a inspeccionar:"
    )
    
    if update.message:
        await update.message.reply_text(mensaje, reply_markup=teclado, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(mensaje, reply_markup=teclado, parse_mode="Markdown")

async def procesar_seleccion_rama(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    datos = query.data
    if datos == "menu:cancelar":
        await query.edit_message_text("📡 Transmisión finalizada. Sistema S-2 en modo de escucha activa.")
        return ConversationHandler.END
        
    if datos.startswith("rama:"):
        rama_seleccionada = datos.split(":")[1]
        context.user_data["rama_seleccionada"] = rama_seleccionada
        
        teclado = generar_menu_subnodos(rama_seleccionada)
        nombre_rama_limpio = MAPEO_TACTICO.get(rama_seleccionada, rama_seleccionada.replace("_", " ").upper())
        
        await query.edit_message_text(
            text=f"📂 **DIVISIÓN ACTIVA:**\n*{nombre_rama_limpio}*\n\nSeleccione el archivo específico:",
            reply_markup=teclado,
            parse_mode="Markdown"
        )
        return ESTADO_SUBNODO
    
    return ESTADO_RAMA

async def procesar_seleccion_subnodo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    datos = query.data
    if datos == "menu:volver":
        teclado = generar_menu_ramas()
        await query.edit_message_text(
            text="📋 **SISTEMA DE ASISTENCIA DIRECTA S-2**\nSeleccione la categoría de inteligencia:",
            reply_markup=teclado,
            parse_mode="Markdown"
        )
        return ESTADO_RAMA
        
    if datos.startswith("subnodo:"):
        subnodo_seleccionado = datos.split(":")[1]
        rama = context.user_data.get("rama_seleccionada", "")
        ruta_completa = f"{rama}/{subnodo_seleccionado}"
        
        await query.edit_message_text(f"⚡ *Extrayendo registros de [ {ruta_completa.upper()} ]...*", parse_mode="Markdown")
        
        # En lugar de importar main aquí, delegamos el proceso final al bot
        # Simulamos un callback para disparar la lógica de navegación de main
        query.data = f"nav:{ruta_completa}"
        import main
        await main.procesar_mensaje(update, context)
        return ConversationHandler.END

    return ESTADO_SUBNODO
