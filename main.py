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
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# --- 1. CONFIGURACIÓN FIREBASE (ENCICLOPEDIA S-2) ---
firebase_creds_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')

if firebase_creds_json:
    try:
        creds_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(creds_dict)
        
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

try:
    with open("SYSTEM_S2_PROTOCOLS.txt", "r", encoding="utf-8") as f:
        instrucciones_base = f.read()
except FileNotFoundError:
    instrucciones_base = "Eres el Oficial S-2 de GUN4FUN. Analista técnico directo. PRECISIÓN ABSOLUTA."

# --- 4. SISTEMA TÁCTICO DE PROCESAMIENTO E INGESTA MULTIMEDIA ---
def extraer_contenido_url(texto: str) -> str:
    """Raspa el HTML de la web extrayendo todo el contenido de texto, imágenes y vídeos reales."""
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
            
            # 1. Extracción y normalización de imágenes reales antes de limpiar
            imagenes_encontradas = []
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and not src.startswith('data:'):
                    # Convertir rutas relativas en URLs absolutas completas
                    url_completa = urljoin(url_objetivo, src)
                    if url_completa not in imagenes_encontradas:
                        imagenes_encontradas.append(url_completa)
            
            # 2. Extracción de vídeos (YouTube o similares)
            videos_encontrados = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'youtube.com' in href or 'youtu.be' in href:
                    url_video = urljoin(url_objetivo, href)
                    if url_video not in videos_encontrados:
                        videos_encontrados.append(url_video)

            # Limpieza de elementos de interfaz irrelevantes
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()
                
            texto_limpio = soup.get_text(separator=' ', strip=True)
            
            # Empaquetado de telemetría multimedia para la IA
            reporte_web = (
                f"\n[CONTENIDO EXTRAÍDO DE LA URL: {url_objetivo}]\n"
                f"TEXTO BASE DE LA WEB:\n{texto_limpio}\n\n"
                f"LISTA DE IMÁGENES REALES DETECTADAS:\n{json.dumps(imagenes_encontradas)}\n\n"
                f"LISTA DE VÍDEOS REALES DETECTADAS:\n{json.dumps(videos_encontrados)}\n"
            )
            return reporte_web
    except Exception as e:
        return f"\n[ERROR TÉCNICO AL ACCEDER A LA URL {url_objetivo}: {str(e)}]"

def ejecutar_ia_con_cascada(prompt_sistema: str, prompt_usuario: str):
    """Ejecuta una solicitud de IA en cascada para el módulo de inyección."""
    # Intentar Plan A: Groq
    try:
        completion = client_groq.chat.completions.create(
            model=MODELO_GROQ,
            messages=[{"role": "system", "content": prompt_sistema}, {"role": "user", "content": prompt_usuario}],
            temperature=0.0
        )
        return completion.choices[0].message.content, "Canal Alpha - Groq"
    except Exception as e:
        print(f"⚠️ Ingesta Plan A fallida: {e}")

    # Intentar Plan B: Mistral
    if MISTRAL_API_KEY:
        try:
            completion = client_mistral.chat.complete(
                model="mistral-small-latest",
                messages=[{"role": "system", "content": prompt_sistema}, {"role": "user", "content": prompt_usuario}],
                temperature=0.0
            )
            return completion.choices[0].message.content, "Canal Bravo - Mistral"
        except Exception as e2:
            print(f"⚠️ Ingesta Plan B fallida: {e2}")

    # Intentar Plan C: DeepSeek
    if DEEPSEEK_API_KEY:
        try:
            completion = client_deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": prompt_sistema}, {"role": "user", "content": prompt_usuario}],
                temperature=0.0
            )
            return completion.choices[0].message.content, "Canal Charlie - DeepSeek"
        except Exception as e3:
            print(f"⚠️ Ingesta Plan C fallida: {e3}")

    raise Exception("Todos los canales de procesamiento de IA se encuentran fuera de servicio.")

