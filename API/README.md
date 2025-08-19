# API de OpenAI (carpeta API)

Este módulo crea una conexión sencilla con OpenAI y expone la función `chat(prompt, model)`.

## Instalación

1) Activar el entorno virtual que ya usas en el proyecto (si aplica).
2) Instalar dependencias:

```powershell
pip install -r API/requirements.txt
```

## Configurar la clave

- Opción recomendada: variable de entorno `OPENAI_API_KEY`.
- Alternativa: en `API/API.txt` añade una línea como:

```
clave API: sk-....
```

Nota: No subas tu clave a repositorios públicos.

## Uso rápido

```powershell
python API/API.py "Hola, ¿quién eres?"
```

O desde Python:

```python
from API.API import chat
print(chat("Di 'ok'"))
```

## Modelos

El valor por defecto es `gpt-4o-mini`. Puedes cambiarlo pasando `model="gpt-4o"`, etc.
