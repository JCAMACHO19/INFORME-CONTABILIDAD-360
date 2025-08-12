import pandas as pd
import re
from path_utils import UPLOAD_FOLDER, NEW_FILES_LIST
import re
patron_final = re.compile(r'^.+ - \d{2}-\d{2}-\d{4}\.xlsx$', re.IGNORECASE)
if NEW_FILES_LIST.exists():
    with open(NEW_FILES_LIST, 'r', encoding='utf-8') as fh:
        nuevos = {l.strip() for l in fh if l.strip()}
else:
    nuevos = None

# Función para extraer banco y tipo de cuenta
def extraer_banco_y_tipo(cuenta):
    if isinstance(cuenta, str):
        match = re.search(r'(.+?)\s+(COR|AHO)\b', cuenta)
        if match:
            banco = match.group(1).strip()
            tipo = match.group(2)
            return banco, tipo
    return "", ""

# Procesar cada archivo en la carpeta
for f in UPLOAD_FOLDER.glob('*.xlsx'):
    archivo = f.name
    if archivo.endswith('.xlsx'):
        ruta_archivo = str(f)
        if patron_final.match(archivo) and (not nuevos or archivo not in nuevos):
            continue
        try:
            df = pd.read_excel(ruta_archivo)

            if "Cuenta" in df.columns:
                # Aplicar la función a la columna Cuenta
                df[["Banco", "Tipo de Cuenta"]] = df["Cuenta"].apply(
                    lambda x: pd.Series(extraer_banco_y_tipo(x))
                )

                # Guardar el archivo actualizado
                df.to_excel(ruta_archivo, index=False)
                print(f"Archivo actualizado: {archivo}")
            else:
                print(f"Columna 'Cuenta' no encontrada en: {archivo}")

        except Exception as e:
            print(f"Error procesando {archivo}: {e}")
