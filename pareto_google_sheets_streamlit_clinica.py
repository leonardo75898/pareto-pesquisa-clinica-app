# app.py
import re
from collections import Counter

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# =====================
# CONFIGURAÇÃO INICIAL
# =====================
st.set_page_config(layout="wide", page_title="Gráficos de Pareto")
st.title("📊 Gráficos de Pareto")
st.caption("Fonte: Respostas da planilha do Google Sheets (atualiza em tempo real)")

st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 2rem; }
[data-testid="column"] { padding: 0.25rem; }
</style>
""", unsafe_allow_html=True)

# =====================
# FUNÇÕES AUXILIARES
# =====================
def remove_prefixo_numerico(txt: str) -> str:
    return re.sub(r'^\s*\d+\)\s*', '', str(txt).strip())

def wrap_label(txt: str, largura: int = 22) -> str:
    palavras = str(txt).split()
    linhas, linha = [], ""
    for p in palavras:
        if len(linha) + len(p) + (1 if linha else 0) <= largura:
            linha = (linha + " " + p).strip()
        else:
            if linha: linhas.append(linha)
            linha = p
    if linha: linhas.append(linha)
    return "<br>".join(linhas)

def carregar_planilha_google_sheets(url: str):
    try:
        if "docs.google.com/spreadsheets/d/e/" in url:
            published_id = url.split("/d/e/")[1].split("/")[0]
            csv_url = f"https://docs.google.com/spreadsheets/d/e/{published_id}/pub?output=csv"
        elif "docs.google.com/spreadsheets/d/" in url:
            sheet_id = url.split("/d/")[1].split("/")[0]
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        else:
            st.error("URL inválida. Verifique se é um link público do Google Sheets.")
            return None
        return pd.read_csv(csv_url)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

def contar_respostas_multipla(df: pd.DataFrame, coluna: str) -> Counter:
    todas_respostas = []
    for resposta in df[coluna].dropna():
        opcoes = [op.strip() for op in str(resposta).split(",")]
        todas_respostas.extend(opcoes)
    return Counter(todas_respostas)

# =====================
# FIGURA: PARETO HORIZONTAL
# =====================
def figura_pareto_horizontal(counter: Counter, titulo: str, ampliado: bool = False):
    if not counter:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados para exibir", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template="plotly_white", height=420,
                          margin=dict(l=140, r=80, t=200, b=80))
        return fig

    labels, valores = zip(*counter.most_common())
    totais = np.array(valores, dtype=float)
    p_acum = 100 * np.cumsum(totais) / totais.sum()

    labels_wrapped = [wrap_label(l, 22) for l in labels]

    base_h = 46 * len(labels) + 240
    height = max(420, base_h)
    if ampliado:
        height = int(height * 1.35)

    fig = go.Figure()

    # Barras horizontais (Frequência)
    fig.add_trace(go.Bar(
        orientation="h",
        x=list(totais),
        y=labels_wrapped,
        name="Frequência",
        marker=dict(color="rgba(59,130,246,0.85)"),
        hovertemplate="%{y}<br>Frequência: %{x}<extra></extra>"
    ))

    # Linha de % acumulado (eixo x2 sobreposto)
    fig.add_trace(go.Scatter(
        x=list(p_acum),
        y=labels_wrapped,
        mode="lines+markers",
        name="% Acumulado",
        line=dict(color="rgba(17,24,39,1)", width=2),
        xaxis="x2",
        hovertemplate="% Acumulado: %{x:.1f}%<extra></extra>"
    ))

    # Eixo X (frequência)
    fig.update_xaxes(
        title_text="Frequência",
        showgrid=True,
        zeroline=False,
        anchor="y",
        domain=[0, 1]
    )

    # Eixo X2 (topo) % acumulado
    fig.update_layout(xaxis2=dict(
        title="% Acumulado",
        overlaying="x",
        side="top",
        range=[0, 110],
        tickmode="array",
        tickvals=[0, 20, 40, 60, 80, 100]
    ))

    # Eixo Y (categorias)
    fig.update_yaxes(
        title_text="",
        automargin=True,
        categoryorder="array",
        categoryarray=labels_wrapped,
        autorange="reversed"
    )

    # Linha 80% (vertical no x2)
    fig.add_shape(
        type="line",
        xref="x2", yref="paper",
        x0=80, x1=80, y0=0, y1=1,
        line=dict(color="gray", width=1, dash="dash")
    )

    # Título rebaixado e margem superior maior para não colidir com a modebar
    fig.update_layout(
        template="plotly_white",
        title={"text": titulo, "x": 0.5, "y": 0.88, "xanchor": "center", "yanchor": "top",
               "font": {"size": 26 if not ampliado else 30}},
        height=height,
        margin=dict(l=160, r=90, t=220 if not ampliado else 260, b=90),
        bargap=0.25,
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="right", x=1)
    )

    return fig

def plot_card(counter: Counter, titulo: str, key: str):
    """Ampliação inline, sem modal nem experimental_rerun."""
    state_key = f"ampliado_{key}"
    ampliado = st.session_state.get(state_key, False)

    config = {
        "displayModeBar": True,
        "scrollZoom": True,
        "responsive": True,
        "toImageButtonOptions": {
            "format": "png", "filename": titulo, "height": 1080, "width": 1920, "scale": 1
        },
    }

    # Gráfico
    fig = figura_pareto_horizontal(counter, titulo, ampliado=ampliado)
    st.plotly_chart(fig, use_container_width=True, config=config, key=f"plot_{'big_' if ampliado else 'small_'}{key}")

    # Controles
    c1, _ = st.columns([1, 6])
    with c1:
        if not ampliado:
            if st.button("Ampliar", key=f"btn_amp_{key}"):
                st.session_state[state_key] = True
        else:
            if st.button("Fechar", key=f"btn_close_{key}"):
                st.session_state[state_key] = False

# =====================
# URL DA PLANILHA
# =====================
URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSKwCflZovzD_0UAlLsDplKqWz2-WKs3agK-HaDQFmT6jx9RkkUAXNbUJvsD622uqUWTpXUTQ8XgILV/pub?output=csv"

# =====================
# CARREGAR DADOS E RENDERIZAR
# =====================
df = carregar_planilha_google_sheets(URL_GOOGLE_SHEETS)

if df is not None:
    st.success("✅ Planilha carregada com sucesso.")
    st.caption(f"Linhas carregadas: {len(df)}")

    perguntas = df.columns[1:8]

    for i in range(0, len(perguntas), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(perguntas):
                col_raw = perguntas[i + j]
                titulo = f"{i + j + 1}) {remove_prefixo_numerico(col_raw)}"
                counter = contar_respostas_multipla(df, col_raw)
                with cols[j]:
                    plot_card(counter, titulo, key=f"{i}_{j}")
else:
    st.error("❌ Não foi possível carregar os dados da planilha.")
