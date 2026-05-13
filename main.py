import os
import threading
from flask import Flask
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

# --- CONFIGURACIÓN DE INTELIGENCIA (MÁXIMA COMPATIBILIDAD) ---
genai.configure(api_key=GEMINI_KEY)

try:
    with open("prom_Oficial_Inteligencia.txt", "r", encoding="utf-8") as f:
        instrucciones_system = f.read()
except FileNotFoundError:
    instrucciones_system = "Eres el Oficial S-2 de GUN4FUN. Procede con protocolos estándar."

# RECALIBRACIÓN: Usamos el alias 'gemini-pro' que redirige automáticamente al modelo disponible
model = genai.GenerativeModel('gemini-1.5-flash') 

# --- LÓGICA DE RESPUESTA ---
async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    mensaje_texto = update.message.text
    
    try:
        # Intento A: Inyección directa de contexto para evitar errores de System Instruction
        prompt_completo = f"SISTEMA: {instrucciones_system}\n\nUSUARIO: {mensaje_texto}"
        
        response = model.generate_content(prompt_completo)
        
        if response and response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("⚠️ El núcleo no devolvió texto. Revise logs de seguridad.")
        
    except Exception as e:
        error_msg = str(e)
        print(f"--- ERROR CRÍTICO ---")
        print(error_msg)
        
        # Último aliento: Intento con el modelo 1.0 (el más compatible de la historia)
        try:
            fallback_model = genai.GenerativeModel('gemini-pro')
            res = fallback_model.generate_content(f"Responde como oficial de inteligencia: {mensaje_texto}")
            await update.message.reply_text(res.text)
        except Exception:
            await update.message.reply_text(f"❌ FALLO DE AUTORIZACIÓN: Su API KEY no es válida o está restringida por región.")

# --- LANZAMIENTO ---
def main():
    if not TELEGRAM_TOKEN or not GEMINI_KEY:
        print("ERROR: Faltan variables de entorno.")
        return

    threading.Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje))
    
    print("Oficial de Inteligencia S-2 en línea. ¡RELOAD!")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
