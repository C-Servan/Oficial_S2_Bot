import os
import threading
import time
from flask import Flask
from groq import Groq
from mistralai.client import MistralClient as Mistral
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- MINI SERVIDOR PARA RENDER ---
app = Flask(__name__)
@app.route('/')
def health_check():
    # Actualizado para reflejar el nuevo estado multi-núcleo
    return "Oficial S-2 Operativo (Motor: Triple-IA)", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURACIÓN DE SEGURIDAD ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

# --- CONFIGURACIÓN DE INTELIGENCIA (TRIPLE NÚCLEO) ---
client_groq = Groq(api_key=GROQ_API_KEY)
client_mistral = Mistral(api_key=MISTRAL_API_KEY)
client_deepseek = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# Nombre del modelo Groq principal
MODELO_GROQ = "llama-3.3-70b-versatile"

try:
    with open("prom_Oficial_Inteligencia.txt", "r", encoding="utf-8") as f:
        instrucciones_system = f.read()
except FileNotFoundError:
    # Opción B: Personalidad base reforzada si falta el archivo
    instrucciones_system = (
        "Eres el Oficial de Inteligencia S-2 de la unidad GUN4FUN. "
        "Tu tono es militar, eficiente, directo y profesional. "
        "Tu misión es asesorar a las tropas y gestionar el flujo de información de combate."
    )

# --- LÓGICA DE RESPUESTA EN CASCADA (OPCIÓN A) ---
async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    mensaje_texto = update.message.text
    
    # 1. INTENTO CON GROQ (PLAN A)
    try:
        chat_completion = client_groq.chat.completions.create(
            model=MODELO_GROQ,
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
            return

    except Exception as e:
        print(f"⚠️ PLAN A (Groq) FALLIDO: {e}")

    # 2. INTENTO CON MISTRAL (PLAN B)
    if MISTRAL_API_KEY:
        try:
            print("🔄 Activando Plan B (Mistral)...")
            res_mistral = client_mistral.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "system", "content": instrucciones_system},
                    {"role": "user", "content": mensaje_texto}
                ]
            )
            await update.message.reply_text(res_mistral.choices[0].message.content)
            return
        except Exception as e2:
            print(f"⚠️ PLAN B (Mistral) FALLIDO: {e2}")

    # 3. INTENTO CON DEEPSEEK (PLAN C)
    if DEEPSEEK_API_KEY:
        try:
            print("🔄 Activando Plan C (DeepSeek)...")
            res_ds = client_deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": instrucciones_system},
                    {"role": "user", "content": mensaje_texto}
                ]
            )
            await update.message.reply_text(res_ds.choices[0].message.content)
            return
        except Exception as e3:
            print(f"⚠️ PLAN C (DeepSeek) FALLIDO: {e3}")

    # FALLBACK FINAL
    await update.message.reply_text("❌ INTERFERENCIA TOTAL: Todos los canales de inteligencia están saturados. Reintentar en 60 segundos.")

# --- LANZAMIENTO ---
def main():
    if not TELEGRAM_TOKEN:
        print("Falta TELEGRAM_TOKEN. Abortando misión.")
        return

    threading.Thread(target=run_flask, daemon=True).start()

    # Opción B: Añadimos un protocolo de reconexión similar al del Instructor
    while True:
        try:
            application = Application.builder().token(TELEGRAM_TOKEN).build()
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje))
            
            print("Oficial S-2 Triple-Core en línea. ¡RELOAD!")
            application.run_polling(drop_pending_updates=True)
        except Exception as e:
            print(f"⚠️ ERROR DE CONEXIÓN EN S-2: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
