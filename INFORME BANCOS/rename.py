import re
from openpyxl import load_workbook
from path_utils import UPLOAD_FOLDER, NEW_FILES_LIST

def main():
    patron_final = re.compile(r'^.+ - \d{2}-\d{2}-\d{4}\.xlsx$', re.IGNORECASE)
    nuevos = []
    for f in UPLOAD_FOLDER.glob('*.xlsx'):
        archivo = f.name
        if patron_final.match(archivo):
            print(f"↪️ Ya con nombre final, se omite: {archivo}")
            continue
        ruta_archivo = str(f)
        try:
            wb = load_workbook(ruta_archivo, data_only=True)
            ws = wb.active
            fila_nombre = str(ws["A2"].value)
            if fila_nombre and "NIT" in fila_nombre:
                nombre_parte1 = fila_nombre.split("NIT")[0].strip()
            else:
                nombre_parte1 = "SIN_NOMBRE"
            fila_fecha = str(ws["A4"].value)
            match_fecha = re.search(r"Fecha Final:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", fila_fecha)
            fecha_final = match_fecha.group(1) if match_fecha else "FECHA_NO_ENCONTRADA"
            fecha_final_safe = fecha_final.replace('/', '-') if fecha_final != 'FECHA_NO_ENCONTRADA' else ''
            nuevo_nombre = f"{nombre_parte1.strip()} - {fecha_final_safe}.xlsx" if fecha_final_safe else f"{nombre_parte1.strip()}.xlsx"
            nueva_ruta = f.with_name(nuevo_nombre)
            if not nueva_ruta.exists():
                f.rename(nueva_ruta)
                nuevos.append(nuevo_nombre)
                print(f"Renombrado: '{archivo}' → '{nuevo_nombre}'")
            else:
                print(f"Archivo ya existe: '{nuevo_nombre}' → se omite.")
        except Exception as e:
            print(f"Error procesando '{archivo}': {e}")
    # Guardar lista de nuevos
    try:
        with open(NEW_FILES_LIST, 'w', encoding='utf-8') as fh:
            for n in nuevos:
                fh.write(n + '\n')
    except Exception as e:
        print(f"⚠️ No se pudo escribir lista de nuevos archivos: {e}")

if __name__ == '__main__':
    main()
