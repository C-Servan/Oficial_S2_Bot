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
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# --- CONFIGURACIÓN DE INTELIGENCIA (GROQ) ---
client = Groq(api_key=GROQ_API_KEY)

# Nombre del modelo actualizado y ultra-estable
MODELO_ACTUAL = "llama-3.3-70b-versatile"

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
        # Petición simplificada para evitar Error 400
        chat_completion = client.chat.completions.create(
            model=MODELO_ACTUAL,
            messages=[
                {"role": "system", "content": instrucciones_system},
                {"role": "user", "content": mensaje_texto}
            ],
            temperature=0.7,
            max_tokens=2048
        )
        
        respuesta = chat_completion.choices[0].message.content
        
        if respuesta:
            await update.message.reply_text(respuesta)
        else:
            await update.message.reply_text("⚠️ El núcleo de Groq no devolvió texto.")
        
    except Exception as e:
        error_str = str(e)
        print(f"--- ERROR EN GROQ ---\n{error_str}")
        
        # Fallback de emergencia si el modelo específico no existe
        if "404" in error_str or "model" in error_str:
            try:
                # Intento con el modelo pequeño (siempre disponible)
                res_backup = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[{"role": "user", "content": mensaje_texto}]
                )
                await update.message.reply_text(res_backup.choices[0].message.content)
            except Exception:
                await update.message.reply_text(f"❌ Error de configuración de modelo en Groq.")
        else:
            await update.message.reply_text(f"❌ Error de enlace: {error_str[:60]}...")

# --- LANZAMIENTO ---
def main():
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        return

    threading.Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje))
    
    print("Oficial de Inteligencia S-2 en línea (Motor Groq). ¡RELOAD!")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
