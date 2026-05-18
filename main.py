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

def obtener_contexto_inteligente(mensaje_usuario: str) -> str:
    """Busca en Firebase de forma selectiva para evitar la saturación de tokens por volumen masivo."""
    try:
        ref_raiz = db.reference('Enciclopedia_S2')
        estructura_completa = ref_raiz.get()
        
        if not estructura_completa:
            return "No hay datos registrados en la enciclopedia aún."
        
        mensaje_min = mensaje_usuario.lower()
        subnodos_encontrados = {}
        
        # Escaneo táctico de ramas y subnodos buscando coincidencias de palabras clave
        for rama, subnodos in estructura_completa.items():
            if isinstance(subnodos, dict):
                for subnodo, contenido in subnodos.items():
                    # Si el usuario menciona el nombre del subnodo (ej: 'batocera', 'wikipedia_lightgun')
                    if subnodo.lower() in mensaje_min or subnodo.replace("_", "") in mensaje_min:
                        if rama not in subnodos_encontrados:
                            subnodos_encontrados[rama] = {}
                        subnodos_encontrados[rama][subnodo] = contenido

        if subnodos_encontrados:
            contexto = "\n--- DATOS ESPECÍFICOS RECUPERADOS (COINCIDENCIA DETECTADA) ---\n"
            contexto += json.dumps(subnodos_encontrados, indent=2, ensure_ascii=False)
            contexto += "\n--- FIN DE LOS DATOS RELEVANTES ---\n"
            return contexto
            
        # Si no hay coincidencia, solo enviamos el mapa taxonómico (el índice de lo que sabemos)
        mapa_conocimiento = {}
        for rama, subnodos in estructura_completa.items():
            if isinstance(subnodos, dict):
                mapa_conocimiento[rama] = list(subnodos.keys())
            else:
                mapa_conocimiento[rama] = "Nodo vacío"
                
        contexto_ligero = "\n--- ÍNDICE DE CONTENIDOS DISPONIBLES EN S-2 ---\n"
        contexto_ligero += f"Actualmente posees información guardada sobre estos sistemas: {json.dumps(mapa_conocimiento, ensure_ascii=False)}\n"
        contexto_ligero += "Si el usuario pregunta por algo que NO está en esta lista, infórmale con disciplina de que el archivo no está indexado y que requiere el comando /guardar.\n"
        contexto_ligero += "----------------------------------------------\n"
        return contexto_ligero

    except Exception as e:
        print(f"Error en filtro analítico de contexto: {e}")
        return "Error limitador al recuperar contexto real."

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
            
            # 1. Extracción y normalización de imágenes reales
            imagenes_encontradas = []
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and not src.startswith('data:'):
                    url_completa = urljoin(url_objetivo, src)
                    if url_completa not in imagenes_encontradas:
                        imagenes_encontradas.append(url_completa)
            
            # 2. Extracción de vídeos (YouTube)
            videos_encontrados = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'youtube.com' in href or 'youtu.be' in href:
                    url_video = urljoin(url_objetivo, href)
                    if url_video not in videos_encontrados:
                        videos_encontrados.append(url_video)

            # Limpieza de elementos de interfaz de la web
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()
                
            texto_limpio = soup.get_text(separator=' ', strip=True)
            
            reporte_web = (
                f"\n[CONTENIDO EXTRAÍDO DE LA URL: {url_objetivo}]\n"
                f"TEXTO BASE DE LA WEB:\n{texto_limpio}\n\n"
                f"LISTA DE IMÁGENES REALES DETECTADAS:\n{json.dumps(imagenes_encontradas)}\n\n"
                f"LISTA DE VÍDEOS REALES DETECTADOS:\n{json.dumps(videos_encontrados)}\n"
            )
            return reporte_web
    except Exception as e:
        return f"\n[ERROR TÉCNICO AL ACCEDER A LA URL {url_objetivo}: {str(e)}]"

def ejecutar_ia_con_cascada(prompt_sistema: str, prompt_usuario: str):
    """Ejecuta una solicitud de IA en cascada blindada con límites de salida ampliados."""
    # Intentar Plan A: Groq
    try:
        completion = client_groq.chat.completions.create(
            model=MODELO_GROQ,
            messages=[{"role": "system", "content": prompt_sistema}, {"role": "user", "content": prompt_usuario}],
            temperature=0.0,
            max_tokens=4096
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
                temperature=0.0,
                max_tokens=4096
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
                temperature=0.0,
                max_tokens=4096
            )
            return completion.choices[0].message.content, "Canal Charlie - DeepSeek"
        except Exception as e3:
            print(f"⚠️ Ingesta Plan C fallida: {e3}")

    raise Exception("Todos los canales de procesamiento de IA se encuentran fuera de servicio debido a saturación de tokens.")

