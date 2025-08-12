import pandas as pd
from path_utils import UPLOAD_FOLDER, NEW_FILES_LIST
import re
patron_final = re.compile(r'^.+ - \d{2}-\d{2}-\d{4}\.xlsx$', re.IGNORECASE)
if NEW_FILES_LIST.exists():
    with open(NEW_FILES_LIST, 'r', encoding='utf-8') as f:
        nuevos = {l.strip() for l in f if l.strip()}
else:
    nuevos = None

for file_path in UPLOAD_FOLDER.glob('*.xlsx'):
    archivo = file_path.name
    if archivo.endswith(".xlsx") and " - " in archivo:
        if patron_final.match(archivo) and (not nuevos or archivo not in nuevos):
            continue
        ruta_archivo = str(file_path)
        try:
            # Cargar el archivo Excel
            df = pd.read_excel(ruta_archivo)

            # Verificar si la columna existe
            if "No. Identificación" in df.columns:
                # Filtrar solo las filas donde la columna "No. Identificación" no esté vacía
                df_filtrado = df[df["No. Identificación"].notna()]

                # Guardar el archivo sobrescribiendo el original
                df_filtrado.to_excel(ruta_archivo, index=False)
                print(f"Archivo procesado: {archivo}")
            else:
                print(f"Columna 'No. Identificación' no encontrada en {archivo}")

        except Exception as e:
            print(f"Error procesando {archivo}: {e}")
