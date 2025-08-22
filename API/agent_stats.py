from __future__ import annotations

from typing import Dict, List
from agno.agent import Agent


def build_stat_agent(tools: List, contexts: Dict[str, str]) -> Agent:
    """Crea el agente estadístico con responsabilidades y estilo precisos."""
    style = contexts.get('_style', '') or ''
    addl_ctx = "\n\n".join([
        style.strip(),
        (contexts.get('period_basic','') or '').strip(),
        (contexts.get('rich','') or '').strip(),
    ]).strip()

    return Agent(
        name="Agente Estadístico-Calculador",
        role=(
            "Responsable de calcular y analizar magnitudes estadísticas y financieras derivadas:"
            " media, mediana, moda, desviación estándar, varianza, percentiles, rangos,"
            " tasas de variación (%), crecimiento intermensual/acumulado y contribuciones."
        ),
        instructions=[
            "Resuelve con precisión numérica, pero no muestres pasos, fórmulas detalladas ni los datos intermedios.",
            "Filtra por Banco/Empresa/Periodo cuando se solicite; omite filas cuya Cuenta contenga 'CXP'.",
            "Entrega solo las cifras esenciales: resultados finales y 1–3 porcentajes clave. Evita tablas y listados de periodos.",
            "Formatea números con separadores de miles y 2 decimales; porcentajes con 2 decimales y signo %.",
            "Si faltan datos, indícalo y sugiere un filtro alternativo o el periodo disponible más cercano.",
            "Prioriza explicación breve del hallazgo (tendencia/impacto) antes de las cifras.",
        ],
        tools=tools,
        add_context=False,
        additional_context=addl_ctx,
        show_tool_calls=False,
        tool_call_limit=4,
    )
