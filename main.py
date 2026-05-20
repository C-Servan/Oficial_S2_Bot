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
    filters, 
    ContextTypes
)

# Inyección de módulos tácticos
import database
import ai_cascade

# --- 1. CONFIGURACIÓN DEL SERVIDOR WEB (RENDER) ---
app = Flask(__name__)
@app.route('/')
def health_check():
    return "Oficial S-2 Operativo (Arquitectura Estática)", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. PROCESADOR PRINCIPAL ---
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

    # A. COMANDO DE INGESTA TÁCTICA (/guardar)
    if not is_callback and data.startswith("/guardar"):
        partes = data.replace("/guardar", "").split("|")
        if len(partes) == 5:
            if database.guardar_manual_estructurado(*[p.strip() for p in partes]):
                await msg_obj.reply_text("✅ [S-2] Manual inyectado en la base de datos con éxito.")
            else:
                await msg_obj.reply_text("❌ [S-2] Error de escritura. Verifique el formato.")
        else:
            await msg_obj.reply_text("⚠️ Formato: /guardar ruta | titulo | texto | imgs | vids")
        return

    # B. NAVEGACIÓN DIRECTA (BOTONES 'nav:')
    if is_callback and data.startswith("nav:"):
        ruta = data.replace("nav:", "")
        datos = database.obtener_datos_nodo(ruta)
        
        if datos:
            # Si el "vídeo" es en realidad un enlace a PDF de Google Drive, lo enviamos como documento
            vids = datos.get('videos', [])
            is_pdf = vids and "drive.google.com" in vids[0]
            
            if is_pdf:
                await context.bot.send_document(
                    chat_id=destino_chat_id, 
                    document=vids[0], 
                    caption=f"📄 *{datos.get('titulo')}*\nManual táctico solicitado."
                )
            else:
                respuesta = f"*{datos.get('titulo', 'Manual S-2')}*\n\n{datos.get('texto_manual', '')}"
                await context.bot.send_message(chat_id=destino_chat_id, text=respuesta, parse_mode="Markdown")
        else:
            await msg_obj.reply_text("⚠️ [S-2] Nodo táctico vacío o inexistente.")
        return

    # C. CONSULTA ABIERTA (IA DE RESPALDO)
    if not is_callback:
        await msg_obj.reply_text("📡 Transmisión recibida. Procesando consulta...")
        # Lógica de IA existente aquí...

# --- 3. LANZAMIENTO Y CONFIGURACIÓN ASÍNCRONA ---
async def start_bot():
    application = Application.builder().token(ai_cascade.TELEGRAM_TOKEN).build()
    
    # Handlers
    application.add_handler(CallbackQueryHandler(procesar_mensaje, pattern="^nav:"))
    application.add_handler(CommandHandler("guardar", procesar_mensaje))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), procesar_mensaje))

    print("🚀 Oficial S-2 en línea. Arquitectura Estática Activa.")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await application.stop()
        await application.shutdown()

def main():
    if not ai_cascade.TELEGRAM_TOKEN:
        return

    print("📡 Iniciando servidor web de telemetría...")
    threading.Thread(target=run_flask, daemon=True).start()

    # Ejecución asíncrona controlada
    asyncio.run(start_bot())

if __name__ == "__main__":
    main()
