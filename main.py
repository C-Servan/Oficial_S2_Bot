import os
import io
import json
import time
import telebot
import requests
import scraper
import database
import threading
from flask import Flask

# ==========================================
# 🛰️ CONFIGURACIÓN DE RESTRICCIONES Y LLAVES
# ==========================================
# Se añade 'DUMMY' por defecto para evitar que Render aborte el despliegue
# si comprueba el código antes de inyectar las variables de entorno reales.
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'DUMMY')
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID')

GEMINI_KEY = os.environ.get('GEMINI_API_KEY')
GROQ_KEY = os.environ.get('GROQ_API_KEY')
DEEPSEEK_KEY = os.environ.get('DEEPSEEK_API_KEY')

bot = telebot.TeleBot(TOKEN)

# ==========================================
# 🌍 CONFIGURACIÓN FLASK + MONITOR ANTI-DORMIR
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    """Endpoint limpio para el monitor Uptime. Evita la hibernación en Render."""
    return "⚡ Sistema central V2 operativo. Monitor activo y en línea.", 200

# ==========================================
# 🧽 SANITIZADOR INMUNE PARA RESPUESTAS JSON
# ==========================================
def limpiar_y_cargar_json(texto_crudo):
    """Limpia de forma agresiva cualquier bloque de código markdown generado por las IAs."""
    texto_crudo = texto_crudo.strip()
    if texto_crudo.startswith("```"):
        lineas = texto_crudo.splitlines()
        if lineas[0].startswith("```"):
            lineas = lineas[1:]
        if lineas[-1].startswith("```"):
            lineas = lineas[:-1]
        texto_crudo = "\n".join(lineas).strip()
    return json.loads(texto_crudo)

# ==========================================
# ⚡ MOTOR DE CASCADA COGNITIVA (AI FALLBACK)
# ==========================================
def analizar_con_cascada_ia(texto_art):
    prompt_maestro = (
        "Analiza el siguiente texto técnico de emulación/sistemas.\n"
        "1. Clasifícalo decidiendo la subcarpeta ideal dentro de la jerarquía 'Sistemas/' "
        "(ejemplo: 'Sistemas/Batocera/Configuracion', 'Sistemas/RetroBat/FAQ', etc.).\n"
        "2. Asígnale un título descriptivo corto en minúsculas, usando guiones bajos en vez de espacios.\n"
        "3. Genera un manual técnico resumido, limpio, estructurado y libre de paja.\n\n"
        "Devuelve ÚNICAMENTE un objeto JSON con este formato exacto, sin bloques de código ni texto adicional:\n"
        '{"ruta": "Sistemas/NombreSistema/Subcarpeta", "titulo": "nombre_del_manual", "resumen": "contenido del manual..."}\n\n'
        f"Texto a analizar:\n{texto_art}"
    )

    # --- 🔴 CANAL ALPHA: Gemini ---
    if GEMINI_KEY:
        print("🔴 [CASCADA] Activando Canal Alpha: Gemini...", flush=True)
        try:
            url_gemini = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=){GEMINI_KEY}"
            payload = {"contents": [{"parts": [{"text": prompt_maestro}]}]}
            res = requests.post(url_gemini, json=payload, timeout=15)
            if res.status_code == 200:
                raw_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                return limpiar_y_cargar_json(raw_text), "🔴 [Canal Alpha - Gemini]"
        except Exception as e:
            print(f"⚠️ [CASCADA] Falló Canal Alpha: {e}. Derivando al frente de reserva...", flush=True)

    # --- 🔵 CANAL BRAVO: Groq ---
    if GROQ_KEY:
        print("🔵 [CASCADA] Activando Canal Bravo: Groq...", flush=True)
        try:
            url_groq = "[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)"
            headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": prompt_maestro}],
                "temperature": 0.2
            }
            res = requests.post(url_groq, json=payload, timeout=15)
            if res.status_code == 200:
                raw_text = res.json()['choices'][0]['message']['content']
                return limpiar_y_cargar_json(raw_text), "🔵 [Canal Bravo - Groq]"
        except Exception as e:
            print(f"⚠️ [CASCADA] Falló Canal Bravo: {e}. Activando última línea de defensa...", flush=True)

    # --- 🟢 CANAL CHARLIE: DeepSeek ---
    if DEEPSEEK_KEY:
        print("🟢 [CASCADA] Activando Canal Charlie: DeepSeek...", flush=True)
        try:
            url_deepseek = "[https://api.deepseek.com/v1/chat/completions](https://api.deepseek.com/v1/chat/completions)"
            headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt_maestro}],
                "temperature": 0.2
            }
            res = requests.post(url_deepseek, json=payload, timeout=15)
            if res.status_code == 200:
                raw_text = res.json()['choices'][0]['message']['content']
                return limpiar_y_cargar_json(raw_text), "🟢 [Canal Charlie - DeepSeek]"
        except Exception as e:
            print(f"🚨 [CASCADA] Línea de defensa rota. Fallaron todos los canales: {e}", flush=True)

    return None, None

