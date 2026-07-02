import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

def limpiar_texto(texto):
    """Elimina saltos de línea consecutivos y espacios en blanco innecesarios."""
    texto = re.sub(r'\n+', '\n', texto)
    texto = re.sub(r' {2,}', ' ', texto)
    return texto.strip()

def raspar_wiki_universal(url):
    """
    Se infiltra en cualquier Wiki de emulación (Batocera, RetroBat, Recalbox, etc.),
    elimina menús, barras de navegación y publicidad, y extrae el contenido técnico 
    junto con las URLs de las imágenes utilizando pasarelas de dominio dinámicas.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        # Extraer la raíz de la URL de forma dinámica (ej: https://wiki.retrobat.org)
        url_analizada = urlparse(url)
        url_raiz = f"{url_analizada.scheme}://{url_analizada.netloc}"

        respuesta = requests.get(url, headers=headers, timeout=10)
        if respuesta.status_code != 200:
            print(f"⚠️ [SCRAPER] Error de conexión con la URL ({respuesta.status_code})", flush=True)
            return None
            
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        
        # --- QUIRÓFANO: Extirpación de basura estándar en páginas Wiki ---
        for elemento_basura in soup(["nav", "footer", "aside", "script", "style", ".header", ".footer", "#dw__navbar", "#dw__aside", ".sidebar", ".menu", ".ads", ".adsense"]):
            elemento_basura.decompose()
            
        # Buscar los contenedores de texto técnico más comunes
        cuerpo_principal = (
            soup.find(id="dokuwiki__content") or 
            soup.find(id="content") or 
            soup.find("article") or 
            soup.find("main")
        )
        
        if not cuerpo_principal:
            cuerpo_principal = soup # Fallback al cuerpo completo si no hay contenedor específico
            
        texto_limpio = limpiar_texto(cuerpo_principal.get_text())
        
        # --- FILTRO MULTIMEDIA: Extracción de imágenes técnicas ---
        imagenes_encontradas = []
        for img in cuerpo_principal.find_all("img"):
            src = img.get("src")
            if src:
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = url_raiz + src # Vinculación dinámica al dominio de origen
                
                # Omitir logos, iconos de interfaz o favicons irrelevantes
                if "logo" not in src.lower() and "favicon" not in src.lower() and "icon" not in src.lower():
                    imagenes_encontradas.append(src)
                    
        return {
            "tipo": "wiki",
            "contenido": texto_limpio,
            "imagenes": imagenes_encontradas[:5] # Límite estratégico de 5 imágenes para evitar saturación
        }
        
    except Exception as e:
        print(f"🚨 [ERROR CRÍTICO] Fallo en el raspador universal: {e}", flush=True)
        return None

def extraer_titulo_youtube(url):
    """
    Se conecta brevemente a los metadatos de YouTube para extraer el título 
    real del videotutorial, evitando descargar el archivo de video pesado.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9" # Forzar metadatos en español si están disponibles
    }
    try:
        respuesta = requests.get(url, headers=headers, timeout=10)
        if respuesta.status_code != 200:
            return None
            
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        
        # Buscar el título en las metaetiquetas OpenGraph de YouTube (es el método más fiable)
        meta_titulo = soup.find("meta", property="og:title")
        if meta_titulo and meta_titulo.get("content"):
            titulo = meta_titulo.get("content")
        else:
            titulo = soup.title.string if soup.title else "Video_Tutorial_YouTube"
            
        # Limpieza del título para transformarlo en un nombre de archivo válido en Drive
        titulo_valido = titulo.replace(" - YouTube", "")
        titulo_valido = re.sub(r'[\\/*?:"<>|]', "", titulo_valido) # Sanitizar caracteres ilegales
        
        return {
            "tipo": "youtube",
            "titulo": titulo_valido.strip(),
            "url_original": url
        }
    except Exception as e:
        print(f"🚨 [ERROR] No se pudo extraer el título de YouTube: {e}", flush=True)
        return None
