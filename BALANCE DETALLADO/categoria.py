import pandas as pd
from path_utils import UPLOAD_FOLDER, NEW_FILES_LIST
import re
patron_final = re.compile(r'^.+ - \d{2}-\d{2}-\d{4}\.xlsx$', re.IGNORECASE)
if NEW_FILES_LIST.exists():
    with open(NEW_FILES_LIST, 'r', encoding='utf-8') as f:
        nuevos = {l.strip() for l in f if l.strip()}
else:
    nuevos = None

# Categorías según los primeros 4 dígitos de la cuenta contable
cobrar = {"1370", "1895"}
pagar = {"2399", "2815", "2360", "3710"}

for file_path in UPLOAD_FOLDER.glob('*.xlsx'):
    archivo = file_path.name
    ruta_archivo = str(file_path)
    if patron_final.match(archivo) and (not nuevos or archivo not in nuevos):
        continue
    try:
            df = pd.read_excel(ruta_archivo)

            if {"Cuenta contable", "Saldo final"}.issubset(df.columns):
                # Obtener los primeros 4 caracteres como string
                df["Prefijo Cuenta"] = df["Cuenta contable"].astype(str).str[:4]

                # Clasificar en Categoría
                def clasificar(prefijo):
                    if prefijo in cobrar:
                        return "Saldo por Cobrar"
                    elif prefijo in pagar:
                        return "Saldo por Pagar"
                    else:
                        return ""

                df["Categoría"] = df["Prefijo Cuenta"].apply(clasificar)

                # Crear columnas adicionales en blanco
                df["Saldo por Cobrar"] = 0
                df["Saldo por Pagar"] = 0

                # Asignar los valores de "Saldo final" a las columnas nuevas según corresponda
                df.loc[df["Categoría"] == "Saldo por Cobrar", "Saldo por Cobrar"] = df["Saldo final"]
                df.loc[df["Categoría"] == "Saldo por Pagar", "Saldo por Pagar"] = df["Saldo final"]

                # Eliminar la columna auxiliar
                df.drop(columns=["Prefijo Cuenta"], inplace=True)

                # Guardar el archivo sobrescribiendo el original
                df.to_excel(ruta_archivo, index=False)
                print(f"Archivo actualizado con categorías y columnas de saldo: {archivo}")
            else:
                print(f"Columnas necesarias no encontradas en: {archivo}")

    except Exception as e:
        print(f"Error procesando {archivo}: {e}")

