import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# Ruta segura en el sistema de archivos de Render (Secret Files)
CREDENTIALS_PATH = "/etc/secrets/google_creds.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

def obtener_servicio_drive():
    """Inicializa de forma segura el cliente de la API de Google Drive"""
    if not os.path.exists(CREDENTIALS_PATH):
        print("🚨 [CRÍTICO] Archivo de credenciales de Google Drive no encontrado en Render.")
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH, scopes=SCOPES
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"🚨 [ERROR] Fallo al autenticar con Google Cloud: {e}")
        return None

def listar_contenido_carpeta(folder_id):
    """
    Lista subcarpetas y archivos de una carpeta específica de Drive.
    Útil para construir los menús dinámicos de botones en Telegram.
    """
    service = obtener_servicio_drive()
    if not service:
        return []
        
    query = f"'{folder_id}' in parents and trashed = false"
    try:
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType)",
            orderBy="name"
        ).execute()
        return results.get('files', [])
    except Exception as e:
        print(f"⚠️ [ERROR] No se pudo listar la carpeta {folder_id}: {e}")
        return []

def buscar_subcarpeta_por_nombre(parent_id, nombre_subcarpeta):
    """
    Rastrea el Drive para encontrar el ID de una subcarpeta específica
    (ej. 'gun4ir' o 'batocera') dentro de la jerarquía del servidor.
    """
    service = obtener_servicio_drive()
    if not service:
        return None
        
    query = (f"mimeType = 'application/vnd.google-apps.folder' and "
             f"name contains '{nombre_subcarpeta}' and "
             f"trashed = false")
    try:
        results = service.files().list(q=query, fields="files(id, name, parents)").execute()
        carpetas = results.get('files', [])
        
        for carpeta in carpetas:
            # Retorna la primera coincidencia válida del árbol
            return carpeta['id']
            
        print(f"⚠️ [SISTEMA] Sector '{nombre_subcarpeta}' no encontrado en el almacenamiento.")
        return None
    except Exception as e:
        print(f"🚨 [ERROR] Fallo crítico al rastrear subcarpetas: {e}")
        return None

def leer_texto_de_documento(file_id, mime_type):
    """
    Extrae el contenido de texto para alimentar la cascada de IA.
    Soporta archivos .txt nativos y Documentos de Google (Google Docs).
    """
    service = obtener_servicio_drive()
    if not service:
        return ""
        
    try:
        # Si es un Google Doc nativo, lo exportamos sobre la marcha a texto plano
        if mime_type == 'application/vnd.google-apps.document':
            request = service.files().export_media(fileId=file_id, mimeType='text/plain')
        else:
            # Si es un archivo de texto estándar (.txt)
            request = service.files().get_media(fileId=file_id)
            
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
            
        return fh.getvalue().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"⚠️ [ERROR] Imposible leer el contenido del archivo {file_id}: {e}")
        return ""

def crear_documento_autonomo(folder_id, titulo, contenido):
    """
    [PROTOCOLO DE AUTO-APRENDIZAJE]
    Crea un nuevo archivo de texto en la carpeta de Drive especificada.
    Usa flujos de bytes en memoria (io.BytesIO) para blindar la estabilidad en Render.
    """
    service = obtener_servicio_drive()
    if not service:
        return False
        
    metadata = {
        'name': f"{titulo}.txt",
        'parents': [folder_id]
    }
    
    # Conversión segura a flujo de bytes para evitar fallos de transmisión
    bytes_contenido = io.BytesIO(contenido.encode('utf-8'))
    media = MediaIoBaseUpload(bytes_contenido, mimeType='text/plain', resumable=True)
    
    try:
        file = service.files().create(
            body=metadata,
            media_body=media,
            fields='id'
        ).execute()
        print(f"🗄️ [SISTEMA] Nuevo conocimiento archivado con éxito en Drive. ID: {file.get('id')}")
        return True
    except Exception as e:
        print(f"🚨 [ERROR] El protocolo de auto-aprendizaje falló al escribir en Drive: {e}")
        return False