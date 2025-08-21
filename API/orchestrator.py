from __future__ import annotations

"""
AGNO: Orquestador simple de agentes especializados.
- Enruta la consulta al agente adecuado (estadístico o financiero).
- Provee memoria básica y consolidación de contexto para grounding.

Uso:
    from API.orchestrator import Orchestrator
    orchestrator = Orchestrator()
    result = orchestrator.handle_query(user_text, data_json, contexts={...})
    print(result["agent"], result["result_text"])
"""

import re
from typing import Dict, Optional

# Asegurar imports relativos al proyecto
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
if str(_ROOT) not in _sys.path:
    _sys.path.append(str(_ROOT))

from API.stat_agent import StatAgent
from API.fin_agent import FinAgent


INTENT_PATTERNS = {
    "stat": re.compile(
        r"promedio|media|mediana|percentil|desviaci[oó]n|varianza|correlaci[oó]n|regresi[oó]n|distribuci[oó]n|histograma|EDA|kpi|\bstd\b",
        re.IGNORECASE
    ),
    "fin": re.compile(
        r"riesgo|proyecci[oó]n|tendenc|variaci[oó]n|flujo|rendimiento|sensibilidad|escenario|VaR|valor en riesgo|margen|liquidez|apalancamiento|\bEBIT|WACC",
        re.IGNORECASE
    ),
}

# Señales por dominio bancario/financiero
BANK_CUES = re.compile(r"banco|cuenta|saldo|adiciones|salidas|libros|empresa|periodo|mes|a[ñn]o|\bYYYY-MM\b", re.IGNORECASE)


class Orchestrator:
    def __init__(self):
        self.stat_agent = StatAgent()
        self.fin_agent = FinAgent()

    def classify(self, user_text: str) -> str:
        t = user_text or ""
        if INTENT_PATTERNS["stat"].search(t):
            return "stat"
        if INTENT_PATTERNS["fin"].search(t):
            return "fin"
        # Heurística: si hay señales bancarias y piden variaciones/proyecciones -> fin, si piden totales/filtrado -> stat
        if BANK_CUES.search(t):
            if re.search(r"proyecci[oó]n|pron[oó]stico|escenario|riesgo|tendenc|variaci[oó]n", t, re.IGNORECASE):
                return "fin"
            return "stat"
        # Por defecto: financiero (para consultas cualitativas)
        return "fin"

    def handle_query(self, user_text: str, data_json: Optional[str], contexts: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        agent_key = self.classify(user_text)
        try:
            if agent_key == "stat":
                result_text = self.stat_agent.analyze(user_text=user_text, data_json=data_json, contexts=contexts or {})
            else:
                result_text = self.fin_agent.analyze(user_text=user_text, data_json=data_json, contexts=contexts or {})
        except Exception as ex:
            result_text = f"[Orquestador] No se pudo completar el análisis: {ex}"
        return {"agent": agent_key, "result_text": result_text}
