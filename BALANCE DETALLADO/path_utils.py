from pathlib import Path

# Directorio base (carpeta donde están los scripts)
BASE_DIR = Path(__file__).resolve().parent

# Carpeta DOCUMENTOS (siempre dentro de la carpeta de los scripts)
UPLOAD_FOLDER = BASE_DIR / "DOCUMENTOS"

# Archivo que guarda los nombres de archivos recién renombrados en la última ejecución
NEW_FILES_LIST = UPLOAD_FOLDER / "_archivos_recien_renombrados.txt"

if not UPLOAD_FOLDER.exists():
    raise FileNotFoundError(f"No se encontró la carpeta DOCUMENTOS en: {UPLOAD_FOLDER}")
