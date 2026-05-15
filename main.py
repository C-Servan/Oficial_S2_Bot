import os
import threading
import time
import json
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask
from groq import Groq
from mistralai import Mistral
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- 1. CONFIGURACIÓN FIREBASE (ENCICLOPEDIA S-2) ---
# Intentamos cargar las credenciales desde una variable de entorno en Render
firebase_creds_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')

if firebase_creds_json:
    try:
        creds_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://gun4fun-ranking-default-rtdb.europe-west1.firebasedatabase.app/'
        })
        print("✅ Conexión a la Enciclopedia S-2 establecida.")
    except Exception as e:
        print(f"❌ Error al inicializar Firebase: {e}")

def obtener_datos_enciclopedia():
    """Recupera toda la sabiduría almacenada para dar contexto a la IA"""
    try:
        ref = db.reference('Enciclopedia_S2')
        datos = ref.get()
        if not datos:
            return "No hay datos registrados en la enciclopedia aún."
        
        # Formateamos los datos para que la IA los entienda como manuales
        contexto = "SABIDURÍA ACTUAL DE LA UNIDAD (Usa esto para responder):\n"
        contexto += json.dumps(datos, indent=2, ensure_ascii=False)
        return contexto
    except Exception as e:
        print(f"Error leyendo base de datos: {e}")
        return ""

# --- 2. CONFIGURACIÓN DEL SERVIDOR WEB ---
app = Flask(__name__)
@app.route('/')
def health_check():
    return "Oficial S-2 Operativo (Motor: Triple-IA + Enciclopedia)", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 3. CONFIGURACIÓN DE SEGURIDAD Y CLIENTES IA ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

client_groq = Groq(api_key=GROQ_API_KEY)
client_mistral = Mistral(api_key=MISTRAL_API_KEY)
client_deepseek = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

MODELO_GROQ = "llama-3.3-70b-versatile"

try:
    with open("prom_Oficial_Inteligencia.txt", "r", encoding="utf-8") as f:
        instrucciones_base = f.read()
except FileNotFoundError:
    instrucciones_base = (
        "Eres el Oficial de Inteligencia S-2 de la unidad GUN4FUN. "
        "Tu misión es ser una enciclopedia del mundo Lightgun. NO INVENTES DATOS. "
        "Si la información no está en los manuales proporcionados, di que no consta en los registros."
    )

# --- 4. LÓGICA DE RESPUESTA EN CASCADA CON CONTEXTO REAL ---
async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    mensaje_usuario = update.message.text
    
    # PASO CLAVE: Obtenemos los datos reales de Firebase
    contexto_real = obtener_datos_enciclopedia()
    
    # Creamos el sistema de instrucciones sumando el Prompt + la Base de Datos
    instrucciones_con_sabiduria = f"{instrucciones_base}\n\n{contexto_real}"

    # --- PLAN A: GROQ ---
    try:
        chat_completion = client_groq.chat.completions.create(
            model=MODELO_GROQ,
            messages=[
                {"role": "system", "content": instrucciones_con_sabiduria},
                {"role": "user", "content": mensaje_usuario}
            ],
            temperature=0.3, # Bajamos temperatura para evitar inventos
            max_tokens=2048
        )
        respuesta = chat_completion.choices[0].message.content
        if respuesta:
            await update.message.reply_text(respuesta)
            return
    except Exception as e:
        print(f"⚠️ PLAN A FALLIDO: {e}")

    # --- PLAN B: MISTRAL ---
    if MISTRAL_API_KEY:
        try:
            res_mistral = client_mistral.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "system", "content": instrucciones_con_sabiduria},
                    {"role": "user", "content": mensaje_usuario}
                ]
            )
            await update.message.reply_text(res_mistral.choices[0].message.content)
            return
        except Exception as e2:
            print(f"⚠️ PLAN B FALLIDO: {e2}")

    # --- PLAN C: DEEPSEEK ---
    if DEEPSEEK_API_KEY:
        try:
            res_ds = client_deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": instrucciones_con_sabiduria},
                    {"role": "user", "content": mensaje_usuario}
                ]
            )
            await update.message.reply_text(res_ds.choices[0].message.content)
            return
        except Exception as e3:
            print(f"⚠️ PLAN C FALLIDO: {e3}")

    await update.message.reply_text("❌ INTERFERENCIA: Los canales de inteligencia están caídos.")

# --- 5. LANZAMIENTO ---
def main():
    if not TELEGRAM_TOKEN:
        return

    threading.Thread(target=run_flask, daemon=True).start()

    while True:
        try:
            application = Application.builder().token(TELEGRAM_TOKEN).build()
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje))
            print("Oficial S-2 Triple-Core + Enciclopedia en línea. ¡RELOAD!")
            application.run_polling(drop_pending_updates=True)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    main()
