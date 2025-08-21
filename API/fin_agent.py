from __future__ import annotations

"""
Agente Analista Financiero (AGNO):
- Aplica lógica financiera y criterios de riesgo de mercado
- Puede ofrecer análisis, retroalimentación y proyecciones basadas en datos
"""

from typing import Dict, Optional
import io
import pandas as pd
import numpy as np

class FinAgent:
    def __init__(self):
        self.memory: Dict[str, str] = {}

    def _df_from_json(self, data_json: Optional[str]) -> pd.DataFrame:
        if not data_json:
            return pd.DataFrame()
        return pd.read_json(io.StringIO(data_json), orient='split')

    def _risk_flags(self, df: pd.DataFrame) -> str:
        if df.empty:
            return "Sin banderas de riesgo (no hay datos)."
        # Señales simples: fuertes salidas vs SI, caída MoM de SL
        lines = ["Banderas de riesgo:"]
        if 'Movimientos' in df.columns:
            mv = pd.to_numeric(df['Movimientos'], errors='coerce')
            if mv.mean() < 0 and mv.sum() < 0:
                lines.append("- Predominio de salidas netas, posible presión de liquidez.")
        if 'Saldo Libros' in df.columns and 'Fecha' in df.columns:
            s = pd.to_numeric(df['Saldo Libros'], errors='coerce')
            df2 = df.copy()
            df2['Fecha'] = pd.to_datetime(df2['Fecha'], errors='coerce')
            df2 = df2.sort_values('Fecha')
            if s.notna().sum() >= 2:
                mom = df2['Saldo Libros'].diff().fillna(0)
                if (mom < 0).sum() >= 2:
                    lines.append("- Varias caídas consecutivas del saldo, revisar flujos.")
        return "\n".join(lines)

    def _projection(self, df: pd.DataFrame, periods: int = 1) -> str:
        if df.empty or 'Fecha' not in df.columns or 'Saldo Libros' not in df.columns:
            return "Sin proyección (datos insuficientes)."
        df = df.copy()
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.sort_values('Fecha')
        sl = pd.to_numeric(df['Saldo Libros'], errors='coerce')
        # Proyección lineal simple por tendencia
        try:
            x = np.arange(len(sl))
            coeffs = np.polyfit(x[sl.notna()], sl[sl.notna()], deg=1)
            slope, intercept = coeffs[0], coeffs[1]
            next_val = slope * (len(sl)) + intercept
            return f"Proyección SL próximo periodo (lineal simple): {next_val:.2f}"
        except Exception:
            return "Sin proyección (no fue posible ajustar tendencia)."

    def analyze(self, user_text: str, data_json: Optional[str], contexts: Dict[str, str]) -> str:
        df = self._df_from_json(data_json)
        # Omitir CXP si existe cuenta
        if 'Cuenta' in df.columns:
            df = df[~df['Cuenta'].astype(str).str.contains('CXP', case=False, na=False)]
        # Preparar periodo
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
            df['Periodo'] = df['Fecha'].dt.to_period('M').astype(str)
        # Riesgos y proyección
        flags = self._risk_flags(df)
        proj = self._projection(df)
        # Breve consolidado con contexto
        head_ctx = []
        for k in ['period_basic','rich','bancos']:
            if k in contexts and contexts[k]:
                head_ctx.append(f"[{k}]\n{contexts[k].splitlines()[-3:]}")
        ctx_snip = "\n\n".join(["\n".join(x if isinstance(x, list) else [str(x) for x in x]) if isinstance(x, list) else str(x) for x in head_ctx])
        result = f"Analista Financiero:\n{flags}\n{proj}\n\nContexto reciente:\n{ctx_snip}"
        self.memory['last_fin'] = result
        return result