def ejecutar_ingesta_base_datos(username: str, comando_texto: str) -> str:
    """Descarga la información existente, genera un índice dinámico y procesa la web por secciones secuenciales."""
    autorizados = ["@carlosfservan", "@gargarensis76", "@gwyllion16"]
    if username.lower() not in autorizados:
        return f"Recluta, transmision denegada. No posees autorización de escritura en los Archivos de Inteligencia S-2."

    # Pre-análisis táctico de la ruta de destino antes de la ejecución de IA
    partes = comando_texto.replace("/guardar", "").split("|")
    rama_detectada = "1_Manuales_tecnicos"
    subnodo_detectado = "desconocido"
    
    if len(partes) >= 2:
        rama_detectada = partes[0].strip()
        subnodo_detectado = partes[1].strip().lower().replace(" ", "")

    # Descarga analítica del estado actual del subnodo en Firebase
    datos_existentes = {}
    try:
        ref_existente = db.reference(f'Enciclopedia_S2/{rama_detectada}/{subnodo_detectado}')
        nodo_actual = ref_existente.get()
        if nodo_actual:
            datos_existentes = nodo_actual
    except Exception as e:
        print(f"Aviso: No se pudo leer el histórico (procesando como nodo nuevo): {e}")

    contenido_web = extraer_contenido_url(comando_texto)
    if not contenido_web or "[ERROR TÉCNICO" in contenido_web:
        return f"Error en la extracción de la URL. Abortando misión: {contenido_web}"

    # ==========================================
    # PASO 1: PASADA DE RECONOCIMIENTO (MAPEO DEL ÍNDICE)
    # ==========================================
    prompt_indexador = (
        "Actúas como el Ingeniero de Reconocimiento del Oficial S-2. Tu único objetivo es analizar la información textual extraída de una web "
        "y estructurar un ÍNDICE DINÁMICO de categorías estandarizadas basadas estrictamente en la materia tratada en el documento.\n\n"
        "REGLAS OBLIGATORIAS:\n"
        "1. Identifica entre 3 y 7 categorías lógicas que agrupen perfectamente todo el contenido expuesto en la web (ejemplos válidos: Manual_Instalacion, Calibracion_Hardware, FAQ, Resolucion_Problemas, Requisitos_Sistema, Comandos_Consola, etc).\n"
        "2. Formatea las categorías usando CamelCase o guiones bajos sin espacios.\n"
        "3. Responde ÚNICAMENTE con la lista de categorías separadas por comas, sin introducciones, saludos, ni bloques de código Markdown.\n\n"
        "Ejemplo de respuesta esperada:\n"
        "Manual_Instalacion, Calibracion_Hardware, FAQ, Resolucion_Problemas"
    )

    try:
        indice_raw, canal_indexador = ejecutar_ia_con_cascada(prompt_indexador, contenido_web)
        indice_raw = re.sub(r'[`\s\n]', '', indice_raw)
        categorias = [cat.strip() for cat in indice_raw.split(",") if cat.strip()]
        if not categorias:
            categorias = ["Manual_Instalacion", "Calibracion_Hardware", "FAQ", "Resolucion_Problemas"]
    except Exception as err_idx:
        print(f"Fallo en indexador dinámico, aplicando categorías base: {err_idx}")
        categorias = ["Manual_Instalacion", "Calibracion_Hardware", "FAQ", "Resolucion_Problemas"]

    # ==========================================
    # PASO 2: FUSIÓN Y ASIMILACIÓN POR OLEADAS SECUENCIALES
    # ==========================================
    payload_acumulado = {}
    canales_utilizados = []
    
    urls_en_texto = re.findall(r'\"(https?://[^\s"]+)\"', contenido_web)
    nuevas_img = [u for u in urls_en_texto if any(ext in u.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])]
    nuevos_vid = [u for u in urls_en_texto if 'youtube.com' in u.lower() or 'youtu.be' in u.lower()]

    for categoria in categorias:
        texto_historico_categoria = datos_existentes.get(categoria, "No hay registros preexistentes de esta categoría.")
        
        datos_oleada_ia = (
            f"=== CATEGORÍA A PROCESAR EN ESTA OLEADA ===\n{categoria}\n\n"
            f"=== HISTÓRICO ALMACENADO EN FIREBASE PARA ESTA CATEGORÍA ===\n{texto_historico_categoria}\n\n"
            f"=== CONTENIDO COMPLETO DE LA NUEVA WEB ===\n{contenido_web}"
        )

        prompt_oleada = (
            f"Actúas como el Especialista de Ingesta Táctica S-2 para la sección '{categoria}'. Tu misión es extraer de manera quirúrgica "
            f"toda la información de la nueva web que corresponda EXCLUSIVAMENTE a la temática de la categoría '{categoria}' y fusionarla con el histórico.\n\n"
            f"INSTRUCCIONES DE ACCIÓN:\n"
            f"1. Haz un 'merge' inteligente: Redacta un manual unificado, extenso, técnico, jerarquizado y más detallado combinando el conocimiento histórico con los nuevos datos entrantes.\n"
            f"2. Si la web entrante no aporta nada nuevo o útil para la sección '{categoria}', mantén íntegro e intacto el texto histórico que se te ha provisto.\n"
            f"3. No inventes configuraciones, mantén la precisión analítica absoluta.\n"
            f"4. Responde ÚNICAMENTE con el desarrollo de texto de la sección unificada, sin etiquetas del formato anterior, sin bloques de código ```json o ```markdown, and sin comentarios editoriales externos."
        )

        try:
            texto_fusionado, canal_oleada = ejecutar_ia_con_cascada(prompt_oleada, datos_oleada_ia)
            payload_acumulado[categoria] = texto_fusionado.strip()
            if canal_oleada not in canales_utilizados:
                canales_utilizados.append(canal_oleada)
            time.sleep(0.5)
        except Exception as err_oleada:
            print(f"Error procesando la oleada {categoria}: {err_oleada}")
            payload_acumulado[categoria] = texto_historico_categoria

    img_historicas = datos_existentes.get("imagenes_esquema", [])
    vid_historicos = datos_existentes.get("videos_tutorial", [])
    img_finales = list(dict.fromkeys(img_historicas + nuevas_img))
    vid_finales = list(dict.fromkeys(vid_historicos + nuevos_vid))

    payload_final = {**payload_acumulado}
    payload_final["imagenes_esquema"] = img_finales
    payload_final["videos_tutorial"] = vid_finales
    payload_final["ultima_modificacion"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    payload_final["modificado_por"] = username

    try:
        ref = db.reference(f'Enciclopedia_S2/{rama_detectada}/{subnodo_detectado}')
        ref.update(payload_final)
        
        prefijo_rango = "Comandante" if username.lower() == "@carlosfservan" else "Sargento"
        canales_str = ", ".join(canales_utilizados)
        return (
            f"[{canales_str}]\n\n"
            f"¡Fase 2 Completada con éxito, {prefijo_rango}! El sistema ha mapeado dinámicamente un índice de {len(categorias)} categorías "
            f"({', '.join(categorias)}). La información ha sido procesada por oleadas y fusionada de manera incremental en "
            f"'{rama_detectada}/{subnodo_detectado}' sin pérdidas sintácticas ni saturación de memoria."
        )
    except Exception as err:
        return f"Error crítico al inyectar el payload consolidado en Firebase: {str(err)}. Transmisión abortada."

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

    # Llamada al nuevo extractor selectivo inteligente para mitigar desbordamientos
    contexto_real = obtener_contexto_inteligente(mensaje_usuario)
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
        print(f"⚠️ PLAN A FALLIDO (Consulta): {e}")

    # --- PLAN B: MISTRAL ---
    if MISTRAL_API_KEY:
        try:
            res_mistral = client_mistral.chat.complete(
                model="mistral-small-latest",
                messages=[{"role": "system", "content": instrucciones_completas}, {"role": "user", "content": mensaje_usuario}],
                temperature=0.0,
                max_tokens=2048
            )
            await update.message.reply_text(f"[Canal Bravo - Mistral]\n\n{res_mistral.choices[0].message.content}")
            return
        except Exception as e2:
            print(f"⚠️ PLAN B FALLIDO (Consulta): {e2}")

    # --- PLAN C: DEEPSEEK ---
    if DEEPSEEK_API_KEY:
        try:
            res_ds = client_deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": instrucciones_completas}, {"role": "user", "content": mensaje_usuario}],
                temperature=0.0,
                max_tokens=2048
            )
            await update.message.reply_text(f"[Canal Charlie - DeepSeek]\n\n{res_ds.choices[0].message.content}")
            return
        except Exception as e3:
            print(f"⚠️ PLAN C FALLIDO (Consulta): {e3}")

    await update.message.reply_text("❌ INTERFERENCIA: Todos los canales de inteligencia están caídos debido a desbordamiento.")

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
