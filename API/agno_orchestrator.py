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
        stat = build_stat_agent(tools, contexts)
        fin = build_fin_agent(tools, contexts)
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
        return {"agent": "team(stat+fin)", "result_text": text or ""}
