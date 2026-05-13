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
# Usamos la configuración estándar que no da problemas de argumentos
client = genai.Client(api_key=GEMINI_KEY)

try:
    with open("prom_Oficial_Inteligencia.txt", "r", encoding="utf-8") as f:
        instrucciones_sistema = f.read()
except FileNotFoundError:
    instrucciones_sistema = "Eres el Oficial S-2 de GUN4FUN. Procede con protocolos estándar."

model_id = "gemini-1.5-flash"

# --- LÓGICA DE RESPUESTA ---
async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    username = f"@{user.username}" if user.username else "Recluta"
    mensaje_texto = update.message.text
    
    try:
        # Simplificamos la configuración para evitar el Error 400
        # Pasamos las instrucciones dentro del config de forma limpia
        response = client.models.generate_content(
            model=model_id,
            config={'system_instruction': instrucciones_sistema},
            contents=mensaje_texto
        )
        
        if response and response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("⚠️ El núcleo no devolvió una respuesta válida.")
        
    except Exception as e:
        error_msg = str(e)
        print(f"--- ERROR TÁCTICO DETECTADO ---\n{error_msg}")
        
        # Si falla el flash, intentamos una llamada de emergencia sin system_instruction
        try:
            resp_emergencia = client.models.generate_content(
                model="gemini-1.5-pro",
                contents=f"{instrucciones_sistema}\n\nUsuario dice: {mensaje_texto}"
            )
            await update.message.reply_text(resp_emergencia.text)
        except Exception:
            await update.message.reply_text(f"❌ Error crítico en el núcleo: {error_msg[:50]}")

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
