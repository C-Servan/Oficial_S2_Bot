import os
import threading
from flask import Flask
from groq import Groq
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- MINI SERVIDOR PARA RENDER ---
app = Flask(__name__)
@app.route('/')
def health_check():
    return "Oficial S-2 Operativo (Motor: Llama-3)", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURACIÓN DE SEGURIDAD ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY') # Cambia el nombre en Render de GEMINI_KEY a GROQ_API_KEY

# --- CONFIGURACIÓN DE INTELIGENCIA (GROQ/LLAMA-3) ---
client = Groq(api_key=GROQ_API_KEY)

try:
    with open("prom_Oficial_Inteligencia.txt", "r", encoding="utf-8") as f:
        instrucciones_system = f.read()
except FileNotFoundError:
    instrucciones_system = "Eres el Oficial S-2 de GUN4FUN. Procede con protocolos estándar."

# --- LÓGICA DE RESPUESTA ---
async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    mensaje_texto = update.message.text
    
    try:
        # Petición de chat a Groq usando Llama-3-70b (potente y rápido)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": instrucciones_system,
                },
                {
                    "role": "user",
                    "content": mensaje_texto,
                }
            ],
            model="llama3-70b-8192",
        )
        
        respuesta = chat_completion.choices[0].message.content
        
        if respuesta:
            await update.message.reply_text(respuesta)
        else:
            await update.message.reply_text("⚠️ El núcleo de Groq no devolvió texto.")
        
    except Exception as e:
        print(f"--- ERROR CRÍTICO EN GROQ ---\n{e}")
        await update.message.reply_text(f"❌ Error de enlace: {str(e)[:50]}")

# --- LANZAMIENTO ---
def main():
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        print("Faltan variables: TELEGRAM_TOKEN o GROQ_API_KEY")
        return

    threading.Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje))
    
    print("Oficial de Inteligencia S-2 en línea (Motor Groq). ¡RELOAD!")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
