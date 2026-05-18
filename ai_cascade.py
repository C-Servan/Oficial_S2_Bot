# ai_cascade.py
import os
import re
import time
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
    Retorna una tupla: (texto_respuesta, canal_utilizado)
    """
    # --- PLAN A: Groq (Canal Alpha) ---
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

    # --- PLAN B: Mistral (Canal Bravo) ---
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

    # --- PLAN C: DeepSeek (Canal Charlie) ---
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

    # Si todo falla, disparamos una excepción controlada que capturará el módulo principal
    raise RuntimeError("Todos los canales de procesamiento de IA se encuentran fuera de servicio o saturados.")

def procesar_consulta_directa(mensaje_usuario: str, contexto_real_json: str, username: str) -> tuple:
    """
    Prepara los metadatos y el contexto estructurado para lanzarlo a la cascada de IA.
    """
    contexto_situacional = (
        f"\n--- METADATOS DE LA TRANSMISIÓN ---\n"
        f"FECHA Y HORA ACTUAL: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"IDENTIDAD DEL REMITENTE: {username}\n"
        f"------------------------------------\n"
    )
    
    prompt_sistema = f"{instrucciones_base}\n{contexto_situacional}\n{contexto_real_json}"
    
    # Limitamos a 2048 tokens la respuesta para evitar cortes en chats estándar
    return ejecutar_ia_con_cascada(prompt_sistema, mensaje_usuario, max_tokens=2048)
