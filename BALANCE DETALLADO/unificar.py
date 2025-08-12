import pandas as pd
from path_utils import UPLOAD_FOLDER, NEW_FILES_LIST
import re
patron_final = re.compile(r'^.+ - \d{2}-\d{2}-\d{4}\.xlsx$', re.IGNORECASE)
if NEW_FILES_LIST.exists():
    with open(NEW_FILES_LIST, 'r', encoding='utf-8') as f:
        nuevos = {l.strip() for l in f if l.strip()}
else:
    nuevos = None

# Diccionario para almacenar el primer nombre de cada No. Identificación
identificacion_dict = {}

# ▶️ PRIMER PASO: Leer todos los archivos y construir el diccionario
for file_path in UPLOAD_FOLDER.glob('*.xlsx'):
    archivo = file_path.name
    if archivo.endswith(".xlsx") and " - " in archivo:
        ruta_archivo = str(file_path)
        if patron_final.match(archivo) and (not nuevos or archivo not in nuevos):
            continue
        try:
            df = pd.read_excel(ruta_archivo, dtype=str)

            if "No. Identificación" in df.columns and "Tercero" in df.columns:
                for idx, row in df.iterrows():
                    identificacion = row["No. Identificación"]
                    tercero = row["Tercero"]

                    # Guardar el primer "Tercero" encontrado para cada "No. Identificación"
                    if pd.notna(identificacion) and identificacion not in identificacion_dict:
                        identificacion_dict[identificacion] = tercero
        except Exception as e:
            print(f"Error leyendo el archivo {archivo}: {e}")

# ▶️ SEGUNDO PASO: Reescribir los archivos con los nombres estandarizados
for file_path in UPLOAD_FOLDER.glob('*.xlsx'):
    archivo = file_path.name
    if archivo.endswith(".xlsx") and " - " in archivo:
        ruta_archivo = str(file_path)
        if patron_final.match(archivo) and (not nuevos or archivo not in nuevos):
            continue
        try:
            df = pd.read_excel(ruta_archivo, dtype=str)

            if "No. Identificación" in df.columns and "Tercero" in df.columns:
                df["Tercero"] = df["No. Identificación"].map(identificacion_dict)

                # Guardar el archivo sobrescribiendo el original
                df.to_excel(ruta_archivo, index=False)
                print(f"Archivo actualizado: {archivo}")
            else:
                print(f"Columnas necesarias no encontradas en {archivo}")
        except Exception as e:
            print(f"Error actualizando el archivo {archivo}: {e}")
