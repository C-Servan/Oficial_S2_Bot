import os
import threading
import time
import json
import re
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask
from groq import Groq
from mistralai import Mistral
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Librerías nativas para extracción web segura y raspado de datos
import urllib.request
from bs4 import BeautifulSoup

# --- 1. CONFIGURACIÓN FIREBASE (ENCICLOPEDIA S-2) ---
firebase_creds_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')

if firebase_creds_json:
    try:
        creds_dict = json.loads(firebase_creds_json)
        # Forzar explícitamente los Scopes de almacenamiento y base de datos para evitar el "Unauthorized request"
        cred = credentials.Certificate(creds_dict)
        
        # Evitar inicializaciones duplicadas si el proceso se reinicia en Render
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://enciclopedia-oficial-s-2-default-rtdb.europe-west1.firebasedatabase.app/'
            })
        print("✅ Conexión blindada a la Enciclopedia S-2 establecida.")
    except Exception as e:
        print(f"❌ Error crítico al inicializar Firebase: {e}")

def obtener_datos_enciclopedia():
    """Recupera toda la sabiduría almacenada para dar contexto a la IA"""
    try:
        ref = db.reference('Enciclopedia_S2')
        datos = ref.get()
        if not datos:
            return "No hay datos registrados en la enciclopedia aún."
        
        contexto = "\n--- DATOS REALES RECUPERADOS DE FIREBASE (ENCICLOPEDIA S-2) ---\n"
        contexto += json.dumps(datos, indent=2, ensure_ascii=False)
        contexto += "\n--- FIN DE LOS DATOS REALES ---\n"
        return contexto
    except Exception as e:
        print(f"Error leyendo base de datos: {e}")
        return ""

# --- 2. CONFIGURACIÓN DEL SERVIDOR WEB ---
app = Flask(__name__)
@app.route('/')
def health_check():
    return "Oficial S-2 Operativo (Protocolos System S2 Activos)", 200

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

# CARGA DEL ARCHIVO DE PROTOCOLO (Aquí reside el comportamiento de analista técnico)
try:
    with open("SYSTEM_S2_PROTOCOLS.txt", "r", encoding="utf-8") as f:
        instrucciones_base = f.read()
except FileNotFoundError:
    instrucciones_base = "Eres el Oficial S-2 de GUN4FUN. Analista técnico directo. PRECISIÓN ABSOLUTA."

