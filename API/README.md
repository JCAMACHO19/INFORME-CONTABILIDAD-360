# API de OpenAI (carpeta API)

Este módulo crea una conexión sencilla con OpenAI y expone la función `chat(prompt, model)`.

## Instalación

1) Activar el entorno virtual que ya usas en el proyecto (si aplica).
2) Instalar dependencias:

```powershell
pip install -r API/requirements.txt
```

## Configurar la clave

# API (AGNO-only)

Este módulo usa únicamente AGNO para la orquestación multiagente. Se eliminó el código legacy.

Piezas principales:
- `API.py`: cliente OpenAI 1.x; lee la clave de `OPENAI_API_KEY` o `API/API.txt` (línea `clave API: ...`).
- `agno_orchestrator.py`: define herramientas por consulta, crea agentes AGNO y ejecuta un `Team` en modo `coordinate`.

Requisitos:
- Instala dependencias desde `API/requirements.txt`.
- Configura `OPENAI_API_KEY` o añade `clave API: TU_CLAVE` a `API/API.txt`.

Notas:
- No hay fallback legacy; toda la lógica pasa por AGNO.

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