def ejecutar_ingesta_base_datos(username: str, comando_texto: str) -> str:
    """Analiza y vuelca el contenido web estructurándolo dinámicamente sin límites de campos."""
    autorizados = ["@carlosfservan", "@gargarensis76", "@gwyllion16"]
    if username.lower() not in autorizados:
        return f"Recluta, transmision denegada. No posees autorización de escritura en los Archivos de Inteligencia S-2."

    contenido_web = extraer_contenido_url(comando_texto)
    datos_completos_para_ia = f"Orden del operador:\n{comando_texto}\n{contenido_web}"

    prompt_parseo = (
        "Actúa como el submódulo de indexación dinámica del Oficial S-2. Tu objetivo es procesar la información técnica "
        "y los arrays de multimedia real proporcionados, estructurándolos en un formato JSON completo, extenso y ordenado.\n\n"
        "REGLAS OBLIGATORIAS DE ESTRUCTURACIÓN:\n"
        "1. Identifica la 'rama' (una de estas: 1_Manuales_tecnicos, 2_Ecosistema_software, 3_Archivo_historico, 4_Protocolos_unidad).\n"
        "2. Identifica el 'subnodo' (sistema o emulador en minúsculas y sin espacios, ej: batocera).\n"
        "3. Dentro del objeto 'datos', NO te limites a un solo campo de texto. Crea claves dinámicas según la información disponible "
        "para segmentar todo sin resumir (ej: 'Descripcion', 'Calibracion_Hardware', 'Emuladores_Soportados', 'FAQ', 'Solucion_Problemas').\n"
        "4. En los campos 'imagenes_esquema' y 'videos_tutorial', utiliza EXCLUSIVAMENTE los enlaces reales provistos en los listados del usuario. "
        "Si un enlace está incompleto o no hay, deja el array vacío. Está prohibido inventar URLs.\n\n"
        "Responde EXCLUSIVAMENTE con el objeto JSON puro con esta forma jerárquica:\n"
        "{\n"
        "  \"rama\": \"Nombre_de_la_rama\",\n"
        "  \"subnodo\": \"Nombre_del_subnodo\",\n"
        "  \"datos\": {\n"
        "    \"Seccion_1\": \"Contenido masivo y detallado sin omitir nada...\",\n"
        "    \"Seccion_2\": \"Contenido masivo...\",\n"
        "    \"imagenes_esquema\": [\"URLs reales extraídas\"],\n"
        "    \"videos_tutorial\": [\"URLs reales extraídas\"]\n"
        "  }\n"
        "}\n"
        "No incluyas introducciones ni bloques de código markdown."
    )

    try:
        resultado_raw, canal_usado = ejecutar_ia_con_cascada(prompt_parseo, datos_completos_para_ia)
        
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

        # Inyección directa
        ref = db.reference(f'Enciclopedia_S2/{rama}/{subnodo}')
        ref.update(payload)
        
        prefijo_rango = "Comandante" if username.lower() == "@carlosfservan" else "Sargento"
        return f"[{canal_usado}]\n\n{prefijo_rango}, toda la información técnica fue clasificada e inyectada dinámicamente con éxito en 'Enciclopedia_S2/{rama}/{subnodo}'."
        
    except Exception as err:
        return f"Error en el sistema de ingesta táctica en cascada: {str(err)}. Transmisión abortada."

