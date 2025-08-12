import pandas as pd
from path_utils import UPLOAD_FOLDER, NEW_FILES_LIST
import re
patron_final = re.compile(r'^.+ - \d{2}-\d{2}-\d{4}\.xlsx$', re.IGNORECASE)
if NEW_FILES_LIST.exists():
    with open(NEW_FILES_LIST, 'r', encoding='utf-8') as f:
        nuevos = {l.strip() for l in f if l.strip()}
else:
    nuevos = None

# Diccionario con los valores a reemplazar
reemplazos = {
    "AMERICAN": ("806010696", "AMERICAN LIGHTING SAS"),
    "CONSORCIO AMERICAN": ("900779363", "CONSORCIO AMERICAN LIGHTING"),
    "AGM": ("800186313", "AGM DESARROLLOS SAS"),
    "CONSORCIO SJC": ("901034269", "CONSORCIO ALUMBRADO PUBLICO SJC"),
}

# Crear diccionario auxiliar de validación por identificación
validacion_identificacion = {v[0]: v[1] for v in reemplazos.values()}

for file_path in UPLOAD_FOLDER.glob('*.xlsx'):
    archivo = file_path.name
    ruta_archivo = str(file_path)
    if patron_final.match(archivo) and (not nuevos or archivo not in nuevos):
        continue
    try:
            df = pd.read_excel(ruta_archivo)

            if {"Cuenta contable nombre", "No. Identificación", "Tercero"}.issubset(df.columns):
                # Primera etapa: reemplazo basado en coincidencias
                for clave, (identificacion, tercero) in reemplazos.items():
                    filtro = df["Cuenta contable nombre"].str.contains("OTRAS CXP", na=False) & \
                             df["Cuenta contable nombre"].str.contains(clave, na=False)

                    df.loc[filtro, "No. Identificación"] = identificacion
                    df.loc[filtro, "Tercero"] = tercero

                # Segunda etapa: validación global por No. Identificación
                df["No. Identificación"] = df["No. Identificación"].astype(str)
                for nit, tercero_correcto in validacion_identificacion.items():
                    df.loc[df["No. Identificación"] == nit, "Tercero"] = tercero_correcto

                # Guardar el archivo sobrescribiendo el original
                df.to_excel(ruta_archivo, index=False)
                print(f"Archivo actualizado con validación de terceros: {archivo}")
            else:
                print(f"Columnas necesarias no encontradas en: {archivo}")

    except Exception as e:
        print(f"Error procesando {archivo}: {e}")