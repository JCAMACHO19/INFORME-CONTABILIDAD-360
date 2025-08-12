from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "SALDO BANCOS"
NEW_FILES_LIST = UPLOAD_FOLDER / "_archivos_recien_renombrados.txt"

if not UPLOAD_FOLDER.exists():
    raise FileNotFoundError(f"No se encontró la carpeta SALDO BANCOS en: {UPLOAD_FOLDER}")
