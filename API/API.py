"""
Conexión a la API de OpenAI.

Características:
- Lee la clave desde la variable de entorno OPENAI_API_KEY.
- Si falta, intenta leerla desde API/API.txt (línea que empiece con "clave API:").
- Expone una función chat(prompt, model) para obtener una respuesta sencilla.

Nota: Evita imprimir o registrar la clave. Recomendado mover la clave a variables de entorno.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Optional

try:
	# SDK moderno de OpenAI (>=1.0)
	from openai import OpenAI
except Exception as exc:  # pragma: no cover
	raise RuntimeError(
		"Falta la dependencia 'openai'. Instala con: pip install -r API/requirements.txt"
	) from exc


BASE_DIR = Path(__file__).resolve().parent
API_TXT_PATH = BASE_DIR / "API.txt"


def _parse_api_key_from_text(text: str) -> Optional[str]:
	"""Extrae la clave de un texto buscando 'clave API: <valor>'.

	Acepta variaciones de espacios y mayúsculas/minúsculas.
	"""
	m = re.search(r"clave\s*api\s*:\s*(\S+)", text, flags=re.IGNORECASE)
	return m.group(1).strip() if m else None


def _read_api_key_from_file(path: Path = API_TXT_PATH) -> Optional[str]:
	"""Lee la clave del archivo API.txt si existe."""
	if not path.exists():
		return None
	try:
		content = path.read_text(encoding="utf-8", errors="ignore")
	except Exception:
		return None
	return _parse_api_key_from_text(content)


def get_api_key() -> str:
	"""Obtiene la clave de API.

	Orden de prioridad:
	1) Variable de entorno OPENAI_API_KEY
	2) Archivo API/API.txt
	"""
	key = os.getenv("OPENAI_API_KEY")
	if key:
		return key.strip()

	key = _read_api_key_from_file()
	if key:
		return key

	raise RuntimeError(
		"No se encontró la clave de OpenAI. Define OPENAI_API_KEY como variable de entorno "
		"o añade una línea 'clave API: <tu_clave>' en API/API.txt."
	)


_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
	"""Crea (una sola vez) y retorna el cliente de OpenAI."""
	global _client
	if _client is None:
		api_key = get_api_key()
		_client = OpenAI(api_key=api_key)
	return _client


def chat(prompt: str, model: str = "gpt-4o-mini") -> str:
	"""Envía un prompt y devuelve el texto de la respuesta del asistente.

	Args:
		prompt: Texto de entrada.
		model: Modelo a usar (por defecto 'gpt-4o-mini').

	Returns:
		Texto de la respuesta.
	"""
	resp = chat_raw(prompt=prompt, model=model)
	choice = resp.choices[0] if resp and resp.choices else None
	content = choice.message.content if choice and getattr(choice, "message", None) else ""
	return content or ""


def chat_raw(
	prompt: str,
	model: str = "gpt-4o-mini",
	temperature: float = 0.2,
	max_tokens: int = 256,
):
	"""Llama a la API y retorna el objeto de respuesta original (incluye usage)."""
	client = get_client()
	return client.chat.completions.create(
		model=model,
		messages=[{"role": "user", "content": prompt}],
		temperature=temperature,
		max_tokens=max_tokens,
	)


def chat_messages(
	messages: list[dict],
	model: str = "gpt-4o-mini",
	temperature: float = 0.2,
	max_tokens: int = 512,
):
	"""Envía una lista de mensajes (roles: system|user|assistant) y retorna la respuesta.

	messages: lista como [{"role":"system","content":"..."}, {"role":"user","content":"..."}, ...]
	"""
	client = get_client()
	return client.chat.completions.create(
		model=model,
		messages=messages,
		temperature=temperature,
		max_tokens=max_tokens,
	)


def main(argv: list[str]) -> int:
	"""Ejecuta una demo desde línea de comandos y muestra uso de tokens.

	Ejemplos:
		python API/API.py "Di 'ok' y nada más."
		python API/API.py --model gpt-4o --temperature 0.2 --max-tokens 200 "Resume esto en 1 línea: ..."
	"""
	parser = argparse.ArgumentParser(description="Probar chat con OpenAI")
	parser.add_argument("prompt", nargs="*", help="Mensaje a enviar al modelo")
	parser.add_argument("--model", default="gpt-4o-mini", help="Modelo a utilizar")
	parser.add_argument("--temperature", type=float, default=0.2, help="Creatividad (0-2)")
	parser.add_argument("--max-tokens", dest="max_tokens", type=int, default=256, help="Límite de tokens de salida")

	args = parser.parse_args(argv[1:])

	prompt = " ".join(args.prompt).strip() if args.prompt else "Di 'ok' y nada más."
	try:
		resp = chat_raw(
			prompt=prompt,
			model=args.model,
			temperature=args.temperature,
			max_tokens=args.max_tokens,
		)
	except Exception as e:  # No exponer secretos
		print(f"Error al llamar a OpenAI: {e}")
		return 1

	# Imprimir contenido
	choice = resp.choices[0] if resp and resp.choices else None
	content = choice.message.content if choice and getattr(choice, "message", None) else ""
	print(content or "")

	# Imprimir uso de tokens si está disponible
	usage = getattr(resp, "usage", None)
	if usage:
		pt = getattr(usage, "prompt_tokens", None)
		ct = getattr(usage, "completion_tokens", None)
		tt = getattr(usage, "total_tokens", None)
		model_used = getattr(resp, "model", "")
		print("\n---")
		print(f"Modelo: {model_used}")
		if pt is not None and ct is not None and tt is not None:
			print(f"Tokens -> prompt: {pt} | respuesta: {ct} | total: {tt}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main(sys.argv))