# --- 5. LÓGICA DE RESPUESTA EN CASCADA CON CONTEXTO REAL ---
async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.message.from_user
    username = f"@{user.username}" if user.username else user.first_name
    mensaje_usuario = update.message.text

    # INTERCEPTOR DE COMANDO /GUARDAR
    if mensaje_usuario.strip().startswith("/guardar"):
        resultado_guardado = ejecutar_ingesta_base_datos(username, mensaje_usuario)
        await update.message.reply_text(f"{resultado_guardado}\n\nCambio y corto. ¡RELOAD!")
        return

    # COMANDO O PREGUNTA DE ESTADO SISTEMA
    if mensaje_usuario.strip().lower() in ["/estado", "estado", "¿con qué ia estás trabajando?", "con que ia estas trabajando"]:
        reporte_estado = (
            "📊 **INFORME DE ESTADO OPERATIVO - OFICIAL S-2**\n"
            f"• Canal Alpha (Groq - {MODELO_GROQ}): {'🟢 ONLINE' if GROQ_API_KEY else '🔴 OFFLINE'}\n"
            f"• Canal Bravo (Mistral - Small): {'🟢 ONLINE' if MISTRAL_API_KEY else '🔴 OFFLINE'}\n"
            f"• Canal Charlie (DeepSeek - Chat): {'🟢 ONLINE' if DEEPSEEK_API_KEY else '🔴 OFFLINE'}\n\n"
            "**Prioridad de Enrutamiento:** Cascada Táctica (Alpha ➡️ Bravo ➡️ Charlie).\n"
            "El sistema responderá utilizando el canal prioritario disponible."
        )
        await update.message.reply_text(reporte_estado, parse_mode="Markdown")
        return

    contexto_situacional = (
        f"\n--- METADATOS DE LA TRANSMISIÓN ---\n"
        f"FECHA Y HORA ACTUAL: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"IDENTIDAD DEL REMITENTE: {username}\n"
        f"------------------------------------\n"
    )

    contexto_real = obtener_datos_enciclopedia()
    instrucciones_completas = f"{instrucciones_base}\n{contexto_situacional}\n{contexto_real}"

    # --- PLAN A: GROQ ---
    try:
        chat_completion = client_groq.chat.completions.create(
            model=MODELO_GROQ,
            messages=[{"role": "system", "content": instrucciones_completas}, {"role": "user", "content": mensaje_usuario}],
            temperature=0.0,
            max_tokens=2048
        )
        respuesta = chat_completion.choices[0].message.content
        if respuesta:
            await update.message.reply_text(f"[Canal Alpha - Groq]\n\n{respuesta}")
            return
    except Exception as e:
        print(f"⚠️ PLAN A FALLIDO: {e}")

    # --- PLAN B: MISTRAL ---
    if MISTRAL_API_KEY:
        try:
            res_mistral = client_mistral.chat.complete(
                model="mistral-small-latest",
                messages=[{"role": "system", "content": instrucciones_completas}, {"role": "user", "content": mensaje_usuario}],
                temperature=0.0
            )
            await update.message.reply_text(f"[Canal Bravo - Mistral]\n\n{res_mistral.choices[0].message.content}")
            return
        except Exception as e2:
            print(f"⚠️ PLAN B FALLIDO: {e2}")

    # --- PLAN C: DEEPSEEK ---
    if DEEPSEEK_API_KEY:
        try:
            res_ds = client_deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": instrucciones_completas}, {"role": "user", "content": mensaje_usuario}],
                temperature=0.0
            )
            await update.message.reply_text(f"[Canal Charlie - DeepSeek]\n\n{res_ds.choices[0].message.content}")
            return
        except Exception as e3:
            print(f"⚠️ PLAN C FALLIDO: {e3}")

    await update.message.reply_text("❌ INTERFERENCIA: Todos los canales de inteligencia están caídos.")

# --- 6. LANZAMIENTO ---
def main():
    if not TELEGRAM_TOKEN:
        print("Falta TELEGRAM_TOKEN. Abortando.")
        return

    threading.Thread(target=run_flask, daemon=True).start()

    while True:
        try:
            application = Application.builder().token(TELEGRAM_TOKEN).build()
            application.add_handler(MessageHandler(filters.TEXT, procesar_mensaje))
            print("Oficial S-2 (Analista Técnico e Ingesta Activa) en línea. ¡RELOAD!")
            application.run_polling(drop_pending_updates=True)
        except Exception as e:
            print(f"Error en polling: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
