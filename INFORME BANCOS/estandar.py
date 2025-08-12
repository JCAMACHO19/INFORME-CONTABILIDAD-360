import pandas as pd
from path_utils import UPLOAD_FOLDER, NEW_FILES_LIST
import re
patron_final = re.compile(r'^.+ - \d{2}-\d{2}-\d{4}\.xlsx$', re.IGNORECASE)
if NEW_FILES_LIST.exists():
    with open(NEW_FILES_LIST, 'r', encoding='utf-8') as fh:
        nuevos = {l.strip() for l in fh if l.strip()}
else:
    nuevos = None

# Columnas requeridas
columnas_requeridas = [
    "Cuenta",
    " Saldo Inicial",
    "ABR - Notas contables",
    "Ajustes y Reclasificaciones",
    "CE CHEQUES",
    "CE TRANSF",
    "Comprobante de Egreso",
    "Comprobante de Ingreso",
    "Cuenta Por Pagar",
    "Documento de Cartera Reversado",
    "Gastos Bancarios",
    "GASTOS BANCARIOS AUTOMATICOS",
    "Legalizacion de anticipos",
    "Prestamos",
    "Traslado de Fondos",
    "Saldo Libros",
    "Cheques x Ent",
    "Saldo Bancos"
]

# Recorre los archivos en la carpeta
for f in UPLOAD_FOLDER.glob('*.xlsx'):
    archivo = f.name
    if archivo.endswith('.xlsx'):
        ruta_archivo = str(f)
        if patron_final.match(archivo) and (not nuevos or archivo not in nuevos):
            continue
        try:
            df = pd.read_excel(ruta_archivo)

            # Verificar qué columnas faltan
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]

            # Agregar columnas faltantes con valores vacíos
            for col in columnas_faltantes:
                df[col] = ""

            # Eliminar filas que contienen "TOTALES" o "TOTAL GENERAL" en la columna 'Cuenta'
            df = df[~df["Cuenta"].astype(str).str.upper().str.contains("TOTALES|TOTAL GENERAL", na=False)]

            # Eliminar columnas adicionales
            df = df[[col for col in columnas_requeridas]]

            # Guardar el archivo actualizado
            df.to_excel(ruta_archivo, index=False)
            print(f"Archivo actualizado: {archivo} (faltaban {len(columnas_faltantes)} columnas, eliminadas extra y filas con totales)")
        except Exception as e:
            print(f"Error procesando {archivo}: {e}")
