import os
import re
import time
import json
from datetime import datetime
from groq import Groq
from mistralai import Mistral
from openai import OpenAI

# Inicialización de Tokens y Clientes de IA
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

client_groq = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
client_mistral = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None
client_deepseek = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com") if DEEPSEEK_API_KEY else None

MODELO_GROQ = "llama-3.3-70b-versatile"

# Carga de Protocolos de Sistema
try:
    with open("SYSTEM_S2_PROTOCOLS.txt", "r", encoding="utf-8") as f:
        instrucciones_base = f.read()
except FileNotFoundError:
    instrucciones_base = "Eres el Oficial S-2 de GUN4FUN. Analista técnico directo. PRECISIÓN ABSOLUTA."

def ejecutar_ia_con_cascada(prompt_sistema: str, prompt_usuario: str, max_tokens: int = 4096) -> tuple:
    """
    Ejecuta una solicitud de IA siguiendo estrictamente el orden de prioridad:
    Alpha (Groq) -> Bravo (Mistral) -> Charlie (DeepSeek).
    """
    if client_groq:
        try:
            completion = client_groq.chat.completions.create(
                model=MODELO_GROQ,
                messages=[{"role": "system", "content": prompt_sistema}, {"role": "user", "content": prompt_usuario}],
                temperature=0.0,
                max_tokens=max_tokens
            )
            return completion.choices[0].message.content, "Canal Alpha - Groq"
        except Exception as e:
            print(f"⚠️ [IA CASCADE] Fallo en Canal Alpha (Groq): {e}")

    if client_mistral:
        try:
            completion = client_mistral.chat.complete(
                model="mistral-small-latest",
                messages=[{"role": "system", "content": prompt_sistema}, {"role": "user", "content": prompt_usuario}],
                temperature=0.0,
                max_tokens=max_tokens
            )
            return completion.choices[0].message.content, "Canal Bravo - Mistral"
        except Exception as e2:
            print(f"⚠️ [IA CASCADE] Fallo en Canal Bravo (Mistral): {e2}")

    if client_deepseek:
        try:
            completion = client_deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": prompt_sistema}, {"role": "user", "content": prompt_usuario}],
                temperature=0.0,
                max_tokens=max_tokens
            )
            return completion.choices[0].message.content, "Canal Charlie - DeepSeek"
        except Exception as e3:
            print(f"⚠️ [IA CASCADE] Fallo en Canal Charlie (DeepSeek): {e3}")

    raise RuntimeError("Todos los canales de IA fuera de servicio.")

def procesar_consulta_directa(mensaje_usuario: str, contexto_real_json: str, username: str) -> tuple:
    """Prepara y lanza la consulta a la IA con optimización de contexto y guía de usuario."""
    
    username_limpio = str(username) if username else "Operador Autorizado"
    
    # Bypass para navegación directa
    if mensaje_usuario.startswith("nav:"):
        return "Navegación directa detectada. Accediendo a registros estáticos.", "Bypass Interno"

    # Instrucción extra para la IA: invitar a usar los menús
    guia_tactica = "\n\n[DIRECTIVA ADICIONAL: Si la respuesta requiere configuración de hardware o software, recuerda al usuario al finalizar que puede usar el comando /ayuda para acceder a nuestro catálogo interactivo de manuales.]"
    
    contexto_situacional = (
        f"\n--- METADATOS DE LA TRANSMISIÓN ---\n"
        f"FECHA Y HORA ACTUAL: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"IDENTIDAD DEL REMITENTE: {username_limpio}\n"
        f"{guia_tactica}"
    )
    
    texto_contexto_limpio = ""
    if contexto_real_json:
        try:
            inicio_json = contexto_real_json.find('{')
            fin_json = contexto_real_json.rfind('}') + 1
            json_puro = contexto_real_json[inicio_json:fin_json] if inicio_json != -1 else contexto_real_json
            
            datos = json.loads(json_puro.strip())
            if isinstance(datos, dict):
                for clave, valor in datos.items():
                    if clave in ["imagenes_esquema", "videos_tutorial", "ultima_modificacion", "modificado_por"]:
                        continue
                    texto_contexto_limpio += f"📂 SECCIÓN: {clave.upper()}\n{valor}\n\n"
            else:
                texto_contexto_limpio = str(datos)
        except Exception:
            texto_contexto_limpio = contexto_real_json[:4000]

    prompt_sistema = f"{instrucciones_base}\n{contexto_situacional}"
    
    prompt_usuario_estructurado = (
        f"=== MANUALES TÉCNICOS EXTRAÍDOS DE LA BASE DE DATOS S-2 ===\n"
        f"{texto_contexto_limpio}\n"
        f"===========================================================\n\n"
        f"INSTRUCCIÓN DEL OPERADOR: {mensaje_usuario}"
    )
    
    return ejecutar_ia_con_cascada(prompt_sistema, prompt_usuario_estructurado, max_tokens=2048)
