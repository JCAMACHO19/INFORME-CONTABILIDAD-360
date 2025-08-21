from __future__ import annotations

from typing import Dict, List
from agno.agent import Agent


def build_fin_agent(tools: List, contexts: Dict[str, str]) -> Agent:
    """Crea el agente financiero con instrucciones y contexto adicional."""
    return Agent(
        name="Analista Financiero",
        role="Analista financiero con criterios de riesgo y proyección",
        instructions=[
            "Identifica banderas de riesgo y realiza proyecciones simples cuando aplique.",
            "Usa el contexto bancario y avanzado para sustentar recomendaciones.",
            "Explica supuestos de manera clara.",
        ],
        tools=tools,
        add_context=False,
        additional_context=contexts.get('bancos','') or '',
        show_tool_calls=True,
        tool_call_limit=4,
    )
