import pandas as pd
from path_utils import UPLOAD_FOLDER, NEW_FILES_LIST
import re
patron_final = re.compile(r'^.+ - \d{2}-\d{2}-\d{4}\.xlsx$', re.IGNORECASE)
if NEW_FILES_LIST.exists():
    with open(NEW_FILES_LIST, 'r', encoding='utf-8') as f:
        nuevos = {l.strip() for l in f if l.strip()}
else:
    nuevos = None

# Columnas a convertir
columnas_a_procesar = [
    "Saldo anterior", "Débitos", "Créditos", "Saldo final",
    "Empresa", "Fecha", "Categoría", "Saldo por Cobrar", "Saldo por Pagar"
]

# Recorre los archivos en la carpeta
for file_path in UPLOAD_FOLDER.glob('*.xlsx'):
    archivo = file_path.name
    if archivo.endswith(".xlsx") and " - " in archivo:
        if patron_final.match(archivo) and (not nuevos or archivo not in nuevos):
            continue
        ruta_archivo = str(file_path)
        try:
            df = pd.read_excel(ruta_archivo, dtype=str)

            # Procesa solo si las columnas existen en el archivo
            for columna in columnas_a_procesar:
                if columna in df.columns:
                    # Reemplaza puntos por comas en las celdas no vacías
                    df[columna] = df[columna].astype(str).str.replace(".", ",", regex=False)

            # Guarda el archivo sobrescribiendo el original
            df.to_excel(ruta_archivo, index=False)
            print(f"Archivo procesado: {archivo}")
        except Exception as e:
            print(f"Error procesando {archivo}: {e}")
