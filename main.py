import os
import threading
import asyncio
import logging
from flask import Flask
from telegram import Update
from telegram.ext import (
    Application, 
    MessageHandler, 
    CommandHandler, 
    CallbackQueryHandler, 
    ConversationHandler,
    filters, 
    ContextTypes
)

# Inyección de módulos tácticos
import database
import ai_cascade
import menus

# --- 1. CONFIGURACIÓN DEL SERVIDOR WEB (RENDER) ---
app = Flask(__name__)
@app.route('/')
def health_check():
    return "Oficial S-2 Operativo (Arquitectura Estática)", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. PROCESADORES DE COMANDOS (Prioridad 1) ---
async def ejecutar_ingesta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja exclusivamente el comando /guardar."""
    data = update.message.text.strip()
    partes = data.replace("/guardar", "").split("|")
    if len(partes) == 5:
        if database.guardar_manual_estructurado(*[p.strip() for p in partes]):
            await update.message.reply_text("✅ [S-2] Manual inyectado con éxito.")
        else:
            await update.message.reply_text("❌ [S-2] Error de escritura.")
    else:
        await update.message.reply_text("⚠️ Formato: /guardar ruta | titulo | texto | imgs | vids")

# --- 3. PROCESADOR DE NAVEGACIÓN Y CONSULTA (Prioridad 2 y 3) ---
async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_callback = update.callback_query is not None
    destino_chat_id = update.effective_chat.id
    
    if is_callback:
        msg_obj = update.callback_query.message
        data = update.callback_query.data
        try: await update.callback_query.answer()
        except: pass
    else:
        if not update.message or not update.message.text: return
        msg_obj = update.message
        data = update.message.text.strip()

    # MEDIDA DE SEGURIDAD: Bloquear comandos residuales que intenten entrar como texto plano
    if not is_callback and data.startswith("/"):
        if data.startswith("/ayuda"):
            # Si entra por texto plano, inicializamos el flujo interactivo de menús
            await menus.activar_encuesta_indice(update, context)
        return

    # NAVEGACIÓN (Lectura final de nodos en Firebase)
    if is_callback and data.startswith("nav:"):
        ruta = data.replace("nav:", "")
        datos = database.obtener_datos_nodo(ruta)
        if datos:
            # Dado que la estructura real tiene subniveles (configuracion, faq), 
            # verificamos si devuelve texto directo o subcategorías
            titulo = datos.get('titulo', 'Manual S-2')
            texto = datos.get('texto_manual', '')
            
            if not texto:
                # Si el nodo contiene más carpetas hijas, listamos sus claves
                claves_internas = [k.replace("_", " ").upper() for k in datos.keys() if isinstance(datos[k], dict)]
                if claves_internas:
                    texto = f"Este sistema contiene las siguientes secciones disponibles:\n" + "\n".join([f"🔹 {c}" for c in claves_internas])
                else:
                    texto = "Registro vacío o estructura profunda no indexada."

            vids = datos.get('videos', [])
            if vids and "drive.google.com" in vids[0]:
                await context.bot.send_document(chat_id=destino_chat_id, document=vids[0], caption=f"📄 *{titulo}*")
            else:
                await context.bot.send_message(chat_id=destino_chat_id, text=f"*{titulo}*\n\n{texto}", parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=destino_chat_id, text="❌ Archivo no encontrado en el sector especificado.")
        return

    # CONSULTA ABIERTA (IA - Solo texto puro)
    if not is_callback:
        respuesta_ia, canal = ai_cascade.procesar_consulta_directa(
            data, 
            str(database.obtener_datos_nodo("GLOBAL")), 
            update.message.from_user.username
        )
        nombre_canal = canal.replace("Canal ", "").strip()
        await msg_obj.reply_text(f"📡 [Comunicación canal - {nombre_canal}]\n\n{respuesta_ia}", parse_mode="Markdown")

# --- 4. LANZAMIENTO Y CONFIGURACIÓN ---
async def start_bot():
    application = Application.builder().token(ai_cascade.TELEGRAM_TOKEN).build()
    
    # Prioridad 1: Comando Ingesta Directa
    application.add_handler(CommandHandler("guardar", ejecutar_ingesta))
    
    # CONVERSATION HANDLER: Control absoluto del flujo interactivo del menú /ayuda
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("ayuda", menus.activar_encuesta_indice)],
        states={
            menus.ESTADO_RAMA: [
                CallbackQueryHandler(menus.procesar_seleccion_rama, pattern="^rama:"),
                CallbackQueryHandler(menus.procesar_seleccion_rama, pattern="^menu:cancelar")
            ],
            menus.ESTADO_SUBNODO: [
                CallbackQueryHandler(menus.procesar_seleccion_subnodo, pattern="^subnodo:"),
                CallbackQueryHandler(menus.procesar_seleccion_subnodo, pattern="^menu:volver")
            ]
        },
        fallbacks=[CommandHandler("ayuda", menus.activar_encuesta_indice)],
        allow_reentry=True
    )
    application.add_handler(conv_handler)
    
    # Callbacks de extracción final de manuales
    application.add_handler(CallbackQueryHandler(procesar_mensaje, pattern="^nav:"))
    
    # Prioridad 3: Mensajes de texto analizados por la IA
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), procesar_mensaje))

    print("🚀 Oficial S-2 en línea. Sistema de Menús Interactivos Sincronizado.")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    try:
        while True: await asyncio.sleep(1)
    finally:
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(start_bot())
