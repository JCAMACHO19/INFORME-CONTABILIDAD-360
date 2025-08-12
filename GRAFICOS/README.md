# Dashboard Saldo Libros

Aplicación Dash sencilla que grafica "Saldo Libros" por fecha y empresa usando los archivos Excel generados en la carpeta `INFORME BANCOS/SALDO BANCOS`.

## Instalación
```powershell
cd "c:\Users\jcamacho\Desktop\INFORME CONTABILIDAD 360\GRAFICOS"
pip install -r requirements.txt
```

## Ejecución
```powershell
python app.py
```
Abrir en el navegador: http://127.0.0.1:8050

## Datos requeridos
Columnas en los Excel:
- Empresa
- Fecha (dd/mm/yyyy o ISO)
- Saldo Libros

## Funcionalidad
- Filtro por empresa.
- Botón para recargar datos.
- Gráfico de líneas con marcadores.

## Notas
- Limpieza básica de números (puntos miles y coma decimal).
