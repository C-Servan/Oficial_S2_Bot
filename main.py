# main.py
import os
import threading
import time
import json
import re
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import (
    Application, 
    MessageHandler, 
    CommandHandler, 
    CallbackQueryHandler, 
    ConversationHandler, 
    filters, 
    ContextTypes
)

# Inyección de módulos tácticos propios
import database
import ai_cascade
import menus

# Librerías nativas para extracción web segura y raspado de datos
import urllib.request
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# --- 1. CONFIGURACIÓN DEL SERVIDOR WEB ---
app = Flask(__name__)
@app.route('/')
def health_check():
    return "Oficial S-2 Operativo (Protocolos System S2 Modulares Activos)", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. SISTEMA TÁCTICO DE INGESTA MULTIMEDIA POR OLEADAS ---
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
            
            imagenes_encontradas = []
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and not src.startswith('data:'):
                    url_completa = urljoin(url_objetivo, src)
                    if url_completa not in imagenes_encontradas:
                        imagenes_encontradas.append(url_completa)
            
            videos_encontrados = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'youtube.com' in href or 'youtu.be' in href:
                    url_video = urljoin(url_objetivo, href)
                    if url_video not in videos_encontrados:
                        videos_encontrados.append(url_video)

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

def ejecutar_ingesta_base_datos(username: str, comando_texto: str) -> str:
    """Descarga la información existente, genera un índice dinámico y procesa la web por secciones secuenciales."""
    autorizados = ["@carlosfservan", "@gargarensis76", "@gwyllion16"]
    if username.lower() not in autorizados:
        return f"Recluta, transmision denegada. No posees autorización de escritura en los Archivos de Inteligencia S-2."

    partes = comando_texto.replace("/guardar", "").split("|")
    rama_detectada = "1_Manuales_tecnicos"
    subnodo_detectado = "desconocido"
    
    if len(partes) >= 2:
        rama_detectada = partes[0].strip()
        subnodo_detectado = partes[1].strip().lower().replace(" ", "")

    datos_existentes = {}
    try:
        from firebase_admin import db
        ref_existente = db.reference(f'Enciclopedia_S2/{rama_detectada}/{subnodo_detectado}')
        nodo_actual = ref_existente.get()
        if nodo_actual:
            datos_existentes = nodo_actual
    except Exception as e:
        print(f"Aviso: No se pudo leer el histórico: {e}")

    contenido_web = extraer_contenido_url(comando_texto)
    if not contenido_web or "[ERROR TÉCNICO" in contenido_web:
        return f"Error en la extracción de la URL. Abortando misión: {contenido_web}"

    prompt_indexador = (
        "Actúas como el Ingeniero de Reconocimiento del Oficial S-2. Tu único objetivo es analizar la información textual extraída de una web "
        "y estructurar un ÍNDICE DINÁMICO de categorías estandarizadas.\n\n"
        "Responde ÚNICAMENTE con la lista de categorías separadas por comas."
    )

    try:
        indice_raw, canal_indexador = ai_cascade.ejecutar_ia_con_cascada(prompt_indexador, contenido_web)
        indice_raw = re.sub(r'[`\s\n]', '', indice_raw)
        categorias = [cat.strip() for cat in indice_raw.split(",") if cat.strip()]
        if not categorias:
            categorias = ["Manual_Instalacion", "Calibracion_Hardware", "FAQ", "Resolucion_Problemas"]
    except Exception as err_idx:
        print(f"Fallo en indexador dinámico, aplicando categorías base: {err_idx}")
        categorias = ["Manual_Instalacion", "Calibracion_Hardware", "FAQ", "Resolucion_Problemas"]

    payload_acumulado = {}
    canales_utilizados = []
    
    urls_en_texto = re.findall(r'\"(https?://[^\s"]+)\"', contenido_web)
    nuevas_img = [u for u in urls_en_texto if any(ext in u.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])]
    nuevos_vid = [u for u in urls_en_texto if 'youtube.com' in u.lower() or 'youtu.be' in u.lower()]

    for category in categorias:
        texto_historico_categoria = datos_existentes.get(category, "No hay registros preexistentes de esta categoría.")
        datos_oleada_ia = (
            f"=== CATEGORÍA A PROCESAR ===\n{category}\n\n"
            f"=== HISTÓRICO ALMACENADO ===\n{texto_historico_categoria}\n\n"
            f"=== CONTENIDO COMPLETO DE LA NUEVA WEB ===\n{contenido_web}"
        )

        prompt_oleada = (
            f"Actúas como el Especialista de Ingesta Táctica S-2 para la sección '{category}'. Tu misión es extraer de manera quirúrgica "
            f"toda la información de la nueva web que corresponda EXCLUSIVAMENTE a la temática de la categoría '{category}' y fusionarla con el histórico.\n\n"
            f"Responde ÚNICAMENTE con el desarrollo de texto de la sección unificada."
        )

        try:
            texto_fusionado, canal_oleada = ai_cascade.ejecutar_ia_con_cascada(prompt_oleada, datos_oleada_ia)
            payload_acumulado[category] = texto_fusionado.strip()
            if canal_oleada not in canales_utilizados:
                canales_utilizados.append(canal_oleada)
            time.sleep(0.5)
        except Exception as err_oleada:
            print(f"Error procesando la oleada {category}: {err_oleada}")
            payload_acumulado[category] = texto_historico_categoria

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
        from firebase_admin import db
        ref = db.reference(f'Enciclopedia_S2/{rama_detectada}/{subnodo_detectado}')
        ref.update(payload_final)
        
        prefijo_rango = "Comandante" if username.lower() == "@carlosfservan" else "Sargento"
        canales_str = ", ".join(canales_utilizados)
        return (
            f"[{canales_str}]\n\n"
            f"¡Fase 2 Completada con éxito, {prefijo_rango}! El sistema ha mapeado dinámicamente un índice de {len(categorias)} categorías. "
            f"La información ha sido procesada por oleadas y fusionada de manera incremental."
        )
    except Exception as err:
        return f"Error crítico al inyectar el payload consolidado en Firebase: {str(err)}."

