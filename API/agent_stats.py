from __future__ import annotations

from typing import Dict, List
from agno.agent import Agent


def build_stat_agent(tools: List, contexts: Dict[str, str]) -> Agent:
    """Crea el agente estadístico con instrucciones y contexto adicional."""
    return Agent(
        name="Estadístico-Calculador",
        role="Analista estadístico con precisión numérica",
        instructions=[
            "Responde con cálculos exactos, usando herramientas si es necesario.",
            "Usa Banco/Empresa/Periodo para filtrar; omite filas con 'CXP'.",
            "Devuelve cifras con miles y 2 decimales.",
        ],
        tools=tools,
        add_context=False,
        additional_context=(contexts.get('period_basic','') or '') + "\n\n" + (contexts.get('rich','') or ''),
        show_tool_calls=True,
        tool_call_limit=4,
    )
