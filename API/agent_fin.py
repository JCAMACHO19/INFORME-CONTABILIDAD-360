from __future__ import annotations

from typing import Dict, List
from agno.agent import Agent


def build_fin_agent(tools: List, contexts: Dict[str, str]) -> Agent:
    """Crea el agente financiero con enfoque descriptivo y predictivo."""
    style = contexts.get('_style', '') or ''
    addl_ctx = "\n\n".join([
        style.strip(),
        (contexts.get('bancos','') or '').strip(),
        (contexts.get('rich','') or '').strip(),
    ]).strip()

    return Agent(
        name="Agente Financiero (Descriptivo & Predictivo)",
        role=(
            "Responsable de análisis, crítica y recomendaciones financieras:"
            " identifica riesgos y oportunidades, explica drivers, y propone acciones."
            " Puede estimar tendencias y escenarios (proyección simple) justificando supuestos."
        ),
        instructions=[
            "Prioriza lenguaje natural claro; incluye solo 2–4 números clave (resultado, % variación, magnitudes relevantes). No listes series completas.",
            "Enfatiza implicaciones (liquidez, concentración bancaria, dependencia de flujos) y recomendaciones accionables.",
            "Declara supuestos al proyectar (p. ej., tendencia lineal, estacionalidad ignorada).",
            "No devuelvas tablas ni listados numéricos largos; resume y referencia solo periodos o bancos clave cuando ayuden a la conclusión.",
            "Termina con 1–2 acciones concretas priorizadas (breves).",
        ],
        tools=tools,
        add_context=False,
        additional_context=addl_ctx,
        show_tool_calls=False,
        tool_call_limit=4,
    )