# ==========================================
# 🛰️ COMANDO CENTRALIZADO V2: /aprender
# ==========================================
@bot.message_handler(commands=['aprender'])
def comando_aprender_universal(message):
    if not message.reply_to_message:
        bot.reply_to(message, "🎛️ *Instrucciones de Mando:*\nPara usar el sistema V2, envíe primero el link, video o archivo al chat, y luego respóndale escribiendo `/aprender [parámetros]`.", parse_mode="Markdown")
        return

    m_origen = message.reply_to_message
    argumentos = message.text.replace('/aprender', '').strip()
    texto_evaluar = m_origen.text or m_origen.caption or ""
    
    # 🔍 VECTOR 1: Procesamiento de Enlaces (Wikis o YouTube)
    if "http://" in texto_evaluar or "https://" in texto_evaluar:
        urls = [palabra for palabra in texto_evaluar.split() if palabra.startswith("http")]
        if not urls:
            bot.reply_to(message, "❌ No se detectó una URL válida en el mensaje de origen.")
            return
        url_objetivo = urls[0]

        # CASO A: Enlace de YouTube
        if "youtube.com" in url_objetivo or "youtu.be" in url_objetivo:
            if not argumentos:
                bot.reply_to(message, "⚠️ *Error Táctico:* Para indexar videos de YouTube, defina la ruta de destino.\nEjemplo: `/aprender Sistemas/Batocera/Tutoriales`", parse_mode="Markdown")
                return
            
            msg_espera = bot.reply_to(message, "📡 Conectando con los metadatos de YouTube...")
            res_yt = scraper.extraer_titulo_youtube(url_objetivo)
            
            if res_yt:
                exito = database.crear_acceso_youtube_en_ruta(DRIVE_FOLDER_ID, argumentos, res_yt['titulo'], res_yt['url_original'])
                if exito:
                    bot.edit_message_text(f"✅ *Indexado con éxito (0% Espacio):*\n📂 Ruta: `{argumentos}`\n🎥 Video: `{res_yt['titulo']}`", message.chat.id, msg_espera.message_id, parse_mode="Markdown")
                else:
                    bot.edit_message_text("❌ Error al desplegar el archivo de acceso en Drive.", message.chat.id, msg_espera.message_id)
            else:
                bot.edit_message_text("❌ No se pudo extraer la información del vídeo.", message.chat.id, msg_espera.message_id)
            return

        # CASO B: Enlace de Wiki (Procesamiento con IA y Raspado de Imágenes)
        else:
            msg_espera = bot.reply_to(message, "🕷️ Raspando contenido de la web y ejecutando purga de basura...")
            datos_wiki = scraper.raspar_wiki_universal(url_objetivo)
            
            if not datos_wiki or not datos_wiki['contenido']:
                bot.edit_message_text("❌ Error al infiltrarse en la URL o cuerpo web vacío.", message.chat.id, msg_espera.message_id)
                return
                
            bot.edit_message_text("🧠 Contenido purgado. Transmitiendo datos a la cascada de IA...", message.chat.id, msg_espera.message_id)
            ia_resultado, canal_activo = analizar_con_cascada_ia(datos_wiki['contenido'])
            
            if not ia_resultado:
                bot.edit_message_text("🚨 Error crítico: Ningún canal de IA pudo procesar la información.", message.chat.id, msg_espera.message_id)
                return
                
            bot.edit_message_text(f"🗄️ Clasificación aprobada por {canal_activo}.\nDesplegando estructuras en Drive...", message.chat.id, msg_espera.message_id)
            
            ruta_ia = ia_resultado['ruta']
            titulo_ia = ia_resultado['titulo']
            resumen_ia = ia_resultado['resumen']
            
            exito_txt = database.crear_documento_en_ruta(DRIVE_FOLDER_ID, ruta_ia, titulo_ia, resumen_ia)
            
            imagenes_subidas = 0
            if exito_txt and datos_wiki['imagenes']:
                for i, img_url in enumerate(datos_wiki['imagenes']):
                    try:
                        r_img = requests.get(img_url, timeout=5)
                        if r_img.status_code == 200:
                            flujo_img = io.BytesIO(r_img.content)
                            nombre_img = f"{titulo_ia}_adjunto_{i+1}.jpg"
                            database.subir_archivo_binario_en_ruta(DRIVE_FOLDER_ID, ruta_ia, nombre_img, flujo_img, 'image/jpeg')
                            imagenes_subidas += 1
                    except:
                        continue

            if exito_txt:
                bot.edit_message_text(f"⚡ *Operación Completada por {canal_activo}*\n📂 *Ruta:* `{ruta_ia}`\n📄 *Archivo:* `{titulo_ia}.txt`\n📸 *Imágenes enlazadas:* {imagenes_subidas}", message.chat.id, msg_espera.message_id, parse_mode="Markdown")
            else:
                bot.edit_message_text("❌ Error al escribir el reporte final en Google Drive.", message.chat.id, msg_espera.message_id)
            return

    # 📂 VECTOR 2: Gestión de Archivos Binarios Físicos (Imágenes, PDFs, etc.)
    elif m_origen.content_type in ['photo', 'document']:
        if not argumentos:
            bot.reply_to(message, "⚠️ *Error de Coordenadas:* Indique la ruta y el nombre deseado.\nEjemplo: `/aprender Sistemas/Batocera/Hardware esquema_pantalla`", parse_mode="Markdown")
            return
            
        msg_espera = bot.reply_to(message, "📥 Capturando transmisión de archivo en la RAM de Render...")
        
        try:
            if m_origen.content_type == 'photo':
                file_id = m_origen.photo[-1].file_id
                mime_type = 'image/jpeg'
                extension = '.jpg'
            else:
                file_id = m_origen.document.file_id
                mime_type = m_origen.document.mime_type
                extension = os.path.splitext(m_origen.document.file_name)[1] or '.dat'

            partes_args = argumentos.split()
            if len(partes_args) > 1:
                nombre_archivo = partes_args[-1] + extension
                ruta_destino = " ".join(partes_args[:-1])
            else:
                nombre_archivo = f"archivo_archivado_{message.message_id}{extension}"
                ruta_destino = partes_args[0]

            file_info = bot.get_file(file_id)
            binario_descargado = bot.download_file(file_info.file_path)
            flujo_bytes = io.BytesIO(binario_descargado)
            
            exito_bin = database.subir_archivo_binario_en_ruta(DRIVE_FOLDER_ID, ruta_destino, nombre_archivo, flujo_bytes, mime_type)
            
            if exito_bin:
                bot.edit_message_text(f"✅ *Archivo Físico Almacenado:*\n📂 Ruta: `{ruta_destino}`\n📦 Nombre: `{nombre_archivo}`", message.chat.id, msg_espera.message_id, parse_mode="Markdown")
            else:
                bot.edit_message_text("❌ Falló la transmisión binaria hacia Google Drive.", message.chat.id, msg_espera.message_id)
                
        except Exception as e:
            bot.edit_message_text(f"🚨 Error crítico en el módulo de archivos: {e}", message.chat.id, msg_espera.message_id)
        return

    else:
        bot.reply_to(message, "❌ El mensaje al que responde no contiene un formato compatible (Link, Video, Foto o PDF).")


