import os
import telebot
from flask import Flask
from threading import Thread
from ai_cascade import procesar_consulta_cascada
from database import (
    obtener_servicio_drive, 
    buscar_subcarpeta_por_nombre, 
    leer_texto_de_documento, 
    crear_documento_autonomo,
    crear_documento_en_ruta  # Nuevo componente táctico para resolver subcarpetas multinivel
)

# --- CONFIGURACIÓN DE VARIABLES DE ENTORNO ---
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CARPETA_RAIZ_MANUALES_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")

# Validación crítica de la línea de suministro
if not TOKEN or not CARPETA_RAIZ_MANUALES_ID:
    raise ValueError("🚨 [CRÍTICO] Faltan variables de entorno esenciales (TELEGRAM_BOT_TOKEN o GOOGLE_DRIVE_FOLDER_ID) en Render.")

bot = telebot.TeleBot(TOKEN)

# --- CADENA DE MANDO (IDs DE TELEGRAM) ---
# REQUISITO RECOMENDADO: Edite estos IDs con sus números reales de Telegram
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
        
    # Extraer palabras clave de más de 3 letras para la búsqueda (ej: 'gun4ir', 'batocera')
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
            
        # Tomamos el primer archivo de coincidencia exacta como base de verdad
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
        saludo += "• Comando de archivo activo: `/aprender [ruta/subcarpetas] [titulo] [contenido]`"
    bot.reply_to(message, saludo, parse_mode="Markdown")

@bot.message_handler(commands=['aprender'])
def comando_aprender(message):
    """
    Protocolo de Auto-Aprendizaje. Organiza los manuales en subcarpetas específicas y profundas.
    Formato: /aprender [ruta/subcarpeta/subsubcarpeta] [titulo] [contenido]
    """
    user_id = message.from_user.id
    rango = obtener_rango_usuario(user_id)
    
    # Restricción estricta de seguridad perimetral
    if rango == "recluta":
        bot.reply_to(message, "❌ ¡Negativo Recluta! No tiene autorización de nivel S-2 para alterar los registros del servidor. Aléjese de la consola.")
        return

    # Extraer los argumentos del comando
    argumentos = telebot.util.extract_arguments(message.text)
    partes = argumentos.strip().split(" ", 2) if argumentos else []
    
    if len(partes) < 3:
        bot.reply_to(message, "⚠️ [SISTEMA] Sintaxis incorrecta. Ordene: `/aprender [ruta/subcarpetas] [titulo_archivo] [contenido técnico]`\n\n*Ejemplo:* `/aprender gun4ir/config/errores leds_error Colocar los leds en orden...`", parse_mode="Markdown")
        return
        
    ruta_sectores = partes[0]  # Ahora puede recibir estructuras como 'emulacion/batocera/bios'
    titulo_nuevo = partes[1]
    contenido_nuevo = partes[2]
    
    bot.send_message(message.chat.id, f"💾 [SISTEMA] {rango.upper()} ordenó indexar datos en el sector: `{ruta_sectores}`. Escaneando y creando árbol de directorios...", parse_mode="Markdown")
    
    # Guardar de forma remota en Google Drive resolviendo dinámicamente toda la ruta
    exito = crear_documento_en_ruta(CARPETA_RAIZ_MANUALES_ID, ruta_sectores, titulo_nuevo, contenido_nuevo)
    
    if exito:
        bot.reply_to(message, f"🗄️ [LOG] Almacenamiento completado. El conocimiento técnico *'{titulo_nuevo}'* ha sido archivado con éxito en la ruta de destino: `{ruta_sectores}`.", parse_mode="Markdown")
    else:
        bot.reply_to(message, "🚨 [ERROR] El ala de almacenamiento de Drive no respondió correctamente o el token OAuth2 rechazó la creación de las subcarpetas. Revise Render.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def escuchar_consultas(message):
    """Intercepta cualquier mensaje de texto, busca en Drive y responde con la cascada de IA"""
    # Ignorar comandos si entran por aquí
    if message.text.startswith('/'):
        return
        
    user_id = message.from_user.id
    rango = obtener_rango_usuario(user_id)
    consulta = message.text
    
    # Enviar señal visual de que el bot está procesando los datos
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Paso 1: Extraer el contexto real desde los manuales de Google Drive (RAG)
    contexto_manual = buscar_contexto_en_drive(consulta)
    
    # Paso 2: Ejecutar el análisis cognitivo con el sistema de cascada (Gemini -> Groq -> DeepSeek)
    respuesta_final = procesar_consulta_cascada(rango, consulta, contexto_manual)
    
    # Paso 3: Entregar la respuesta al frente de batalla
    bot.reply_to(message, respuesta_final, parse_mode="Markdown")

# --- PARCHE DE COMPATIBILIDAD PARA RENDER (FLASK DUMMY SERVER) ---
app = Flask('')

@app.route('/')
def home():
    return "Oficial S-2: Servidor en línea y operativo."

def run():
    # Render asigna automáticamente un puerto en la variable de entorno PORT
    puerto = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=puerto)

def mantener_vivo():
    t = Thread(target=run)
    t.start()

# --- ARRANQUE SEGURO DEL MOTOR ---
if __name__ == "__main__":
    print("🌐 [SISTEMA] Activando servidor de flancos para Render...")
    mantener_vivo()  # Engaña a Render diciendo "estoy escuchando el puerto web"
    
    print("🧹 [SISTEMA] Purgando el búfer de Telegram para eliminar duplicados...")
    try:
        # Esto elimina el proceso fantasma y limpia los mensajes acumulados de golpe
        bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"⚠️ [SISTEMA] Nota de purga: {e}")
    
    print("🚀 [SISTEMA] Oficial S-2 desplegado con éxito. Escuchando frecuencias...")
    bot.infinity_polling()
