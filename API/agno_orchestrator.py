from __future__ import annotations

"""
AGNO nativo: orquestador multiagente sin fallback legacy.
- Define agentes declarativos (estadístico y financiero) con herramientas específicas.
- Usa Team para coordinar en modo 'coordinate' (ruta/cascada) y fusionar respuestas.
- Integra memoria (AGNO) y limita tokens vía resúmenes externos (contexts).
"""

from typing import Dict, Optional, List
import os
import io
import pandas as pd

from agno.team import Team
# Carga modular de herramientas y agentes
from API.agents_tools import make_tools
from API.agent_stats import build_stat_agent
from API.agent_fin import build_fin_agent


def _mk_tools_for_query(data_json: Optional[str], contexts: Dict[str, str]):
    return make_tools(data_json, contexts)


class AgnoOrchestrator:
    def __init__(self):
        # Asegurar OPENAI_API_KEY para AGNO si no está en entorno (lee de API.txt si procede)
        try:
            if not os.getenv("OPENAI_API_KEY"):
                from API.API import get_api_key  # carga perezosa para evitar dependencias prematuras
                os.environ["OPENAI_API_KEY"] = get_api_key()
        except Exception:
            # Si falla, AGNO intentará y reportará; el chat principal también puede manejarlo.
            pass
        # Sin memoria explícita (opcional añadir backend en el futuro).

    def _make_agents(self, tools: List, contexts: Dict[str, str]) -> List:
        # Guía de estilo compartida para limitar cifras y priorizar claridad
        style_guide = (
            "Estilo de respuesta (obligatorio): lenguaje natural, claro y breve. "
            "Incluye solo números esenciales: resultados finales y porcentajes clave; evita tablas largas y listados extensos. "
            "Máximo 2–4 cifras por párrafo. Explica el 'por qué' y las implicaciones."
        )
        cx = dict(contexts or {})
        cx['_style'] = style_guide
        stat = build_stat_agent(tools, cx)
        fin = build_fin_agent(tools, cx)
        return [stat, fin]

    def handle_query(self, user_text: str, data_json: Optional[str], contexts: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        contexts = contexts or {}
        tools = _mk_tools_for_query(data_json, contexts)
        agents = self._make_agents(tools, contexts)
        team = Team(members=agents, mode='coordinate', show_members_responses=False)
        # Ejecutar equipo: AGNO decidirá rutas/transferencias y fusionará resultados
        run = team.run(message=user_text)
        # Extraer texto de salida de forma robusta
        text = None
        for attr in ('output_text', 'text', 'content', 'response', 'message', 'messages'):
            if hasattr(run, attr):
                v = getattr(run, attr)
                if isinstance(v, str):
                    text = v
                    break
        if text is None:
            try:
                text = str(run)
            except Exception:
                text = ""
        # Síntesis final: reforzar estilo y recortar números redundantes
        try:
            synthesized = _synthesize_final_answer(user_text, text or "", contexts)
        except Exception:
            synthesized = text or ""
        return {"agent": "team(stat+fin)", "result_text": synthesized}


def _synthesize_final_answer(prompt: str, draft: str, contexts: Dict[str, str]) -> str:
    """Realiza una síntesis rápida basada en reglas para asegurar brevedad y foco.

    - Mantiene 3–6 frases máximo.
    - Incluye hasta 2–4 cifras esenciales (detectadas por % o números grandes) y elimina el resto.
    - Prioriza conclusiones, riesgos y acciones.
    """
    if not draft:
        return ""
    import re
    # Partir en frases y limpiar espacios
    sentences = re.split(r"(?<=[\.!?])\s+", draft.strip())
    # Regla: mantener primeras 3–5 frases que aporten insight (no listas ni pasos)
    kept = []
    num_count = 0
    for s in sentences:
        if len(kept) >= 6:
            break
        # descartar frases que parezcan pasos/viñetas largas
        if re.match(r"^[-•\d]+[\).:-]", s.strip()):
            continue
        # contar cifras y limitar
        nums = re.findall(r"(?:\d+[\.,]?\d*\s*%|\$?\d{2,}(?:[\.,]\d{3})*(?:[\.,]\d+)?)", s)
        if num_count + len(nums) > 4 and nums:
            # intenta recortar números extra
            excess = (num_count + len(nums)) - 4
            if excess > 0:
                # elimina los últimos 'excess' números encontrados
                for n in nums[::-1][:excess]:
                    s = s.replace(n, "", 1)
                nums = nums[:-excess] if excess < len(nums) else []
        num_count += len(nums)
        kept.append(s.strip())
    # Si faltan acciones, añade una breve sugerencia basada en prompt
    text = " ".join(kept).strip()
    if not re.search(r"recom|accion|suger", text, flags=re.I):
        text += " Recomendación: centraliza la conclusión en 1–2 acciones inmediatas (p. ej., ajustar flujo en bancos con mayores salidas)."
    return text
