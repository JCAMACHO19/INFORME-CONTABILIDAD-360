import os
import pandas as pd
from datetime import datetime
from path_utils import UPLOAD_FOLDER, NEW_FILES_LIST
import re
patron_final = re.compile(r'^.+ - \d{2}-\d{2}-\d{4}\.xlsx$', re.IGNORECASE)
if NEW_FILES_LIST.exists():
    with open(NEW_FILES_LIST, 'r', encoding='utf-8') as fh:
        nuevos = {l.strip() for l in fh if l.strip()}
else:
    nuevos = None

for f in UPLOAD_FOLDER.glob('*.xlsx'):
    archivo = f.name
    if archivo.endswith('.xlsx') and ' - ' in archivo:
        ruta_archivo = str(f)
        if patron_final.match(archivo) and (not nuevos or archivo not in nuevos):
            continue
        try:
            # Separar nombre del archivo en partes
            nombre_sin_extension = os.path.splitext(archivo)[0]
            partes = nombre_sin_extension.split(" - ")

            empresa = partes[0].strip()
            fecha_str = partes[1].strip()

            # Convertir la fecha a datetime (formato: dd-mm-yyyy)
            fecha_dt = datetime.strptime(fecha_str, "%d-%m-%Y")
            fecha_formateada = fecha_dt.strftime("%d/%m/%Y")  # formato deseado: aaaa/mm/dd

            # Leer el archivo Excel
            df = pd.read_excel(ruta_archivo)

            # Determinar qué filas tienen datos (por ejemplo, si la columna "Cuenta" no está vacía)
            if "Cuenta" in df.columns:
                df["Empresa"] = df["Cuenta"].notna().map(lambda x: empresa if x else "")
                df["Fecha"] = df["Cuenta"].notna().map(lambda x: fecha_formateada if x else "")
            else:
                df["Empresa"] = empresa
                df["Fecha"] = fecha_formateada

            # Guardar archivo actualizado
            df.to_excel(ruta_archivo, index=False)
            print(f"Archivo actualizado: {archivo} (Empresa: {empresa}, Fecha: {fecha_formateada})")

        except Exception as e:
            print(f"Error procesando {archivo}: {e}")
