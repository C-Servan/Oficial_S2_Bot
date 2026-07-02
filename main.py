import os
import io
import time
import telebot
import requests
from flask import Flask
from threading import Thread
from ai_cascade import procesar_consulta_cascada
import scraper
from database import (
    obtener_servicio_drive, 
    leer_texto_de_documento, 
    crear_documento_en_ruta,
    crear_acceso_youtube_en_ruta,
    subir_archivo_binario_en_ruta
)

# --- CONFIGURACIÓN DE VARIABLES DE ENTORNO ---
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CARPETA_RAIZ_MANUALES_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")

# Validación crítica de la línea de suministro
if not TOKEN or not CARPETA_RAIZ_MANUALES_ID:
    raise ValueError("🚨 [CRÍTICO] Faltan variables de entorno esenciales (TELEGRAM_BOT_TOKEN o GOOGLE_DRIVE_FOLDER_ID) en Render.")

bot = telebot.TeleBot(TOKEN)

# --- CADENA DE MANDO (IDs DE TELEGRAM) ---
COMANDANTE_ID = 1596889771  
SARGENTOS_IDS = [953225999, 162691919]  

def obtener_rango_usuario(user_id):
    """Filtra el ID de Telegram y devuelve el rango militar correspondiente"""
    if user_id == COMANDANTE_ID:
        return "comandante"
    elif user_id in SARGENTOS_IDS:
        return "sargento"
    return "recluta"

def buscar_contexto_en_drive(consulta_usuario):
    """
    RAG (Generación Aumentada por Recuperación):
    Busca palabras clave en los nombres de los archivos dentro de Drive 
    para extraer el manual correcto antes de enviárselo a la cascada de IA.
    """
    service = obtener_servicio_drive()
    if not service:
        return "No hay conexión con los servidores de almacenamiento de Drive."
        
    # Extraer palabras clave de más de 3 letras para la búsqueda
    palabras = [p.lower() for p in consulta_usuario.split() if len(p) > 3]
    if not palabras:
        return "Consulta demasiado genérica para escanear los manuales técnicos."
        
    query_parts = [f"name contains '{p}'" for p in palabras]
    or_query = " or ".join(query_parts)
    query = f"('{CARPETA_RAIZ_MANUALES_ID}' in parents) and ({or_query}) and trashed = false"
    
    try:
        results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        archivos = results.get('files', [])
        
        if not archivos:
            return "No se encontraron manuales específicos para esta anomalía en el servidor principal."
            
        primer_archivo = archivos[0]
        texto_manual = leer_texto_de_documento(primer_archivo['id'], primer_archivo['mimeType'])
        return f"--- MANUAL RECOBRADO DEL SERVIDOR: {primer_archivo['name']} ---\n{texto_manual}"
        
    except Exception as e:
        print(f"⚠️ [SISTEMA] Error en el escaneo RAG de Drive: {e}")
        return "Error de enlace al consultar los almacenes de datos de Drive."

# --- MANEJADORES DE COMANDOS DE TELEGRAM ---

@bot.message_handler(commands=['start', 'help'])
def enviar_bienvenida(message):
    """Mensaje de inicio del bot con formato oficial S-2"""
    rango = obtener_rango_usuario(message.from_user.id)
    saludo = f"🫡 ¡A sus órdenes, {rango.capitalize()}!\n\n"
    saludo += "Oficial S-2 en línea. Central técnica de Lightguns y Emulación operativa.\n"
    saludo += "• Formule su consulta técnica directamente en el chat.\n"
    if rango in ["comandante", "sargento"]:
        saludo += "• Comando de archivo activo: `/aprender [ruta/subcarpetas] [titulo] [contenido]`\n"
        saludo += "• Auto-indexado: Responda a un link/archivo con `/aprender [ruta]`"
    bot.reply_to(message, saludo, parse_mode="Markdown")

