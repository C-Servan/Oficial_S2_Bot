import os
import threading
from flask import Flask
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- MINI SERVIDOR PARA RENDER ---
app = Flask(_name_)
@app.route('/')
def health_check():
    return "Oficial S-2 Operativo", 200

def run_flask():
    # Render asigna un puerto automáticamente en la variable PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURACIÓN DE SEGURIDAD (Se rellenará en Render) ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_KEY')

# --- CONFIGURACIÓN DE INTELIGENCIA ---
genai.configure(api_key=GEMINI_KEY)

# Intentar cargar el manual de inteligencia desde el archivo txt que subiste
try:
    with open("prom_Oficial_Inteligencia.txt", "r", encoding="utf-8") as f:
        instrucciones_sistema = f.read()
except FileNotFoundError:
    instrucciones_sistema = "Eres el Oficial S-2 de GUN4FUN. Manual no encontrado. Procede con protocolos estándar."

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=instrucciones_sistema
)

# --- LÓGICA DE RESPUESTA ---
async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    username = f"@{user.username}" if user.username else "Recluta"
    mensaje_texto = update.message.text

    # El bot sabe quién le habla para aplicar la jerarquía del manual
    contexto_usuario = f"[Mensaje de {username}]: "
    
    chat = model.start_chat(history=[])
    response = chat.send_message(contexto_usuario + mensaje_texto)
    
    await update.message.reply_text(response.text)

# --- LANZAMIENTO ---
def main():
    if not TELEGRAM_TOKEN or not GEMINI_KEY:
        print("ERROR: Faltan las llaves de acceso en las variables de entorno.")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje))
    
    print("Oficial de Inteligencia S-2 en línea. ¡RELOAD!")
    application.run_polling()

if __name__ == "__main__":
    main()