# --- 3. PROCESADOR PRINCIPAL DE MENSAJES E INTEGRACIÓN DE IA ---
async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Soporte polimórfico: Maneja tanto mensajes directos como redirecciones de CallbackQueries de botones
    is_callback = update.callback_query is not None
    
    if is_callback:
        user = update.callback_query.from_user
        msg_obj = update.callback_query.message
        mensaje_usuario = msg_obj.text.strip() if msg_obj.text else ""
    else:
        if not update.message or not update.message.text:
            return
        user = update.message.from_user
        msg_obj = update.message
        mensaje_usuario = msg_obj.text.strip()

    username = f"@{user.username}" if user.username else user.first_name

    # INTERCEPTOR DE COMANDO /GUARDAR (Exclusivo para mensajes directos de texto)
    if not is_callback and mensaje_usuario.startswith("/guardar"):
        resultado_guardado = ejecutar_ingesta_base_datos(username, mensaje_usuario)
        await msg_obj.reply_text(f"{resultado_guardado}\n\nCambio y corto. ¡RELOAD!")
        return

    # COMANDO O PREGUNTA DE ESTADO SISTEMA
    if not is_callback and mensaje_usuario.lower() in ["/estado", "estado", "¿con qué ia estás trabajando?", "con que ia estas trabajando"]:
        reporte_estado = (
            "📊 **INFORME DE ESTADO OPERATIVO - OFICIAL S-2**\n"
            f"• Canal Alpha (Groq - {ai_cascade.MODELO_GROQ}): {'🟢 ONLINE' if ai_cascade.GROQ_API_KEY else '🔴 OFFLINE'}\n"
            f"• Canal Bravo (Mistral - Small): {'🟢 ONLINE' if ai_cascade.MISTRAL_API_KEY else '🔴 OFFLINE'}\n"
            f"• Canal Charlie (DeepSeek - Chat): {'🟢 ONLINE' if ai_cascade.DEEPSEEK_API_KEY else '🔴 OFFLINE'}\n\n"
            "**Prioridad de Enrutamiento:** Cascada Táctica (Alpha ➡️ Bravo ➡️ Charlie).\n"
            "El sistema responderá utilizando el canal prioritario disponible."
        )
        await msg_obj.reply_text(reporte_estado, parse_mode="Markdown")
        return

    # ANALIZADOR DE CONTEXTO REAL EN FIREBASE
    if "forzar_subnodo" in context.user_data:
        subnodo_elegido = context.user_data.pop("forzar_subnodo")
        from firebase_admin import db
        mapa = database.obtener_mapa_superficial()
        rama_objetivo = next((r for r, subs in mapa.items() if subnodo_elegido in subs), "1_Manuales_tecnicos")
        
        ref_especifica = db.reference(f'Enciclopedia_S2/{rama_objetivo}/{subnodo_elegido}')
        datos_nodo = ref_especifica.get()
        
        contexto_real = f"\n--- DATOS REALES EXTRAÍDOS DE LA ENCICLOPEDIA ---\nRAMA: {rama_objetivo} | SUBNODO: {subnodo_elegido}\n{json.dumps(datos_nodo, indent=2, ensure_ascii=False)}\n"
        coincidencia = True
    else:
        # Búsqueda tradicional en texto libre
        datos_nodo, rama_obj, sub_obj = database.buscar_coincidencia_exacta(mensaje_usuario)
        if datos_nodo:
            contexto_real = f"\n--- DATOS REALES EXTRAÍDOS DE LA ENCICLOPEDIA ---\nRAMA: {rama_obj} | SUBNODO: {sub_obj}\n{json.dumps(datos_nodo, indent=2, ensure_ascii=False)}\n"
            coincidencia = True
        else:
            contexto_real, coincidencia = "", False

    # SI NO HAY COINCIDENCIA, SE DISPARA LA INTERFAZ INTERACTIVA
    if not coincidencia or mensaje_usuario.lower() in ["ayuda", "/ayuda", "menu", "menú"]:
        await menus.activar_encuesta_indice(update, context, mensaje_usuario)
        return

    # FLUJO SEGURO DE IA EN CASCADA
    try:
        respuesta, canal = ai_cascade.procesar_consulta_directa(mensaje_usuario, contexto_real, username)
        await msg_obj.reply_text(f"[{canal}]\n\n{respuesta}")
    except Exception as e:
        print(f"❌ Error crítico en cascada de IA: {e}")
        await msg_obj.reply_text("❌ INTERFERENCIA: Todos los canales de inteligencia están caídos debido a desbordamiento.")

