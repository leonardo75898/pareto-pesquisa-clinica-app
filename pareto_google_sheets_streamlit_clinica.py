# app.py
import re
from collections import Counter

import numpy as np
import pandas as pd
import streamlit as st
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# =====================
# CONFIGURAÇÃO INICIAL
# =====================
st.set_page_config(layout="wide", page_title="Gráficos de Pareto")
st.title("📊 Gráficos de Pareto")
st.caption("Fonte: Respostas da planilha do Google Sheets (atualiza em tempo real)")

# CSS básico
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

def wrap_label(txt: str, largura: int = 18) -> str:
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

def criar_figura_pareto(counter: Counter, titulo: str):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.update_layout(template="plotly_white")

    if not counter:
        fig.add_annotation(text="Sem dados para exibir", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(margin=dict(l=70, r=40, t=120, b=120), height=440)
        return fig

    labels, valores = zip(*counter.most_common())
    totais = np.array(valores, dtype=float)
    p_acum = 100 * np.cumsum(totais) / totais.sum()

    labels_wrapped = [wrap_label(l, 18) for l in labels]

    fig.add_trace(
        go.Bar(
            x=list(labels),
            y=list(totais),
            name="Frequência",
            marker=dict(color="rgba(59,130,246,0.85)"),
            hovertemplate="%{x}<br>Frequência: %{y}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=list(labels),
            y=list(p_acum),
            mode="lines+markers",
            name="% Acumulado",
            line=dict(color="rgba(17,24,39,1)", width=2),
            hovertemplate="% Acumulado: %{y:.1f}%<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.add_hline(y=80, line_dash="dash", line_color="gray", secondary_y=True)

    fig.update_yaxes(title_text="Frequência", secondary_y=False, automargin=True)
    fig.update_yaxes(title_text="% Acumulado", range=[0,110], secondary_y=True, automargin=True)
    fig.update_xaxes(
        tickmode="array", tickvals=list(labels), ticktext=labels_wrapped,
        automargin=True, ticklabelstandoff=10
    )

    # Título único (dentro do gráfico), longe da modebar
    fig.update_layout(
        title={"text": titulo, "x": 0.5, "y": 0.92, "xanchor": "center", "yanchor": "top"},
        margin=dict(l=70, r=40, t=120, b=120),
        height=440,
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="right", x=1),
        bargap=0.25,
    )
    return fig

def plot_card(fig, titulo: str, key: str):
    # Barra do Plotly configurada para exportar em 1920x1080 via ícone de câmera
    config = {
        "displayModeBar": True,
        "scrollZoom": True,
        "responsive": True,
        "toImageButtonOptions": {"format": "png", "filename": titulo, "height": 1080, "width": 1920, "scale": 1},
    }

    st.plotly_chart(fig, use_container_width=True, config=config)

    c1, _ = st.columns([1, 3])
    with c1:
        if st.button("Ampliar", key=f"amp_{key}"):
            st.session_state[f"show_{key}"] = True

    if st.session_state.get(f"show_{key}", False):
        with st.modal(titulo, key=f"modal_{key}"):
            st.plotly_chart(fig, use_container_width=True, config=config)
            st.caption("Use o ícone de câmera (na barra do gráfico) para baixar em PNG 2K.")
            if st.button("Fechar", key=f"fechar_{key}"):
                st.session_state[f"show_{key}"] = False

# =====================
# URL DA PLANILHA
# =====================
URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSKwCflZovzD_0UAlLsDplKqWz2-WKs3agK-HaDQFmT6jx9RkkUAXNbUJvsD622uqUWTpXUTQ8XgILV/pub?output=csv"

# =====================
# CARREGAR DADOS
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
                contador = contar_respostas_multipla(df, col_raw)
                fig = criar_figura_pareto(counter=contador, titulo=titulo)
                with cols[j]:
                    plot_card(fig, titulo, key=f"{i}_{j}")
else:
    st.error("❌ Não foi possível carregar os dados da planilha.")
