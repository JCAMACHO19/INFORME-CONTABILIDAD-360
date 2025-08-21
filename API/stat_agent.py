from __future__ import annotations

"""
Agente Estadístico-Calculador (AGNO):
- Memoria básica (resumen acumulado por clave de intención)
- Herramientas: Pandas (JSON de DataFrame), SQL (placeholder), API (placeholder), vector store (placeholder)
- Precisión numérica y cálculos detallados
"""

from typing import Dict, Optional
import io
import json
import pandas as pd
import numpy as np
from pathlib import Path
from API.memory import MemoryStore

# Placeholders para herramientas externas (SQL/API/VectorStore)
class SQLTool:
    def query(self, sql: str) -> pd.DataFrame:
        # TODO: implementar
        return pd.DataFrame()

class APITool:
    def call(self, endpoint: str, payload: dict) -> dict:
        # TODO: implementar
        return {"ok": True}

class VectorStore:
    def __init__(self):
        self._docs = []
    def add(self, text: str, meta: dict | None = None):
        self._docs.append({"text": text, "meta": meta or {}})
    def similarity_search(self, query: str, k: int = 3):
        # Simplificado: devuelve los últimos k
        return self._docs[-k:]


class StatAgent:
    def __init__(self):
        self.sql = SQLTool()
        self.api = APITool()
        self.vstore = VectorStore()
        self.memory = {}
        self.long_memory = MemoryStore(namespace="stat_agent")

    def _df_from_json(self, data_json: Optional[str]) -> pd.DataFrame:
        if not data_json:
            return pd.DataFrame()
        return pd.read_json(io.StringIO(data_json), orient='split')

    def _build_numeric_summary(self, df: pd.DataFrame) -> str:
        if df.empty:
            return "No hay datos para análisis estadístico."
        cols = [c for c in ["Saldo Inicial","Saldo Libros","Movimientos","Adiciones","Salidas"] if c in df.columns]
        lines = ["Resumen estadístico (p50, p90, media, std):"]
        for c in cols:
            s = pd.to_numeric(df[c], errors='coerce')
            lines.append(
                f"{c}: p50={s.quantile(0.5):.2f}, p90={s.quantile(0.9):.2f}, media={s.mean():.2f}, std={s.std():.2f}"
            )
        return "\n".join(lines)

    def analyze(self, user_text: str, data_json: Optional[str], contexts: Dict[str, str]) -> str:
        df = self._df_from_json(data_json)
        # Filtros rápidos por empresa/banco/periodo si están en el texto (heurístico simple)
        if not df.empty:
            if 'Fecha' in df.columns:
                df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
                df['Periodo'] = df['Fecha'].dt.to_period('M').astype(str)
            # Heurística: banco
            import re
            m_banco = re.search(r"banco\s*:?\s*([\w\s\.]+)", user_text, re.IGNORECASE)
            if m_banco and 'Banco' in df.columns:
                banco = m_banco.group(1).strip()
                df = df[df['Banco'].astype(str).str.contains(banco, case=False, na=False)]
            # Periodo YYYY-MM
            m_periodo = re.search(r"(\d{4}[-/](0[1-9]|1[0-2]))", user_text)
            if m_periodo and 'Periodo' in df.columns:
                per = m_periodo.group(1).replace('/', '-')
                df = df[df['Periodo'] == per]
        # Resumen
        summary = self._build_numeric_summary(df)
        # Guardar memoria simple + persistente
        self.memory['last_summary'] = summary
        self.long_memory.add({"type":"summary","text": summary})
        # Adjuntar últimos recuerdos para enriquecer salida
        recents = self.long_memory.recent(limit=3)
        rec_text = "\n".join([f"[mem] {r.get('text','')}" for r in recents])
        return summary + ("\n\n" + rec_text if rec_text else "")
