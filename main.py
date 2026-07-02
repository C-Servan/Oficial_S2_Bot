import os
import io
import json
import telebot
import requests
import scraper
import database

# ==========================================
# 🛰️ CONFIGURACIÓN DE RESTRICCIONES Y LLAVES
# ==========================================
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID') # Asegúrese de que coincide con su variable en Render

# Llaves del Sistema de Cascada Cognitiva
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')
GROQ_KEY = os.environ.get('GROQ_API_KEY')
DEEPSEEK_KEY = os.environ.get('DEEPSEEK_API_KEY')

bot = telebot.TeleBot(TOKEN)

# ==========================================
# ⚡ MOTOR DE CASCADA COGNITIVA (AI FALLBACK)
# ==========================================
def analizar_con_cascada_ia(texto_art):
    """
    Gestiona la línea de contingencia de tres canales. 
    Fuerza a las IAs a devolver una estructura de datos limpia (JSON).
    """
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

    # --- 🔴 CANAL ALPHA: Gemini (Google) ---
    if GEMINI_KEY:
        print("🔴 [CASCADA] Activando Canal Alpha: Gemini...", flush=True)
        try:
            url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
            payload = {"contents": [{"parts": [{"text": prompt_maestro}]}]}
            res = requests.post(url_gemini, json=payload, timeout=15)
            if res.status_code == 200:
                raw_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                # Sanitizar si la IA envuelve el JSON en bloques de marcado
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                return json.loads(raw_text), "🔴 [Canal Alpha - Gemini]"
        except Exception as e:
            print(f"⚠️ [CASCADA] Falló Canal Alpha: {e}. Derivando al frente de reserva...", flush=True)

    # --- 🔵 CANAL BRAVO: Groq / Llama 3 (Meta) ---
    if GROQ_KEY:
        print("🔵 [CASCADA] Activando Canal Bravo: Groq...", flush=True)
        try:
            url_groq = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": prompt_maestro}],
                "temperature": 0.2
            }
            res = requests.post(url_groq, json=payload, timeout=15)
            if res.status_code == 200:
                raw_text = res.json()['choices'][0]['message']['content']
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                return json.loads(raw_text), "🔵 [Canal Bravo - Groq]"
        except Exception as e:
            print(f"⚠️ [CASCADA] Falló Canal Bravo: {e}. Activando última línea de defensa...", flush=True)

    # --- 🟢 CANAL CHARLIE: DeepSeek (Reserva Final) ---
    if DEEPSEEK_KEY:
        print("🟢 [CASCADA] Activando Canal Charlie: DeepSeek...", flush=True)
        try:
            url_deepseek = "https://api.deepseek.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt_maestro}],
                "temperature": 0.2
            }
            res = requests.post(url_deepseek, json=payload, timeout=15)
            if res.status_code == 200:
                raw_text = res.json()['choices'][0]['message']['content']
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                return json.loads(raw_text), "🟢 [Canal Charlie - DeepSeek]"
        except Exception as e:
            print(f"🚨 [CASCADA] Línea de defensa rota. Fallaron todos los canales: {e}", flush=True)

    return None, None


