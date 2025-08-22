from __future__ import annotations

from typing import Dict, Optional, List, Callable
import io
import pandas as pd
from agno.tools import tool


def make_tools(data_json: Optional[str], contexts: Dict[str, str]) -> List[Callable]:
    """Crea herramientas (tools) AGNO cerradas sobre los datos y contextos de la consulta.

    Devuelve una lista de funciones decoradas con @tool.
    """
    df = pd.read_json(io.StringIO(data_json), orient='split') if data_json else pd.DataFrame()

    # Tipos y columnas derivadas
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df['Periodo'] = df['Fecha'].dt.to_period('M').astype(str)
    if 'Cuenta' in df.columns:
        df = df[~df['Cuenta'].astype(str).str.contains('CXP', case=False, na=False)]
    for c in ['Saldo Inicial','Saldo Libros','Movimientos','Adiciones','Salidas']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    if 'Movimientos' in df.columns:
        if 'Adiciones' not in df.columns:
            df['Adiciones'] = df['Movimientos'].where(df['Movimientos'] > 0, 0.0)
        if 'Salidas' not in df.columns:
            df['Salidas'] = (-df['Movimientos'].where(df['Movimientos'] < 0, 0.0)).abs()

    @tool(name="stat_summary", description="Resumen estadístico (p50, p90, media, std) de una columna; filtros opcionales por Banco/Empresa/Periodo.")
    def stat_summary(column: str = 'Movimientos', banco: str = '', empresa: str = '', periodo: str = '') -> str:
        dd = df
        if banco and 'Banco' in dd.columns:
            dd = dd[dd['Banco'].astype(str).str.contains(banco, case=False, na=False)]
        if empresa and 'Empresa' in dd.columns:
            dd = dd[dd['Empresa'].astype(str).str.contains(empresa, case=False, na=False)]
        if periodo and 'Periodo' in dd.columns:
            dd = dd[dd['Periodo'] == periodo]
        if column not in dd.columns or dd.empty:
            return f"Sin datos para {column}."
        s = pd.to_numeric(dd[column], errors='coerce')
        res = {
            'p50': float(s.quantile(0.5)) if s.notna().any() else 0.0,
            'p90': float(s.quantile(0.9)) if s.notna().any() else 0.0,
            'media': float(s.mean()) if s.notna().any() else 0.0,
            'std': float(s.std()) if s.notna().any() else 0.0,
        }
        return f"{column}: p50={res['p50']:.2f}, p90={res['p90']:.2f}, media={res['media']:.2f}, std={res['std']:.2f}"

    @tool(name="bank_slice", description="Resumen por Banco+Empresa+Periodo: SI, SL, MV, Adiciones y Salidas para un filtro específico.")
    def bank_slice(banco: str = '', empresa: str = '', periodo: str = '') -> str:
        dd = df
        if banco and 'Banco' in dd.columns:
            dd = dd[dd['Banco'].astype(str).str.contains(banco, case=False, na=False)]
        if empresa and 'Empresa' in dd.columns:
            dd = dd[dd['Empresa'].astype(str).str.contains(empresa, case=False, na=False)]
        if periodo and 'Periodo' in dd.columns:
            dd = dd[dd['Periodo'] == periodo]
        if dd.empty:
            return "Sin datos para el filtro solicitado."
        cols = {k: 'sum' for k in ['Saldo Inicial','Saldo Libros','Movimientos','Adiciones','Salidas'] if k in dd.columns}
        gcols = [c for c in ['Periodo','Empresa','Banco'] if c in dd.columns]
        agg = dd.groupby(gcols, as_index=False).agg(cols)
        r = agg.iloc[-1].to_dict()
        return (
            f"{r.get('Periodo','')} | {r.get('Empresa','')} | Banco={r.get('Banco','')} | "
            f"SI={r.get('Saldo Inicial',0.0):.2f} | Adiciones={r.get('Adiciones',0.0):.2f} | "
            f"Salidas={r.get('Salidas',0.0):.2f} | MV={r.get('Movimientos',0.0):.2f} | SL={r.get('Saldo Libros',0.0):.2f}"
        )

    @tool(name="latest_period_kpis", description="KPIs clave del último periodo disponible por Empresa: SL, MV, variación % vs periodo previo.")
    def latest_period_kpis(empresa: str = '') -> str:
        dd = df
        if empresa and 'Empresa' in dd.columns:
            dd = dd[dd['Empresa'].astype(str).str.contains(empresa, case=False, na=False)]
        if 'Periodo' not in dd.columns or dd.empty:
            return "Sin datos."
        d2 = dd.copy()
        d2 = d2.groupby(['Periodo','Empresa'], as_index=False).agg({
            k: 'sum' for k in ['Saldo Libros','Movimientos','Adiciones','Salidas'] if k in d2.columns
        })
        d2 = d2.sort_values('Periodo')
        last = d2.iloc[-1]
        prev = d2.iloc[-2] if len(d2) > 1 else None
        sl = float(last.get('Saldo Libros', 0.0))
        mv = float(last.get('Movimientos', 0.0))
        var = 0.0
        if prev is not None and 'Saldo Libros' in d2.columns:
            prev_sl = float(prev.get('Saldo Libros', 0.0))
            if prev_sl:
                var = (sl - prev_sl) / abs(prev_sl) * 100.0
        return f"Periodo {last['Periodo']} | SL={sl:.2f} | MV={mv:.2f} | Var% vs previo={var:.2f}%"

    @tool(name="top_banks_concentration", description="Concentración top-3 bancos del SL del último periodo (porcentaje sobre total empresa).")
    def top_banks_concentration(empresa: str = '') -> str:
        dd = df
        if empresa and 'Empresa' in dd.columns:
            dd = dd[dd['Empresa'].astype(str).str.contains(empresa, case=False, na=False)]
        if 'Periodo' not in dd.columns or 'Banco' not in dd.columns or 'Saldo Libros' not in dd.columns or dd.empty:
            return "Sin datos."
        last_period = dd['Periodo'].dropna().max()
        d2 = dd[dd['Periodo'] == last_period]
        g = d2.groupby('Banco', as_index=False)['Saldo Libros'].sum().sort_values('Saldo Libros', ascending=False)
        total = float(g['Saldo Libros'].sum()) or 1.0
        g['pct'] = g['Saldo Libros'] / total * 100.0
        top3 = g.head(3)
        pct_top3 = float(top3['pct'].sum())
        names = ", ".join(top3['Banco'].astype(str).tolist())
        return f"Periodo {last_period} | Top3={pct_top3:.2f}% del SL total ({names})"

    @tool(name="kpi_bundle", description="Paquete de KPIs concisos para respuesta final: SL último, Var% MoM, MV neto, Top3 concentración.")
    def kpi_bundle(empresa: str = '') -> str:
        return "; ".join([
            latest_period_kpis(empresa=empresa),
            top_banks_concentration(empresa=empresa),
        ])

    @tool(name="fin_risk_projection", description="Evalúa banderas de riesgo básicas y proyecta SL de forma lineal.")
    def fin_risk_projection(empresa: str = '', banco: str = '') -> str:
        dd = df
        if empresa and 'Empresa' in dd.columns:
            dd = dd[dd['Empresa'].astype(str).str.contains(empresa, case=False, na=False)]
        if banco and 'Banco' in dd.columns:
            dd = dd[dd['Banco'].astype(str).str.contains(banco, case=False, na=False)]
        if dd.empty:
            return "Sin datos para evaluar riesgo/proyección."
        flags = []
        if 'Movimientos' in dd.columns:
            mv = pd.to_numeric(dd['Movimientos'], errors='coerce')
            if mv.mean() < 0 and mv.sum() < 0:
                flags.append("Predominio de salidas netas")
        proj = "Sin proyección"
        if 'Saldo Libros' in dd.columns and 'Fecha' in dd.columns:
            d2 = dd[['Fecha','Saldo Libros']].copy().sort_values('Fecha')
            s = pd.to_numeric(d2['Saldo Libros'], errors='coerce')
            if s.notna().sum() >= 2:
                import numpy as np
                x = np.arange(len(s))
                try:
                    slope, intercept = np.polyfit(x[s.notna()], s[s.notna()], 1)
                    proj = f"Proyección SL próximo periodo: {slope*len(s)+intercept:.2f}"
                except Exception:
                    pass
        flags_txt = "; ".join(flags) if flags else "Sin banderas relevantes"
        return f"Riesgo: {flags_txt} | {proj}"

    # Contextos como tools
    ctx_period = contexts.get('period_basic', '') or ''
    ctx_rich = contexts.get('rich', '') or ''
    ctx_bancos = contexts.get('bancos', '') or ''

    @tool(name="context_period", description="Contexto agregado por periodo y empresa.")
    def context_period() -> str:
        return ctx_period

    @tool(name="context_rich", description="Contexto avanzado con adiciones/salidas, variaciones y totales.")
    def context_rich() -> str:
        return ctx_rich

    @tool(name="context_bancos", description="Contexto bancario (Banco+Empresa+Periodo).")
    def context_bancos() -> str:
        return ctx_bancos

    return [
        stat_summary,
        bank_slice,
        latest_period_kpis,
        top_banks_concentration,
        kpi_bundle,
        fin_risk_projection,
        context_period,
        context_rich,
        context_bancos,
    ]