@bot.message_handler(commands=['aprender'])
def comando_aprender(message):
    """
    Protocolo de Auto-Aprendizaje. 
    Maneja tanto la inserción manual de texto como la extracción de enlaces/archivos.
    """
    user_id = message.from_user.id
    rango = obtener_rango_usuario(user_id)
    
    if rango == "recluta":
        bot.reply_to(message, "❌ ¡Negativo Recluta! No tiene autorización de nivel S-2 para alterar los registros.")
        return

    argumentos = telebot.util.extract_arguments(message.text) or ""

    # VECTOR 1: Si se responde a un mensaje (Links, Archivos, Imágenes)
    if message.reply_to_message:
        m_origen = message.reply_to_message
        texto_evaluar = m_origen.text or m_origen.caption or ""
        ruta_destino = argumentos.strip()

        if not ruta_destino:
            bot.reply_to(message, "⚠️ [SISTEMA] Indique la ruta de destino al responder. Ej: `/aprender emulacion/batocera`", parse_mode="Markdown")
            return

        # Es un enlace
        if "http://" in texto_evaluar or "https://" in texto_evaluar:
            urls = [p for p in texto_evaluar.split() if p.startswith("http")]
            if not urls:
                bot.reply_to(message, "❌ No se pudo extraer un enlace válido.")
                return
                
            url_objetivo = urls[0]
            
            if "youtube.com" in url_objetivo or "youtu.be" in url_objetivo:
                msg_espera = bot.reply_to(message, "📡 Analizando metadatos de YouTube...")
                res_yt = scraper.extraer_titulo_youtube(url_objetivo)
                if res_yt and crear_acceso_youtube_en_ruta(CARPETA_RAIZ_MANUALES_ID, ruta_destino, res_yt['titulo'], url_objetivo):
                    bot.edit_message_text(f"✅ *Video indexado:*\n📂 `{ruta_destino}`\n🎥 `{res_yt['titulo']}`", message.chat.id, msg_espera.message_id, parse_mode="Markdown")
                else:
                    bot.edit_message_text("❌ Error al guardar en Drive.", message.chat.id, msg_espera.message_id)
            else:
                msg_espera = bot.reply_to(message, "🕷️ Extrayendo contenido web...")
                datos_wiki = scraper.raspar_wiki_universal(url_objetivo)
                if datos_wiki and datos_wiki['contenido']:
                    crear_documento_en_ruta(CARPETA_RAIZ_MANUALES_ID, ruta_destino, "Documento_Web_Raspado", datos_wiki['contenido'][:2000]) # Resumen básico temporal
                    bot.edit_message_text(f"✅ *Web indexada en:*\n📂 `{ruta_destino}`", message.chat.id, msg_espera.message_id, parse_mode="Markdown")
                else:
                    bot.edit_message_text("❌ Fallo al raspar la web.", message.chat.id, msg_espera.message_id)
            return

        # Es un archivo
        elif m_origen.content_type in ['photo', 'document']:
            msg_espera = bot.reply_to(message, "📥 Capturando archivo...")
            try:
                if m_origen.content_type == 'photo':
                    file_id = m_origen.photo[-1].file_id
                    mime_type = 'image/jpeg'
                    nombre_archivo = f"img_{message.message_id}.jpg"
                else:
                    file_id = m_origen.document.file_id
                    mime_type = m_origen.document.mime_type
                    nombre_archivo = m_origen.document.file_name

                file_info = bot.get_file(file_id)
                binario = bot.download_file(file_info.file_path)
                
                if subir_archivo_binario_en_ruta(CARPETA_RAIZ_MANUALES_ID, ruta_destino, nombre_archivo, io.BytesIO(binario), mime_type):
                    bot.edit_message_text(f"✅ *Archivo guardado:*\n📂 `{ruta_destino}`\n📦 `{nombre_archivo}`", message.chat.id, msg_espera.message_id, parse_mode="Markdown")
                else:
                    bot.edit_message_text("❌ Falló la subida a Drive.", message.chat.id, msg_espera.message_id)
            except Exception as e:
                bot.edit_message_text(f"🚨 Error: {e}", message.chat.id, msg_espera.message_id)
            return

    # VECTOR 2: Estructura original de inserción manual de texto
    partes = argumentos.strip().split(" ", 2) if argumentos else []
    
    if len(partes) < 3:
        bot.reply_to(message, "⚠️ [SISTEMA] Sintaxis incorrecta. Ordene: `/aprender [ruta/subcarpetas] [titulo_archivo] [contenido técnico]`", parse_mode="Markdown")
        return
        
    ruta_sectores = partes[0]
    titulo_nuevo = partes[1]
    contenido_nuevo = partes[2]
    
    bot.send_message(message.chat.id, f"💾 [SISTEMA] Escaneando y creando árbol de directorios...", parse_mode="Markdown")
    
    exito = crear_documento_en_ruta(CARPETA_RAIZ_MANUALES_ID, ruta_sectores, titulo_nuevo, contenido_nuevo)
    
    if exito:
        bot.reply_to(message, f"🗄️ [LOG] Almacenamiento completado. *'{titulo_nuevo}'* ha sido archivado en: `{ruta_sectores}`.", parse_mode="Markdown")
    else:
        bot.reply_to(message, "🚨 [ERROR] Fallo de comunicación con Drive. Revise Render.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def escuchar_consultas(message):
    """Intercepta cualquier mensaje de texto, busca en Drive y responde con la cascada de IA"""
    if message.text.startswith('/'):
        return
        
    user_id = message.from_user.id
    rango = obtener_rango_usuario(user_id)
    consulta = message.text
    
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Paso 1: Extraer el contexto real desde los manuales de Google Drive (RAG)
    contexto_manual = buscar_contexto_en_drive(consulta)
    
    # Paso 2: Ejecutar el análisis cognitivo con el sistema de cascada (Gemini -> Groq -> DeepSeek)
    respuesta_final = procesar_consulta_cascada(rango, consulta, contexto_manual)
    
    # Paso 3: Entregar la respuesta
    bot.reply_to(message, respuesta_final, parse_mode="Markdown")

# --- PARCHE DE COMPATIBILIDAD PARA RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Oficial S-2: Servidor en línea y operativo."

def run():
    puerto = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=puerto)

def mantener_vivo():
    t = Thread(target=run, daemon=True)
    t.start()

# --- ARRANQUE SEGURO Y ANTI-409 ---
if __name__ == "__main__":
    print("🌐 [SISTEMA] Activando servidor de flancos para Render...")
    mantener_vivo() 
    
    while True:
        try:
            print("🧹 [SISTEMA] Purgando webhooks fantasma...")
            bot.delete_webhook(drop_pending_updates=True)
            print("🚀 [SISTEMA] Oficial S-2 desplegado. Escuchando frecuencias...")
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"⚠️ [ALERTA] Caída detectada (posible Conflicto 409): {e}. Reiniciando en 10s...")
            time.sleep(10)