# ==========================================
# 🛰️ COMANDO CENTRALIZADO V2: /aprender
# ==========================================
@bot.message_handler(commands=['aprender'])
def comando_aprender_universal(message):
    """Analizador táctico multifunción mediante el uso de Respuestas (Replies)."""
    
    # Defensa básica: Validar que sea una respuesta
    if not message.reply_to_message:
        bot.reply_to_message(message, "🎛️ *Instrucciones de Mando:*\nPara usar el sistema V2, envíe primero el link, video o archivo al chat, y luego respóndale escribiendo `/aprender [parámetros]`.", parse_mode="Markdown")
        return

    m_origen = message.reply_to_message
    argumentos = message.text.replace('/aprender', '').strip()
    
    # Detectar el texto principal (puede venir en el mensaje o en el comentario de un archivo)
    texto_evaluar = m_origen.text or m_origen.caption or ""
    
    # 🔍 VECTOR 1: Detección de Enlaces Web (Wikis o YouTube)
    if "http://" in texto_evaluar or "https://" in texto_evaluar:
        # Extraer la URL exacta del texto
        urls = [palabra for palabra in texto_evaluar.split() if palabra.startswith("http")]
        if not urls:
            bot.reply_to_message(message, "❌ No se detectó una URL válida en el mensaje de origen.")
            return
        url_objetivo = urls[0]

        # CASO A: Enlace de YouTube
        if "youtube.com" in url_objetivo or "youtu.be" in url_objetivo:
            if not argumentos:
                bot.reply_to_message(message, "⚠️ *Error Táctico:* Para indexar videos de YouTube, defina la ruta de destino.\nEjemplo: `/aprender Sistemas/Batocera/Tutoriales`", parse_mode="Markdown")
                return
            
            msg_espera = bot.reply_to_message(message, "📡 Conectando con los metadatos de YouTube...")
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

        # CASO B: Enlace de Wiki (Análisis con IA)
        else:
            msg_espera = bot.reply_to_message(message, "🕷️ Raspando contenido de la web y ejecutando purga de basura...")
            datos_wiki = scraper.raspar_wiki_universal(url_objetivo)
            
            if not datos_wiki or not datos_wiki['contenido']:
                bot.edit_message_text("❌ Error al infiltrarse en la URL o cuerpo web vacío.", message.chat.id, msg_espera.message_id)
                return
                
            bot.edit_message_text("🧠 Contenido purgado. Transmitiendo datos a la cascada de IA...", message.chat.id, msg_espera.message_id)
            ia_resultado, canal_activo = analizar_con_cascada_ia(datos_wiki['contenido'])
            
            if not ia_resultado:
                bot.edit_message_text("🚨 Error crítico: Ningún canal de IA pudo procesar la información.", message.chat.id, msg_espera.message_id)
                return
                
            # Desplegar el documento de texto curado por la IA en Drive
            bot.edit_message_text(f"🗄️ Clasificación aprobada por {canal_activo}.\nDesplegando estructuras en Drive...", message.chat.id, msg_espera.message_id)
            
            ruta_ia = ia_resultado['ruta']
            titulo_ia = ia_resultado['titulo']
            resumen_ia = ia_resultado['resumen']
            
            exito_txt = database.crear_documento_en_ruta(DRIVE_FOLDER_ID, ruta_ia, titulo_ia, resumen_ia)
            
            # Descargar y archivar imágenes adjuntas si existen en el artículo
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
                        continue # Si una imagen falla, el bot prosigue con el despliegue

            if exito_txt:
                bot.edit_message_text(f"⚡ *Operación Completada por {canal_activo}*\n📂 *Ruta:* `{ruta_ia}`\n📄 *Archivo:* `{titulo_ia}.txt`\n📸 *Imágenes enlazadas:* {imagenes_subidas}", message.chat.id, msg_espera.message_id, parse_mode="Markdown")
            else:
                bot.edit_message_text("❌ Error al escribir el reporte final en Google Drive.", message.chat.id, msg_espera.message_id)
            return

    # 📂 VECTOR 2: Gestión de Archivos Físicos (Fotos o PDFs)
    elif m_origen.content_type in ['photo', 'document']:
        if not argumentos:
            bot.reply_to_message(message, "⚠️ *Error de Coordenadas:* Indique la ruta y el nombre deseado.\nEjemplo: `/aprender Sistemas/Batocera/Hardware esquema_pantalla`", parse_mode="Markdown")
            return
            
        msg_espera = bot.reply_to_message(message, "📥 Capturando transmisión de archivo en la RAM de Render...")
        
        try:
            # Procesar si es una Foto
            if m_origen.content_type == 'photo':
                file_id = m_origen.photo[-1].file_id # Máxima resolución disponible
                mime_type = 'image/jpeg'
                extension = '.jpg'
            # Procesar si es un Documento (PDF u otros)
            else:
                file_id = m_origen.document.file_id
                mime_type = m_origen.document.mime_type
                extension = os.path.splitext(m_origen.document.file_name)[1] or '.dat'

            # Desglosar los argumentos en Ruta + Nombre
            partes_args = argumentos.split()
            if len(partes_args) > 1:
                nombre_archivo = partes_args[-1] + extension
                ruta_destino = " ".join(partes_args[:-1])
            else:
                nombre_archivo = f"archivo_archivado_{message.message_id}{extension}"
                ruta_destino = partes_args[0]

            # Descarga del binario
            file_info = bot.get_file(file_id)
            binario_descargado = bot.download_file(file_info.file_path)
            flujo_bytes = io.BytesIO(binario_descargado)
            
            # Subir a Drive
            exito_bin = database.subir_archivo_binario_en_ruta(DRIVE_FOLDER_ID, ruta_destino, nombre_archivo, flujo_bytes, mime_type)
            
            if exito_bin:
                bot.edit_message_text(f"✅ *Archivo Físico Almacenado:*\n📂 Ruta: `{ruta_destino}`\n📦 Nombre: `{nombre_archivo}`", message.chat.id, msg_espera.message_id, parse_mode="Markdown")
            else:
                bot.edit_message_text("❌ Falló la transmisión binaria hacia Google Drive.", message.chat.id, msg_espera.message_id)
                
        except Exception as e:
            bot.edit_message_text(f"🚨 Error crítico en el módulo de archivos: {e}", message.chat.id, msg_espera.message_id)
        return

    else:
        bot.reply_to_message(message, "❌ El mensaje al que responde no contiene un formato compatible (Link, Video, Foto o PDF).")

# ==========================================
# 🚀 ARRANQUE DE SISTEMAS EN RENDER
# ==========================================
if __name__ == "__main__":
    print("🛰️ [SISTEMA CENTRAL] Servidor V2 operativo. Escuchando canales...", flush=True)
    bot.infinity_polling()
