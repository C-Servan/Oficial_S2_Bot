from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
import database
import traceback

# Definición estricta de los estados de la conversación
ESTADO_RAMA, ESTADO_SUBNODO = range(2)

# DICCIONARIO TÁCTICO CORREGIDO (Alineación exacta con tus capturas de Firebase)
MAPEO_TACTICO = {
    "1_light_guns": "🔫 LIGHT GUNS / HARDWARE",
    "2_sistemas": "🎮 SISTEMAS Y EMULADORES",
}

def generar_menu_ramas(mapa) -> InlineKeyboardMarkup:
    teclado = []
    
    for rama in sorted(mapa.keys()):
        nombre_elegante = MAPEO_TACTICO.get(rama, rama.replace("_", " ").upper())
        teclado.append([InlineKeyboardButton(nombre_elegante, callback_data=f"rama:{rama}")])
            
    teclado.append([InlineKeyboardButton("❌ CANCELAR CONSULTA", callback_data="menu:cancelar")])
    return InlineKeyboardMarkup(teclado)

def generar_menu_subnodos(rama: str, mapa: dict) -> InlineKeyboardMarkup:
    subnodos = mapa.get(rama, [])
    teclado = []
    
    for subnodo in sorted(subnodos):
        nombre_limpio = subnodo.replace("_", " ").upper()
        teclado.append([InlineKeyboardButton(f"📁 [ {nombre_limpio} ]", callback_data=f"subnodo:{subnodo}")])
        
    teclado.append([InlineKeyboardButton("⬅️ VOLVER AL ÍNDICE", callback_data="menu:volver")])
    return InlineKeyboardMarkup(teclado)

async def activar_encuesta_indice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Activa el menú interactivo principal mapeando las carpetas de Firebase."""
    try:
        mapa = database.obtener_mapa_superficial() or {}
        teclado = generar_menu_ramas(mapa)
        
        user = update.message.from_user if update.message else update.callback_query.from_user
        username = f"@{user.username}" if user.username else user.first_name
        
        if username.lower() == "@carlosfservan":
            rango = "Comandante"
        elif username.lower() in ["@gargarensis76", "@gwyllion16"]:
            rango = "Sargento"
        else:
            rango = "Recluta"

        mensaje = (
            f"📋 *SISTEMA DE ASISTENCIA DIRECTA S-2*\n"
            f"{rango}, seleccione el sector de inteligencia a inspeccionar:"
        )
        
        if update.message:
            await update.message.reply_text(mensaje, reply_markup=teclado, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.message.reply_text(mensaje, reply_markup=teclado, parse_mode="Markdown")
            
        return ESTADO_RAMA
            
    except Exception as e:
        error_txt = f"❌ [ERROR S-2 CRÍTICO] Fallo en interfaz:\n`{e}`"
        print(traceback.format_exc())
        if update.message:
            await update.message.reply_text(error_txt, parse_mode="Markdown")
        return ConversationHandler.END

async def procesar_seleccion_rama(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la rama elegida y despliega sus subnodos."""
    query = update.callback_query
    await query.answer()
    
    datos = query.data
    if datos == "menu:cancelar":
        await query.edit_message_text("📡 Transmisión finalizada. Sistema S-2 en modo de escucha activa.")
        return ConversationHandler.END
        
    if datos.startswith("rama:"):
        rama_seleccionada = datos.split(":")[1]
        context.user_data["rama_seleccionada"] = rama_seleccionada
        
        mapa = database.obtener_mapa_superficial() or {}
        teclado = generar_menu_subnodos(rama_seleccionada, mapa)
        nombre_rama_limpio = MAPEO_TACTICO.get(rama_seleccionada, rama_seleccionada.replace("_", " ").upper())
        
        await query.edit_message_text(
            text=f"📂 *DIVISIÓN ACTIVA:*\n*{nombre_rama_limpio}*\n\nSeleccione el archivo específico:",
            reply_markup=teclado,
            parse_mode="Markdown"
        )
        return ESTADO_SUBNODO
    
    return ESTADO_RAMA

async def procesar_seleccion_subnodo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el subnodo y redirige al lector de manuales de main.py."""
    query = update.callback_query
    await query.answer()
    
    datos = query.data
    if datos == "menu:volver":
        mapa = database.obtener_mapa_superficial() or {}
        teclado = generar_menu_ramas(mapa)
        await query.edit_message_text(
            text="📋 *SISTEMA DE ASISTENCIA DIRECTA S-2*\nSeleccione la categoría de inteligencia:",
            reply_markup=teclado,
            parse_mode="Markdown"
        )
        return ESTADO_RAMA
        
    if datos.startswith("subnodo:"):
        subnodo_seleccionado = datos.split(":")[1]
        rama = context.user_data.get("rama_seleccionada", "")
        ruta_completa = f"{rama}/{subnodo_seleccionado}"
        
        await query.edit_message_text(f"⚡ *Extrayendo registros de [ {subnodo_seleccionado.upper()} ]...*", parse_mode="Markdown")
        
        # Inyectamos la ruta en los datos de navegación y saltamos a main.py
        query.data = f"nav:{ruta_completa}"
        import main
        await main.procesar_mensaje(update, context)
        return ConversationHandler.END

    return ESTADO_SUBNODO
