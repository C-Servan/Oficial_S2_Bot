import os
import threading
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- MINI SERVIDOR PARA RENDER ---
app = Flask(__name__)
@app.route('/')
def health_check():
    return "Oficial S-2 Operativo", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURACIÓN DE SEGURIDAD ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_KEY')

# --- CONFIGURACIÓN DE INTELIGENCIA ---
# RECALIBRACIÓN: Cliente con parámetros de compatibilidad total
client = genai.Client(api_key=GEMINI_KEY)

try:
    with open("prom_Oficial_Inteligencia.txt", "r", encoding="utf-8") as f:
        instrucciones_system = f.read()
except FileNotFoundError:
    instrucciones_system = "Eres el Oficial S-2 de GUN4FUN. Procede con protocolos estándar."

# IMPORTANTE: Usamos el nombre técnico largo para evitar el 404
model_id = "models/gemini-1.5-flash"

# --- LÓGICA DE RESPUESTA ---
async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    username = f"@{user.username}" if user.username else "Recluta"
    mensaje_texto = update.message.text
    
    try:
        # Intento A: Configuración estándar con nombre completo
        response = client.models.generate_content(
            model=model_id,
            config={'system_instruction': instrucciones_system},
            contents=mensaje_texto
        )
        
        if response and response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("⚠️ El núcleo no devolvió texto.")
        
    except Exception as e:
        error_msg = str(e)
        print(f"--- ERROR TÁCTICO DETECTADO ---\n{error_msg}")
        
        # Intento B (Modo Supervivencia): Sin System Instruction y con modelo Pro
        try:
            # Forzamos el modelo Pro con el nombre completo
            resp_emergencia = client.models.generate_content(
                model="models/gemini-1.5-pro",
                contents=f"INSTRUCCIONES: {instrucciones_system}\n\nUSUARIO: {mensaje_texto}"
            )
            await update.message.reply_text(resp_emergencia.text)
        except Exception as e2:
            await update.message.reply_text(f"❌ Fallo total del sistema API. Verifique cuotas o API Key.")

# --- LANZAMIENTO ---
def main():
    if not TELEGRAM_TOKEN or not GEMINI_KEY:
        print("Faltan credenciales.")
        return

    threading.Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje))
    
    print("Oficial de Inteligencia S-2 en línea. ¡RELOAD!")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
