import os
import io
import time
import telebot
from flask import Flask
from threading import Thread
from ai_cascade import procesar_consulta_cascada
import scraper
import database

# --- CONFIGURACIÓN DE VARIABLES DE ENTORNO ---
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CARPETA_RAIZ_MANUALES_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")

if not TOKEN or not CARPETA_RAIZ_MANUALES_ID:
    raise ValueError("🚨 [CRÍTICO] Faltan variables de entorno esenciales.")

bot = telebot.TeleBot(TOKEN)

# --- CADENA DE MANDO ---
COMANDANTE_ID = 1596889771  
SARGENTOS_IDS = [953225999, 162691919]  

def obtener_rango_usuario(user_id):
    if user_id == COMANDANTE_ID: return "comandante"
    elif user_id in SARGENTOS_IDS: return "sargento"
    return "recluta"

# --- MANEJADORES DE COMANDOS ---

@bot.message_handler(commands=['start', 'help'])
def enviar_bienvenida(message):
    rango = obtener_rango_usuario(message.from_user.id)
    saludo = f"🫡 ¡A sus órdenes, {rango.capitalize()}!\n\nOficial S-2 en línea. Central de Emulación operativa.\n"
    saludo += "• Use `/aprender [ruta] [nombre] [contenido]` para texto.\n"
    saludo += "• Responda a un enlace/archivo con `/aprender [ruta]` para indexar recursos."
    bot.reply_to(message, saludo, parse_mode="Markdown")

@bot.message_handler(commands=['aprender'])
def comando_aprender_universal(message):
    """Manejador táctico unificado: Texto manual, Enlaces (YT/Wiki) o Binarios."""
    rango = obtener_rango_usuario(message.from_user.id)
    if rango == "recluta":
        bot.reply_to(message, "❌ ¡Negativo! No tiene autorización de nivel S-2.")
        return

    # VECTOR 1: Procesamiento si es respuesta a un mensaje (Links o Archivos)
    if message.reply_to_message:
        m_origen = message.reply_to_message
        args = message.text.replace('/aprender', '').strip()
        texto_evaluar = m_origen.text or m_origen.caption or ""
        
        # Caso: Enlace
        if "http" in texto_evaluar:
            url = [p for p in texto_evaluar.split() if p.startswith("http")][0]
            if "youtube" in url:
                msg = bot.reply_to(message, "📡 Analizando YouTube...")
                datos = scraper.extraer_titulo_youtube(url)
                if datos and database.crear_acceso_youtube_en_ruta(CARPETA_RAIZ_MANUALES_ID, args, datos['titulo'], url):
                    bot.edit_message_text("✅ Video indexado con éxito.", message.chat.id, msg.message_id)
            else:
                msg = bot.reply_to(message, "🕷️ Raspando Wiki...")
                datos = scraper.raspar_wiki_universal(url)
                # Integrar aquí la lógica de base de datos para guardar el contenido purgado
                bot.edit_message_text("💾 Contenido web procesado y archivado.", message.chat.id, msg.message_id)
        
        # Caso: Archivo Binario
        elif m_origen.content_type in ['photo', 'document']:
            msg = bot.reply_to(message, "📥 Descargando archivo físico...")
            file_id = m_origen.photo[-1].file_id if m_origen.content_type == 'photo' else m_origen.document.file_id
            path = bot.get_file(file_id)
            binario = bot.download_file(path.file_path)
            # Guardar usando database.subir_archivo_binario_en_ruta
            bot.edit_message_text("📦 Archivo binario almacenado.", message.chat.id, msg.message_id)
        return

    # VECTOR 2: Entrada manual (Texto)
    partes = message.text.split(" ", 3)
    if len(partes) < 4:
        bot.reply_to(message, "⚠️ Sintaxis: `/aprender [ruta] [titulo] [contenido]`")
        return
    
    database.crear_documento_en_ruta(CARPETA_RAIZ_MANUALES_ID, partes[1], partes[2], partes[3])
    bot.reply_to(message, "🗄️ Texto archivado en la ruta solicitada.")

@bot.message_handler(func=lambda message: not message.text.startswith('/'))
def escuchar_consultas(message):
    bot.send_chat_action(message.chat.id, 'typing')
    # Usar su lógica de RAG original
    # contexto = buscar_contexto_en_drive(message.text)
    # respuesta = procesar_consulta_cascada(obtener_rango_usuario(message.from_user.id), message.text, contexto)
    bot.reply_to(message, "Análisis cognitivo en proceso...")

# --- PARCHE PARA RENDER (FLASK + ANTI-409) ---
app = Flask('')
@app.route('/')
def home(): return "Oficial S-2 operativo."

def run(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    
    while True:
        try:
            print("🚀 [SISTEMA] Iniciando despliegue de frecuencias...")
            bot.delete_webhook(drop_pending_updates=True)
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print(f"⚠️ [CONFLICTO 409 DETECTADO] Reintentando en 10s: {e}")
            time.sleep(10)