# --- 4. LANZAMIENTO Y CONFIGURACIÓN DEL BOT ---
def main():
    import asyncio
    
    if not ai_cascade.TELEGRAM_TOKEN:
        print("❌ [CRÍTICO] Falta TELEGRAM_TOKEN. Abortando misión.")
        return

    # 1. Forzar e inicializar un loop de eventos asíncronos limpio en el hilo principal
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # 2. Lanzamos el servidor web Flask en su propio hilo secundario para Render
    print("📡 Iniciando servidor web de telemetría...")
    threading.Thread(target=run_flask, daemon=True).start()

    try:
        # 3. Construimos la aplicación de Telegram de forma estándar
        application = Application.builder().token(ai_cascade.TELEGRAM_TOKEN).build()
        
        # CONFIGURACIÓN DEL CONTROLADOR DE CONVERSACIONES NATIVO (FSM)
        manejador_encuesta = ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje)],
            states={
                menus.ESTADO_RAMA: [CallbackQueryHandler(menus.procesar_seleccion_rama)],
                menus.ESTADO_SUBNODO: [CallbackQueryHandler(menus.procesar_seleccion_subnodo)]
            },
            fallbacks=[CommandHandler('cancelar', menus.cancelar_navegacion)],
            allow_reentry=True
        )
        
        # Registramos el manejador maestro
        application.add_handler(manejador_encuesta)
        
        # Manejador de respaldo para comandos directos o eventos aislados
        application.add_handler(MessageHandler(filters.TEXT, procesar_mensaje))

        print("🚀 Oficial S-2 modularizado y blindado en línea. ¡Escuchando transmisiones!")
        
        # 4. run_polling se encarga de bloquear el MainThread de manera asíncrona segura sin romper el loop de eventos
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ Error crítico durante la ejecución del Bot: {e}")

if __name__ == "__main__":
    main()
