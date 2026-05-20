import os
import json
import firebase_admin
from firebase_admin import credentials, db

# Inicialización Firebase
firebase_creds_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
if firebase_creds_json:
    if not firebase_admin._apps:
        cred = credentials.Certificate(json.loads(firebase_creds_json))
        firebase_admin.initialize_app(cred, {'databaseURL': 'https://enciclopedia-oficial-s-2-default-rtdb.europe-west1.firebasedatabase.app/'})

def guardar_manual_estructurado(ruta, titulo, texto, imgs, vids):
    """Escribe el manual directamente en Firebase en la ruta especificada."""
    try:
        ref = db.reference(f'Enciclopedia_S2/{ruta}')
        payload = {
            "titulo": titulo,
            "texto_manual": texto,
            "imagenes": [i.strip() for i in imgs.split(',')] if imgs else [],
            "videos": [v.strip() for v in vids.split(',')] if vids else []
        }
        ref.update(payload)
        return True
    except Exception as e:
        print(f"❌ Error en escritura: {e}")
        return False

def obtener_datos_nodo(ruta):
    """Lee el manual de forma directa desde la ruta especificada."""
    try:
        ref = db.reference(f'Enciclopedia_S2/{ruta}')
        return ref.get()
    except Exception as e:
        print(f"❌ Error en lectura: {e}")
        return None

def obtener_mapa_superficial():
    """
    Explora la raíz 'Enciclopedia_S2' en Firebase para construir dinámicamente
    el mapa de ramas y subnodos necesarios para el menú interactivo.
    """
    try:
        ref = db.reference('Enciclopedia_S2')
        datos_raiz = ref.get()
        
        if not datos_raiz:
            return {}
            
        mapa = {}
        # Iteramos sobre las ramas principales (ej: 1_light_guns, 2_sistemas)
        for rama, contenido in datos_raiz.items():
            if isinstance(contenido, dict):
                # Extraemos los nombres de los subnodos que cuelgan de cada rama
                mapa[rama] = list(contenido.keys())
            else:
                mapa[rama] = []
                
        return mapa
    except Exception as e:
        print(f"❌ Error extrayendo mapa superficial: {e}")
        return {}
