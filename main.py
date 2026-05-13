import os
import threading
from flask import Flask
# CAMBIO A LIBRERÍA ESTABLE
import google.generativeai as genai
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

# --- CONFIGURACIÓN DE INTELIGENCIA (MODO ESTABLE) ---
genai.configure(api_key=GEMINI_KEY)

try:
    with open("prom_Oficial_Inteligencia.txt", "r", encoding="utf-8") as f:
        instrucciones_system = f.read()
except FileNotFoundError:
    instrucciones_system = "Eres el Oficial S-2 de GUN4FUN. Procede con protocolos estándar."

# Configuración del modelo clásico
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=instrucciones_system
)

# --- LÓGICA DE RESPUESTA ---
async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    mensaje_texto = update.message.text
    
    try:
        # Generación con la librería estándar de Google
        response = model.generate_content(mensaje_texto)
        
        if response and response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("⚠️ El núcleo no devolvió texto.")
        
    except Exception as e:
        error_msg = str(e)
        print(f"--- ERROR TÁCTICO DETECTADO ---\n{error_msg}")
        
        # Fallback directo si falla el sistema de instrucciones
        try:
            model_alt = genai.GenerativeModel("gemini-1.5-flash")
            resp_alt = model_alt.generate_content(f"{instrucciones_system}\n\nPregunta: {mensaje_texto}")
            await update.message.reply_text(resp_alt.text)
        except Exception:
            await update.message.reply_text(f"❌ Error de API: Verifique si su API KEY tiene acceso a Gemini 1.5.")

# --- LANZAMIENTO ---
def main():
    if not TELEGRAM_TOKEN or not GEMINI_KEY:
        return

    threading.Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje))
    
    print("Oficial de Inteligencia S-2 en línea. ¡RELOAD!")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
