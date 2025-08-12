import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
scripts = [
    "rename.py",
    "clean.py",
    "estandar.py",
    "agregar_colum.py",
    "agregar_colm2.py"
]

for script in scripts:
    script_path = BASE_DIR / script
    print(f"\n🟡 Ejecutando {script_path.name}...")
    try:
        subprocess.run([sys.executable, str(script_path)], check=True)
        print(f"✅ {script_path.name} ejecutado correctamente.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar {script_path.name}: {e}")
        break
