import requests
from bs4 import BeautifulSoup
import re

def limpiar_texto(texto):
    """Elimina saltos de línea consecutivos y espacios en blanco innecesarios"""
    texto = re.sub(r'\n+', '\n', texto)
    texto = re.sub(r' {2,}', ' ', texto)
    return texto.strip()

def raspar_wiki_batocera(url):
    """
    Se infiltra en la Wiki de Batocera, elimina menús, navegación, 
    publicidad y extrae el contenido técnico junto con las URLs de las imágenes.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        respuesta = requests.get(url, headers=headers, timeout=10)
        if respuesta.status_code != 200:
            print(f"⚠️ [SCRAPER] Error de conexión con la Wiki ({respuesta.status_code})", flush=True)
            return None
            
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        
        # --- QUIRÓFANO: Extirpación de basura (Menús, barras laterales, pies de página, comentarios) ---
        for elemento_basura in soup(["nav", "footer", "aside", "script", "style", ".header", ".footer", "#dw__navbar", "#dw__aside"]):
            elemento_basura.decompose()
            
        # Intentar centrarse en el cuerpo principal del artículo de la Wiki (DokuWiki suele usar id="dokuwiki__content")
        cuerpo_principal = soup.find(id="dokuwiki__content") or soup.find("article") or soup.find("main")
        
        if not cuerpo_principal:
            cuerpo_principal = soup # Si no encuentra contenedor, procesa el cuerpo limpio completo
            
        # 1. Extraer el texto técnico estructurado
        texto_limpio = limpiar_texto(cuerpo_principal.get_text())
        
        # 2. Extraer enlaces de imágenes importantes embebidas en el artículo
        imagenes_encontradas = []
        for img in cuerpo_principal.find_all("img"):
            src = img.get("src")
            if src:
                # Convertir rutas relativas a absolutas si es necesario
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = "https://wiki.batocera.org" + src
                
                # Filtrar iconos pequeños o avatares irrelevantes
                if "wiki:logo" not in src and "favicon" not in src:
                    imagenes_encontradas.append(src)
                    
        return {
            "tipo": "wiki",
            "contenido": texto_limpio,
            "imagenes": imagenes_encontradas[:5] # Limitamos a las 5 primeras imágenes más importantes para no saturar
        }
        
    except Exception as e:
        print(f"🚨 [ERROR CRÍTICO] Fallo en el raspador de la Wiki: {e}", flush=True)
        return None

def extraer_titulo_youtube(url):
    """
    Se conecta brevemente a la URL de YouTube para extraer el título 
    real del videotutorial, evitando descargar el video pesado.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9" # Forzar que intente traer el título en español si está disponible
    }
    try:
        respuesta = requests.get(url, headers=headers, timeout=10)
        if respuesta.status_code != 200:
            return None
            
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        
        # Buscar el título en las metaetiquetas OpenGraph (más fiable en YouTube)
        meta_titulo = soup.find("meta", property="og:title")
        if meta_titulo and meta_titulo.get("content"):
            titulo = meta_titulo.get("content")
        else:
            # Fallback a la etiqueta <title> clásica
            titulo = soup.title.string if soup.title else "Video_Tutorial_YouTube"
            
        # Limpieza básica del título para que sea un nombre de archivo válido
        titulo_valido = titulo.replace(" - YouTube", "")
        titulo_valido = re.sub(r'[\\/*?:"<>|]', "", titulo_valido) # Eliminar caracteres prohibidos en sistemas de archivos
        
        return {
            "tipo": "youtube",
            "titulo": titulo_valido.strip(),
            "url_original": url
        }
    except Exception as e:
        print(f"🚨 [ERROR] No se pudo extraer el título de YouTube: {e}", flush=True)
        return None