# ==========================================
# 🚀 HILO INMORTAL DE ESCUCHA (TELEGRAM POLLING)
# ==========================================
def lanzar_polling_bot():
    """Ejecuta la escucha en un bucle infinito autorreparable ante caídas de red."""
    while True:
        try:
            # Protegemos el polling para que no falle si el token es el temporal (DUMMY)
            if bot.token == 'DUMMY':
                print("⏳ Esperando inyección de variables de entorno de Render...", flush=True)
                time.sleep(5)
                # Actualiza el token si Render lo acaba de cargar
                bot.token = os.environ.get('TELEGRAM_BOT_TOKEN', 'DUMMY')
                continue

            print("🧹 [SISTEMA] Removiendo ganchos y webhooks antiguos de Telegram...", flush=True)
            bot.remove_webhook()
            print("🛰️ [SISTEMA CENTRAL] Hilo secundario del bot iniciado de forma segura.", flush=True)
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"🚨 [ALERTA] Caída crítica detectada en el hilo del bot: {e}. Reiniciando bucle en 10 segundos...", flush=True)
            time.sleep(10)


if __name__ == "__main__":
    # 1. Desplegar el Bot de Telegram de fondo de manera inmortal
    hilo_bot = threading.Thread(target=lanzar_polling_bot, daemon=True)
    hilo_bot.start()
    
    # 2. Levantar Flask en el hilo principal acoplándose al puerto dinámico de Render
    puerto = int(os.environ.get("PORT", 8080))
    print(f"🌍 [FLASK] Escuchando solicitudes en el puerto {puerto}. Infraestructura en línea para el Monitor.", flush=True)
    app.run(host="0.0.0.0", port=puerto)
