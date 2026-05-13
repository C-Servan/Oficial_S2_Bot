import os
import threading
from flask import Flask
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- MINI SERVIDOR PARA RENDER ---
app = Flask(__name__)
@app.route('/')
def health_check():
    return "Oficial S-2 Operativo", 200

def run_flask():
    # Render asigna un puerto automáticamente en la variable PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURACIÓN DE SEGURIDAD ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_KEY')

# --- CONFIGURACIÓN DE INTELIGENCIA ---
genai.configure(api_key=GEMINI_KEY)

# Carga del manual de inteligencia
try:
    with open("prom_Oficial_Inteligencia.txt", "r", encoding="utf-8") as f:
        instrucciones_sistema = f.read()
except FileNotFoundError:
    instrucciones_sistema = "Eres el Oficial S-2 de GUN4FUN. Manual no encontrado. Procede con protocolos estándar."

# Configuración del modelo - RECALIBRADO a 'gemini-1.5-flash-latest' para máxima compatibilidad
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    system_instruction=instrucciones_sistema
)

# --- LÓGICA DE RESPUESTA CON DIAGNÓSTICO ---
async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    username = f"@{user.username}" if user.username else "Recluta"
    mensaje_texto = update.message.text

    # El bot sabe quién le habla para aplicar la jerarquía
    contexto_usuario = f"[Mensaje de {username}]: "
    
    try:
        # Intento de comunicación con el núcleo Gemini
        # Se usa generate_content directo para mayor estabilidad ante errores de versión
        response = model.generate_content(contexto_usuario + mensaje_texto)
        await update.message.reply_text(response.text)
        
    except Exception as e:
        # LOGS DETALLADOS PARA EL COMANDANTE
        error_msg = str(e)
        print(f"--- ERROR TÁCTICO DETECTADO ---")
        print(f"Detalle del error: {error_msg}")
        print(f"-------------------------------")
        
        # SISTEMA DE RESPALDO AUTOMÁTICO EN CASO DE 404
        if "404" in error_msg:
            try:
                backup_model = genai.GenerativeModel("gemini-pro")
                resp = backup_model.generate_content(f"{instrucciones_sistema}\n\n{contexto_usuario}{mensaje_texto}")
                await update.message.reply_text(resp.text)
            except Exception as e_backup:
                await update.message.reply_text(f"❌ Fallo total de enlace. Revise API KEY.\nDetalle: {e_backup}")
        else:
            # Respuesta en Telegram indicando el fallo de enlace genérico
            await update.message.reply_text(
                f"⚠️ Interferencia crítica en el enlace. Error detectado en el núcleo.\n"
                f"Comandante, verifique los logs de Render para la instrucción de recalibrado."
            )

# --- LANZAMIENTO ---
def main():
    if not TELEGRAM_TOKEN or not GEMINI_KEY:
        print("ERROR: Faltan las llaves de acceso en las variables de entorno.")
        return

    # Ejecución del hilo para evitar el timeout en Render
    threading.Thread(target=run_flask, daemon=True).start()

    # Configuración de la aplicación de Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje))
    
    print("Oficial de Inteligencia S-2 en línea. ¡RELOAD!")
    # drop_pending_updates=True evita que el bot se colapse con mensajes antiguos al reiniciar
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
