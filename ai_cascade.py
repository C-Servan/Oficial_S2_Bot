import os
import requests
from groq import Groq

def cargar_protocolos_sistema(contexto_drive=""):
    """Carga el archivo de directivas de rango e inyecta el contexto de Google Drive"""
    try:
        with open("PROTOCOLOS_SISTEMA_S2.txt", "r", encoding="utf-8") as f:
            prompt_maestro = f.read()
        return prompt_maestro.replace("{CONTEXTO_DRIVE}", contexto_drive)
    except FileNotFoundError:
        # Salvaguarda crítica para evitar que el bot muera si el archivo se desubica
        return f"Eres el Oficial S-2, analista técnico en Lightguns. Manuales disponibles: {contexto_drive}"

def intentar_gemini(system_prompt, user_message):
    """Línea de Defensa 1: Gemini 1.5 Flash (Google AI Studio)"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise Exception("API Key de Gemini no configurada en el entorno.")
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # Formato oficial y óptimo para que Gemini obedezca las instrucciones del sistema
    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [{
            "parts": [{"text": user_message}]
        }]
    }
    
    response = requests.post(url, json=payload, timeout=6)
    if response.status_code == 200:
        try:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            raise Exception("Respuesta de Gemini con estructura inesperada.")
    raise Exception(f"Gemini fuera de línea. Estado HTTP: {response.status_code}")

def intentar_groq(system_prompt, user_message):
    """Línea de Defensa 2: Groq (Llama 3 70B)"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise Exception("API Key de Groq no configurada.")
        
    # Inicialización segura dentro del flujo de ejecución (lazy loading)
    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        timeout=6
    )
    return completion.choices[0].message.content

def intentar_deepseek_openrouter(system_prompt, user_message):
    """Línea de Defensa 3: DeepSeek Chat vía OpenRouter (Económico/Gratuito)"""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("API Key de OpenRouter no configurada.")
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://render.com", 
        "X-Title": "Oficial S2 Bot"
    }
    payload = {
        "model": "deepseek/deepseek-chat:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }
    response = requests.post(url, json=payload, headers=headers, timeout=6)
    if response.status_code == 200:
        try:
            return response.json()['choices'][0]['message']['content']
        except (KeyError, IndexError):
            raise Exception("Respuesta de OpenRouter con estructura inesperada.")
    raise Exception(f"DeepSeek/OpenRouter fuera de línea. Estado HTTP: {response.status_code}")

def procesar_consulta_cascada(rango, mensaje_usuario, contexto_drive="No hay manuales específicos indexados para esta consulta."):
    """
    Función maestra y blindada de la cascada técnica.
    Formatea los rangos e itera de forma inteligente entre los proveedores de IA.
    """
    system_prompt = cargar_protocolos_sistema(contexto_drive)
    mensaje_formateado = f"[{rango.upper()} EN LÍNEA] Consulta técnica: {mensaje_usuario}"
    
    # --- EJECUCIÓN DEL PROTOCOLO DE CASCADA ---
    
    # TIER 1: Gemini (Cerebro masivo para devorar manuales de Drive)
    try:
       return intentar_gemini(system_prompt, mensaje_formateado)
    except Exception as e:
        print(f"⚠️ [FALLO TIER 1] {e} -> Desplegando contramedidas: Activando Tier 2...")
        
        # TIER 2: Groq (Velocidad de respuesta pura si Gemini se satura)
        try:
            return intentar_groq(system_prompt, mensaje_formateado)
        except Exception as e:
            print(f"⚠️ [FALLO TIER 2] {e} -> Desplegando última línea de defensa: Activando Tier 3...")
            
            # TIER 3: DeepSeek vía OpenRouter (Ingeniería de respaldo lógica)
            try:
                return intentar_deepseek_openrouter(system_prompt, mensaje_formateado)
            except Exception as e:
                # Blindaje absoluto ante un colapso general de internet o APIs
                print(f"🚨 [CRÍTICO] Colapso total de la cascada de IA: {e}")
                return (f"⚠️ [COMUNICACIÓN INTERRUMPIDA] Oficial S-2 informa: Pérdida total de enlace "
                        f"con la red de análisis cognitivo. Sistemas de contingencia activos.\n\n"
                        f"{rango.capitalize()}, recurra temporalmente a las Wikis oficiales del sistema.")