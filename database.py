# database.py
import os
import json
import re
import firebase_admin
from firebase_admin import credentials, db

# Inicialización segura y blindada de Firebase
firebase_creds_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')

if firebase_creds_json:
    try:
        if not firebase_admin._apps:
            creds_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://enciclopedia-oficial-s-2-default-rtdb.europe-west1.firebasedatabase.app/'
            })
            print("✅ [MÓDULO BD] Conexión blindada a la Enciclopedia S-2 establecida.")
        else:
            print("✅ [MÓDULO BD] Conexión Firebase ya activa en subproceso.")
    except Exception as e:
        print(f"❌ [MÓDULO BD] Error crítico al inicializar Firebase: {e}")
else:
    print("⚠️ [MÓDULO BD] No se detectó la variable FIREBASE_SERVICE_ACCOUNT.")

def obtener_mapa_superficial() -> dict:
    """
    Descarga SOLO la estructura de claves (Ramas y Subnodos) usando shallow=True.
    Evita por completo el desbordamiento por descarga de datos masivos.
    Retorna un diccionario: { "Rama_1": ["subnodo1", "subnodo2"], "Rama_2": [] }
    """
    try:
        ref_raiz = db.reference('Enciclopedia_S2')
        ramas_claves = ref_raiz.get(shallow=True)
        
        if not ramas_claves:
            return {}
        
        mapa_conocimiento = {}
        for rama in ramas_claves.keys():
            ref_subnodos = db.reference(f'Enciclopedia_S2/{rama}')
            subnodos_claves = ref_subnodos.get(shallow=True)
            
            if subnodos_claves and isinstance(subnodos_claves, dict):
                mapa_conocimiento[rama] = sorted(list(subnodos_claves.keys()))
            else:
                mapa_conocimiento[rama] = []
                
        return mapa_conocimiento
    except Exception as e:
        print(f"❌ Error al obtener mapa superficial: {e}")
        return {}

def buscar_coincidencia_exacta(mensaje_usuario: str) -> tuple:
    """
    Analiza si el texto del usuario coincide directamente con algún subnodo.
    Retorna (datos_subnodo, nombre_rama, nombre_subnodo) si coincide.
    Retorna (None, None, None) si no hay match.
    """
    try:
        mapa = obtener_mapa_superficial()
        # Normalización total: quitamos espacios, guiones y pasamos a minúsculas
        mensaje_limpio = re.sub(r'[\s_\-]', '', mensaje_usuario.strip().lower())
        
        for rama, subnodos in mapa.items():
            for subnodo in subnodos:
                subnodo_limpio = re.sub(r'[\s_\-]', '', subnodo.lower())
                if subnodo_limpio == mensaje_limpio:
                    ref_especifica = db.reference(f'Enciclopedia_S2/{rama}/{subnodo}')
                    datos = ref_especifica.get()
                    return datos, rama, subnodo
                    
        return None, None, None
    except Exception as e:
        print(f"❌ Error en búsqueda de coincidencia exacta: {e}")
        return None, None, None
