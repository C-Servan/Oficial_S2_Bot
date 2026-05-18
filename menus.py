# menus.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
import database

# Definición estricta de los estados de la conversación
ESTADO_RAMA, ESTADO_SUBNODO = range(2)

# DICCIONARIO TÁCTICO: Títulos optimizados en longitud para evitar cortes y forzar centrado visual
MAPEO_TACTICO = {
    "1_Manuales_tecnicos": "⚙️ CONFIG. SISTEMAS / LIGHT GUNS",
    "2_Ecosistema_software": "🎮 EMULADORES Y SOFTWARE",
    # Las ramas "3_Archivo_historico" y "4_Protocolos_unidad" quedan capadas automáticamente al no incluirse aquí
}

def generar_menu_ramas() -> InlineKeyboardMarkup:
    """Genera botones limpios basados exclusivamente en el Mapeo Táctico autorizado."""
    mapa = database.obtener_mapa_superficial()
    teclado = []
    
    # Iteramos solo sobre las ramas permitidas y configuradas en nuestro filtro visual
    for rama in sorted(mapa.keys()):
        if rama in MAPEO_TACTICO:
            nombre_elegante = MAPEO_TACTICO[rama]
            teclado.append([InlineKeyboardButton(nombre_elegante, callback_data=f"rama:{rama}")])
        
    teclado.append([InlineKeyboardButton("❌ CANCELAR CONSULTA", callback_data="menu:cancelar")])
    return InlineKeyboardMarkup(teclado)

def generar_menu_subnodos(rama: str) -> InlineKeyboardMarkup:
    """Extrae los subnodos internos y les aplica un formato visual de archivo limpio."""
    mapa = database.obtener_mapa_superficial()
    subnodos = mapa.get(rama, [])
    teclado = []
    
    for subnodo in sorted(subnodos):
        # Embellecemos el subnodo técnico (ej: "openfire" -> "OPENFIRE")
        nombre_limpio = subnodo.replace("_", " ").upper()
        teclado.append([InlineKeyboardButton(f"📁 [ {nombre_limpio} ]", callback_data=f"subnodo:{subnodo}")])
        
    teclado.append([InlineKeyboardButton("⬅️ VOLVER AL ÍNDICE", callback_data="menu:volver")])
    return InlineKeyboardMarkup(teclado)

async def activar_encuesta_indice(update: Update, context: ContextTypes.DEFAULT_TYPE, texto_alerta: str) -> int:
    """Activa el menú interactivo principal cuando no hay coincidencias directas en el texto."""
    teclado = generar_menu_ramas()
    
    # Se extrae el rango dinámicamente según las directivas del sistema
    user = update.message.from_user if update.message else update.callback_query.from_user
    username = f"@{user.username}" if user.username else user.first_name
    
    if username.lower() == "@carlosfservan":
        rango = "Comandante"
    elif username.lower() in ["@gargarensis76", "@gwyllion16"]:
        rango = "Sargento"
    else:
        rango = "Recluta"

    mensaje = (
        f"⚠️ **REGISTRO NO ENCONTRADO**\n"
        f"{rango}, los parámetros solicitados no constan en los índices de acceso rápido.\n\n"
        f"📋 **SISTEMA DE ASISTENCIA DIRECTA S-2**\n"
        f"Por favor, seleccione directamente en la interfaz el sector de inteligencia a inspeccionar:"
    )
    
    if update.message:
        await update.message.reply_text(mensaje, reply_markup=teclado, parse_mode="Markdown")
    return ESTADO_RAMA

async def procesar_seleccion_rama(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el clic sobre una rama autorizada y despliega sus subnodos de configuración."""
    query = update.callback_query
    await query.answer() # Libera el estado de carga en los servidores de Telegram inmediatamente
    
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
            text=f"📂 **DIVISIÓN ACTIVA:**\n*{nombre_rama_limpio}*\n\nSeleccione el archivo específico para desplegar el manual táctico:",
            reply_markup=teclado,
            parse_mode="Markdown"
        )
        return ESTADO_SUBNODO
    
    return ESTADO_RAMA

async def procesar_seleccion_subnodo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el clic sobre el subnodo final, inyecta la solución y cierra la conversación de forma segura."""
    query = update.callback_query
    await query.answer() # Libera el callback de inmediato para evitar el bucle "Cargando..."
    
    datos = query.data
    if datos == "menu:volver":
        teclado = generar_menu_ramas()
        await query.edit_message_text(
            text="📋 **SISTEMA DE ASISTENCIA DIRECTA S-2**\nSeleccione la categoría de inteligencia que desea inspeccionar:",
            reply_markup=teclado,
            parse_mode="Markdown"
        )
        return ESTADO_RAMA
        
    if datos.startswith("subnodo:"):
        subnodo_seleccionado = datos.split(":")[1]
        
        # Fijamos de forma estricta en la sesión el subnodo elegido para saltar la búsqueda libre
        context.user_data["forzar_subnodo"] = subnodo_seleccionado
        
        await query.edit_message_text(f"⚡ *Extrayendo registros de [ {subnodo_seleccionado.upper()} ] y procesando con cascada de IA...*", parse_mode="Markdown")
        
        # EVITAMOS IMPORTACIÓN CIRCULAR: Importamos el procesador principal bajo demanda
        import main
        
        # Sincronizamos de manera segura el texto para el analizador secundario
        if query.message:
            query.message.text = subnodo_seleccionado
            
        # Ejecutamos el procesamiento sin bloquear la máquina de estados nativa de la botonera
        asyncio.create_task(main.procesar_mensaje(update, context))
        
        return ConversationHandler.END

    return ESTADO_SUBNODO

async def cancelar_navegacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Permite abortar la interfaz del menú interactivo mediante comandos del sistema."""
    await update.message.reply_text("📡 Operación abortada. Regresando a modo de guardia táctica.")
    return ConversationHandler.END
