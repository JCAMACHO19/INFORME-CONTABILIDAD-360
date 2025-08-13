import os
import pandas as pd
from datetime import datetime
from path_utils import UPLOAD_FOLDER, NEW_FILES_LIST, FECHAS_INICIALES_JSON
import re
from openpyxl import load_workbook
patron_final = re.compile(r'^.+ - \d{2}-\d{2}-\d{4}\.xlsx$', re.IGNORECASE)
if NEW_FILES_LIST.exists():
    with open(NEW_FILES_LIST, 'r', encoding='utf-8') as fh:
        nuevos = {l.strip() for l in fh if l.strip()}
else:
    nuevos = None

# Cargar mapping de fechas iniciales guardadas por rename.py
if FECHAS_INICIALES_JSON.exists():
    try:
        import json
        with open(FECHAS_INICIALES_JSON, 'r', encoding='utf-8') as fh:
            MAP_FECHAS_INICIAL = json.load(fh)
    except Exception:
        MAP_FECHAS_INICIAL = {}
else:
    MAP_FECHAS_INICIAL = {}

for f in UPLOAD_FOLDER.glob('*.xlsx'):
    archivo = f.name
    if archivo.endswith('.xlsx') and ' - ' in archivo:
        ruta_archivo = str(f)
        if patron_final.match(archivo) and (not nuevos or archivo not in nuevos):
            continue
        try:
            # Separar nombre del archivo en partes (Empresa y Fecha Final en nombre)
            nombre_sin_extension = os.path.splitext(archivo)[0]
            partes = nombre_sin_extension.split(" - ")
            empresa = partes[0].strip()
            fecha_final_str = partes[1].strip()
            fecha_final_dt = datetime.strptime(fecha_final_str, "%d-%m-%Y")
            fecha_final_formateada = fecha_final_dt.strftime("%d/%m/%Y")

            # Obtener Fecha Inicial desde mapping persistente
            fecha_inicial_formateada = MAP_FECHAS_INICIAL.get(archivo, '')

            # Leer el archivo Excel completo con pandas
            df = pd.read_excel(ruta_archivo)

            # Añadir columnas Empresa / Fecha (Final) conservando lógica existente
            if "Cuenta" in df.columns:
                tiene_cuenta = df["Cuenta"].notna()
                df["Empresa"] = tiene_cuenta.map(lambda x: empresa if x else "")
                df["Fecha"] = tiene_cuenta.map(lambda x: fecha_final_formateada if x else "")
            else:
                df["Empresa"] = empresa
                df["Fecha"] = fecha_final_formateada

            # Nueva columna: Fecha Inicial (mismo valor para todas las filas)
            df["Fecha Inicial"] = fecha_inicial_formateada

            # Asegurar que 'Fecha Inicial' quede al final
            cols = [c for c in df.columns if c != 'Fecha Inicial'] + ['Fecha Inicial']
            df = df[cols]

            # Guardar archivo actualizado
            df.to_excel(ruta_archivo, index=False)
            print(f"Archivo actualizado: {archivo} (Empresa: {empresa}, Fecha Final: {fecha_final_formateada}, Fecha Inicial: {fecha_inicial_formateada or 'NO_ENCONTRADA'})")

        except Exception as e:
            print(f"Error procesando {archivo}: {e}")
