import os
import threading
import json
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
    # Detección de origen
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
        # Sintaxis: /guardar ruta | titulo | texto | imgs | vids
        partes = data.replace("/guardar", "").split("|")
        if len(partes) == 5:
            if database.guardar_manual_estructurado(*[p.strip() for p in partes]):
                await msg_obj.reply_text("✅ [S-2] Manual inyectado en la base de datos con éxito.")
            else:
                await msg_obj.reply_text("❌ [S-2] Error de escritura. Verifique el formato.")
        else:
            await msg_obj.reply_text("⚠️ Formato incorrecto. Use: /guardar ruta | titulo | texto | imgs | vids")
        return

    # B. NAVEGACIÓN DIRECTA (BOTONES 'nav:')
    if is_callback and data.startswith("nav:"):
        ruta = data.replace("nav:", "")
        datos = database.obtener_datos_nodo(ruta)
        
        if datos:
            # Construcción del reporte tipo conversación
            respuesta = f"*{datos.get('titulo', 'Manual S-2')}*\n\n{datos.get('texto_manual', '')}"
            
            # Gestión multimedia
            imgs = datos.get('imagenes', [])
            vids = datos.get('videos', [])
            if imgs and len(imgs) > 0: 
                respuesta += "\n\n📷 **Recursos Visuales:**\n" + "\n".join([f"• {i}" for i in imgs])
            if vids and len(vids) > 0: 
                respuesta += "\n\n🎥 **Recursos Audiovisuales:**\n" + "\n".join([f"• {v}" for v in vids])
            
            await context.bot.send_message(chat_id=destino_chat_id, text=respuesta, parse_mode="Markdown")
        else:
            await msg_obj.reply_text("⚠️ [S-2] Nodo táctico vacío o inexistente.")
        return

    # C. CONSULTA ABIERTA (IA DE RESPALDO)
    if not is_callback:
        await msg_obj.reply_text("📡 Transmisión recibida. Procesando consulta mediante IA de respaldo...")
        # Aquí mantendríamos la lógica de ai_cascade.procesar_consulta_directa si la pregunta no es navegación
        # ... (Tu lógica de IA existente) ...

# --- 3. LANZAMIENTO DEL SISTEMA ---
def main():
    if not ai_cascade.TELEGRAM_TOKEN:
        return

    print("📡 Iniciando servidor web de telemetría...")
    threading.Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(ai_cascade.TELEGRAM_TOKEN).build()
    
    # Handlers
    application.add_handler(CallbackQueryHandler(procesar_mensaje, pattern="^nav:"))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), procesar_mensaje))
    application.add_handler(CommandHandler("guardar", procesar_mensaje))

    print("🚀 Oficial S-2 en línea. Arquitectura Estática Activa.")
    application.run_polling()

if __name__ == "__main__":
    main()