# --- 4. SISTEMA TÁCTICO DE PROCESAMIENTO E INGESTA MULTIMEDIA ---
def extraer_contenido_url(texto: str) -> str:
    """Detecta si hay un enlace en el comando, raspa el HTML de la web y extrae el texto limpio."""
    urls = re.findall(r'(https?://[^\s|]+)', texto)
    if not urls:
        return ""
    
    url_objetivo = urls[0]
    try:
        req = urllib.request.Request(
            url_objetivo, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Limpieza de elementos irrelevantes de la interfaz web
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()
                
            return f"\n[CONTENIDO EXTRAÍDO EN TIEMPO REAL DESDE LA URL: {url_objetivo}]\n{soup.get_text(separator=' ', strip=True)}"
    except Exception as e:
        return f"\n[ERROR TÉCNICO AL ACCEDER A LA URL {url_objetivo}: {str(e)}]"

def ejecutar_ingesta_base_datos(username: str, comando_texto: str) -> str:
    """
    Intercepta y procesa la orden de guardado. Utiliza la potencia de procesamiento de la IA 
    para parsear el texto o enlace del Comandante/Sargento en un objeto JSON multimedia limpio.
    """
    # Verificación de Rangos Autorizados (Evitamos conflictos convirtiendo temporalmente a minúsculas)
    autorizados = ["@carlosfservan", "@gargarensis76", "@gwyllion16"]
    if username.lower() not in autorizados:
        return f"Recluta, transmision denegada. No posees autorización de escritura en los Archivos de Inteligencia S-2."

    # Si hay un enlace, el bot extrae la información técnica de la página web directamente
    contenido_web = extraer_contenido_url(comando_texto)
    datos_completos_para_ia = f"Orden original del usuario:\n{comando_texto}\n{contenido_web}"

    # Prompt maestro de inyección estructural
    prompt_parseo = (
        "Actúa como el submódulo de indexación del Oficial S-2. Tu único objetivo es recibir una orden técnica "
        "junto con el contenido extraído de un enlace web suministrado por el Comandante o un Sargento, y estructurarlo en un formato JSON estricto.\n"
        "Debes analizar minuciosamente el texto e identificar: todas las configuraciones, parámetros del sistema, pasos detallados, e indexar todas las URLs de imágenes, esquemas "
        "o vídeos de YouTube que se encuentren explícitos en el texto.\n\n"
        "Debes responder EXCLUSIVAMENTE con un objeto JSON válido que contenga la siguiente estructura:\n"
        "{\n"
        "  \"rama\": \"Indica una de estas cuatro opciones exactas: 1_Manuales_tecnicos, 2_Ecosistema_software, 3_Archivo_historico, 4_Protocolos_unidad\",\n"
        "  \"subnodo\": \"Nombre del sistema, emulador o tema en minúsculas y sin espacios (ej: batocera, openfire, mame)\",\n"
        "  \"datos\": {\n"
        "    \"texto_guia\": \"Pasos detallados de configuración, parámetros explicados de archivos .conf, mapeos y calibración sin omitir nada.\",\n"
        "    \"imagenes_esquema\": [\"Lista de URLs completas de diagramas o capturas encontradas en el texto, o un array vacío si no hay\"],\n"
        "    \"videos_tutorial\": [\"Lista de URLs completas de vídeos de YouTube o referencias multimedia encontradas, o un array vacío si no hay\"]\n"
        "  }\n"
        "}\n"
        "No agregues introducciones, no saludes, no agregues markdown extra de código. Solo el JSON puro."
    )

    try:
        # Usamos Groq para procesar y estructurar el texto/enlace a guardar
        parse_completion = client_groq.chat.completions.create(
            model=MODELO_GROQ,
            messages=[
                {"role": "system", "content": prompt_parseo},
                {"role": "user", "content": datos_completos_para_ia}
            ],
            temperature=0.0
        )
        
        resultado_raw = parse_completion.choices[0].message.content.strip()
        
        # Limpieza de posibles bloques de código agregados por el modelo
        if resultado_raw.startswith("```json"):
            resultado_raw = resultado_raw[7:]
        if resultado_raw.endswith("```"):
            resultado_raw = resultado_raw[:-3]
        
        objeto_datos = json.loads(resultado_raw.strip())
        
        rama = objeto_datos.get("rama")
        subnodo = objeto_datos.get("subnodo")
        payload = objeto_datos.get("datos")
        payload["ultima_modificacion"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        payload["modificado_por"] = username

        # Inyección directa en la Realtime Database de Firebase
        ref = db.reference(f'Enciclopedia_S2/{rama}/{subnodo}')
        ref.update(payload)
        
        # Confirmación adaptada al rango del operador usando lower() para evitar fallos de strings
        prefijo_rango = "Comandante" if username.lower() == "@carlosfservan" else "Sargento"
        return f"{prefijo_rango}, datos técnicos procesados, extraídos de la URL y guardados con éxito en 'Enciclopedia_S2/{rama}/{subnodo}'."
        
    except Exception as err:
        return f"Error en el sistema de ingesta táctica: {str(err)}. Transmisión abortada."

# --- 5. LÓGICA DE RESPUESTA EN CASCADA CON CONTEXTO REAL ---
async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    # EXTRACCIÓN DE METADATOS (USUARIO Y TIEMPO)
    user = update.message.from_user
    username = f"@{user.username}" if user.username else user.first_name
    ahora = datetime.now()
    fecha_hora = ahora.strftime("%d/%m/%Y %H:%M:%S")
    
    mensaje_usuario = update.message.text

    # INTERCEPTOR DE COMANDO /GUARDAR
    if mensaje_usuario.strip().startswith("/guardar"):
        resultado_guardado = ejecutar_ingesta_base_datos(username, mensaje_usuario)
        await update.message.reply_text(f"{resultado_guardado}\n\nCambio y corto. ¡RELOAD!")
        return

    contexto_situacional = (
        f"\n--- METADATOS DE LA TRANSMISIÓN ---\n"
        f"FECHA Y HORA ACTUAL: {fecha_hora}\n"
        f"IDENTIDAD DEL REMITENTE: {username}\n"
        f"------------------------------------\n"
    )

    contexto_real = obtener_datos_enciclopedia()
    instrucciones_completas = f"{instrucciones_base}\n{contexto_situacional}\n{contexto_real}"

    # --- PLAN A: GROQ ---
    try:
        chat_completion = client_groq.chat.completions.create(
            model=MODELO_GROQ,
            messages=[
                {"role": "system", "content": instrucciones_completas},
                {"role": "user", "content": mensaje_usuario}
            ],
            temperature=0.0,
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
                    {"role": "system", "content": instrucciones_completas},
                    {"role": "user", "content": mensaje_usuario}
                ],
                temperature=0.0
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
                    {"role": "system", "content": instrucciones_completas},
                    {"role": "user", "content": mensaje_usuario}
                ],
                temperature=0.0
            )
            await update.message.reply_text(res_ds.choices[0].message.content)
            return
        except Exception as e3:
            print(f"⚠️ PLAN C FALLIDO: {e3}")

    await update.message.reply_text("❌ INTERFERENCIA: Los canales de intelligence están caídos.")

# --- 6. LANZAMIENTO ---
def main():
    if not TELEGRAM_TOKEN:
        print("Falta TELEGRAM_TOKEN. Abortando.")
        return

    threading.Thread(target=run_flask, daemon=True).start()

    while True:
        try:
            application = Application.builder().token(TELEGRAM_TOKEN).build()
            
            # CORRECCIÓN DE FILTRO: Procesamiento de '/guardar' como texto plano activo.
            application.add_handler(MessageHandler(filters.TEXT, procesar_mensaje))
            
            print("Oficial S-2 (Analista Técnico e Ingesta Activa) en línea. ¡RELOAD!")
            application.run_polling(drop_pending_updates=True)
        except Exception as e:
            print(f"Error en polling: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
