import os
import io
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

# Permisos requeridos para operar en Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']

def obtener_servicio_drive():
    """Establece la conexión autenticada con la API de Google Drive."""
    creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    try:
        if creds_json:
            # Configuración para producción en Render (Variable de entorno)
            info = json.loads(creds_json)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        elif os.path.exists('credentials.json'):
            # Configuración para pruebas en entorno local
            creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        else:
            print("🚨 [DATABASE] No se detectaron credenciales autorizadas para Google Drive.", flush=True)
            return None
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"🚨 [DATABASE] Error crítico en la pasarela de autenticación de Drive: {e}", flush=True)
        return None

def _obtener_o_crear_subcarpeta_interna(service, nombre_carpeta, id_padre):
    """Módulo interno: Busca una carpeta por nombre dentro de un directorio padre. Si no existe, la construye."""
    query = f"name = '{nombre_carpeta}' and '{id_padre}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    try:
        resultados = service.files().list(q=query, fields="files(id)").execute()
        archivos = resultados.get('files', [])
        
        if archivos:
            return archivos[0]['id'] # Retorna la carpeta existente
            
        # Protocolo de creación si el sector no existe
        metadata = {
            'name': nombre_carpeta,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [id_padre]
        }
        subcarpeta = service.files().create(body=metadata, fields='id').execute()
        return subcarpeta.get('id')
    except Exception as e:
        print(f"🚨 [DATABASE] Error al resolver subcarpeta '{nombre_carpeta}': {e}", flush=True)
        return id_padre

def crear_documento_en_ruta(carpeta_raiz_id, ruta_sectores, nombre_archivo, contenido):
    """Crea o actualiza un archivo de texto plano (.txt) en una ruta multinivel dinámica."""
    service = obtener_servicio_drive()
    if not service:
        return False
    try:
        # Resolver el cuartel de destino final analizando la ruta por niveles
        if not ruta_sectores or ruta_sectores.strip() in ['raiz', 'root', '/']:
            id_destino_final = carpeta_raiz_id
        else:
            partes_ruta = [p.strip() for p in ruta_sectores.split('/') if p.strip()]
            id_actual = carpeta_raiz_id
            for parte in partes_ruta:
                id_actual = _obtener_o_crear_subcarpeta_interna(service, parte, id_actual)
            id_destino_final = id_actual

        if not nombre_archivo.endswith('.txt'):
            nombre_archivo += '.txt'

        metadata = {
            'name': nombre_archivo,
            'parents': [id_destino_final]
        }
        
        # Conversión del texto a flujo de transmisión en memoria RAM
        flujo_memoria = io.BytesIO(contenido.encode('utf-8'))
        media = MediaIoBaseUpload(flujo_memoria, mimetype='text/plain', resumable=True)
        
        file = service.files().create(body=metadata, media_body=media, fields='id').execute()
        print(f"📝 [DATABASE] Archivo de texto creado con éxito. ID: {file.get('id')}", flush=True)
        return True
    except Exception as e:
        print(f"🚨 [DATABASE] Error al desplegar documento de texto: {e}", flush=True)
        return False

def subir_archivo_binario_en_ruta(carpeta_raiz_id, ruta_sectores, nombre_archivo, flujo_bytes, mime_type):
    """
    [PROTOCOLO MULTIMEDIA]
    Recibe un flujo de bytes en memoria de archivos físicos (Fotos, PDFs, Esquemas),
    crea la ruta de carpetas necesaria y sube el archivo manteniendo su formato original.
    """
    service = obtener_servicio_drive()
    if not service:
        return False
    try:
        if not ruta_sectores or ruta_sectores.strip() in ['raiz', 'root', '/']:
            id_destino_final = carpeta_raiz_id
        else:
            partes_ruta = [p.strip() for p in ruta_sectores.split('/') if p.strip()]
            id_actual = carpeta_raiz_id
            for parte in partes_ruta:
                id_actual = _obtener_o_crear_subcarpeta_interna(service, parte, id_actual)
            id_destino_final = id_actual

        metadata = {
            'name': nombre_archivo,
            'parents': [id_destino_final]
        }
        
        media = MediaIoBaseUpload(flujo_bytes, mimetype=mime_type, resumable=True)
        file = service.files().create(body=metadata, media_body=media, fields='id').execute()
        
        print(f"📸 [DATABASE] Archivo multimedia indexado con éxito. ID: {file.get('id')}", flush=True)
        return True
    except Exception as e:
        print(f"🚨 [DATABASE] Error al subir archivo binario a Drive: {e}", flush=True)
        return False

def crear_acceso_youtube_en_ruta(carpeta_raiz_id, ruta_sectores, titulo_video, url_video):
    """
    [PROTOCOLO DE ACCESO ULTRA-LIGERO]
    Crea un reporte de texto individual con los datos y link del videotutorial de YouTube,
    ahorrando espacio de almacenamiento en la unidad (Consumo: 0%).
    """
    contenido_acceso = (
        f"==================================================\n"
        f" VIDEOTUTORIAL DE CONFIGURACIÓN INDEXADO\n"
        f"==================================================\n\n"
        f"TÍTULO DEL VIDEO: {titulo_video}\n"
        f"ENLACE DIRECTO:   {url_video}\n\n"
        f"--------------------------------------------------\n"
        f"Optimización de almacenamiento: Enlace web archivado."
    )
    return crear_documento_en_ruta(carpeta_raiz_id, ruta_sectores, titulo_video, contenido_acceso)
