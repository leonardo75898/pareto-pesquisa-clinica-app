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

# CSS (corrige corte do título no mobile e melhora espaçamento)
st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 2rem; }
[data-testid="column"] { padding: 0.25rem; }

@media (max-width: 640px) {
  .block-container { padding-top: 2.4rem; }          /* empurra o topo para longe da app bar */
  h1 { font-size: 1.6rem; line-height: 1.25; margin-top: .25rem; }
}
</style>
""", unsafe_allow_html=True)

# =====================
# AJUSTES / CONFIGS
# =====================
HAS_MODAL = hasattr(st, "modal")

def slugify(txt: str) -> str:
  s = re.sub(r"\s+", "_", str(txt).strip())
  s = re.sub(r"[^\w\-_.()]+", "", s)
  return s.lower()

# export da câmera: card (FullHD) e modal (1440p)
CONFIG_IMG_CARD = {
  "displayModeBar": True, "scrollZoom": True, "responsive": True,
  "toImageButtonOptions": {"format": "png", "filename": "grafico", "height": 1080, "width": 1920, "scale": 1},
}
CONFIG_IMG_MODAL = {
  "displayModeBar": True, "scrollZoom": True, "responsive": True,
  "toImageButtonOptions": {"format": "png", "filename": "grafico", "height": 1440, "width": 2560, "scale": 1},
}

# =====================
# FUNÇÕES AUXILIARES
# =====================
def remove_prefixo_numerico(txt: str) -> str:
    return re.sub(r'^\s*\d+\)\s*', '', str(txt).strip())

def wrap_text_br(txt: str, max_chars: int = 40) -> str:
    """Quebra um texto em múltiplas linhas (<br>) próximo de espaços, útil p/ títulos."""
    t = str(txt).strip()
    out, linha = [], ""
    for palavra in t.split():
        if len(linha) + len(palavra) + (1 if linha else 0) <= max_chars:
            linha = (linha + " " + palavra).strip()
        else:
            if linha: out.append(linha)
            linha = palavra
    if linha: out.append(linha)
    return "<br>".join(out)

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

def criar_figura_pareto(counter: Counter, titulo: str,
                        *, title_size=26, axis_size=15, tick_size=12, legend_size=13,
                        height=480, bottom_margin=120, title_wrap=40):
    """Figura para CARD (mobile-friendly).
       - título com quebra <br>, fonte moderada
       - eixos/ticks menores para caber em telas estreitas
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.update_layout(template="plotly_white")

    if not counter:
        fig.add_annotation(text="Sem dados para exibir", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(margin=dict(l=70, r=40, t=130, b=bottom_margin), height=height)
        return fig

    labels, valores = zip(*counter.most_common())
    totais = np.array(valores, dtype=float)
    p_acum = 100 * np.cumsum(totais) / totais.sum()

    labels_wrapped = [wrap_text_br(l, 18) for l in labels]
    titulo_wrapped = wrap_text_br(titulo, title_wrap)

    fig.add_trace(
        go.Bar(x=list(labels), y=list(totais), name="Frequência",
               marker=dict(color="rgba(59,130,246,0.85)"),
               hovertemplate="%{x}<br>Frequência: %{y}<extra></extra>"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=list(labels), y=list(p_acum), mode="lines+markers", name="% Acumulado",
                   line=dict(color="rgba(17,24,39,1)", width=2),
                   hovertemplate="% Acumulado: %{y:.1f}%<extra></extra>"),
        secondary_y=True,
    )
    fig.add_hline(y=80, line_dash="dash", line_color="gray", secondary_y=True)

    fig.update_xaxes(tickmode="array", tickvals=list(labels), ticktext=labels_wrapped,
                     automargin=True, ticklabelstandoff=10, tickfont=dict(size=tick_size))
    fig.update_yaxes(title_text="Frequência", secondary_y=False,
                     automargin=True, title_font=dict(size=axis_size), tickfont=dict(size=tick_size))
    fig.update_yaxes(title_text="% Acumulado", range=[0,110], secondary_y=True,
                     automargin=True, title_font=dict(size=axis_size), tickfont=dict(size=tick_size))

    fig.update_layout(
        title={"text": titulo_wrapped, "x": 0.5, "y": 0.92, "xanchor": "center", "yanchor": "top",
               "font": {"size": title_size}},
        margin=dict(l=70, r=40, t=130, b=bottom_margin),
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="right", x=1,
                    font=dict(size=legend_size)),
        bargap=0.25,
        font=dict(size=tick_size),
    )
    return fig

def criar_figura_pareto_grande(counter: Counter, titulo: str):
    """Figura para MODAL/Download (título grande)"""
    return criar_figura_pareto(
        counter, titulo,
        title_size=40, axis_size=18, tick_size=14, legend_size=16,
        height=560, bottom_margin=160, title_wrap=48
    )

def abrir_ampliacao(counter: Counter, titulo: str, key: str):
    fig_big = criar_figura_pareto_grande(counter, titulo)
    if HAS_MODAL:
        with st.modal(titulo, key=f"modal_{key}"):
            st.plotly_chart(fig_big, key=f"plt_modal_{key}", use_container_width=True, config=CONFIG_IMG_MODAL)
            st.caption("Use o ícone de câmera (na barra do gráfico) para baixar em PNG 2560×1440.")
            st.button("Fechar", key=f"fechar_{key}")
    else:
        with st.expander(f"Visualização ampliada — {titulo}", expanded=True):
            st.plotly_chart(fig_big, key=f"plt_exp_{key}", use_container_width=True, config=CONFIG_IMG_MODAL)
            st.caption("Use o ícone de câmera (na barra do gráfico) para baixar em PNG 2560×1440.")
            if st.button("Fechar", key=f"fechar_{key}"):
                st.session_state[f"exp_{key}"] = False

def plot_card(counter: Counter, titulo: str, key: str):
    fig = criar_figura_pareto(counter, titulo)  # versão mobile-friendly
    st.plotly_chart(fig, key=f"plt_{key}", use_container_width=True, config=CONFIG_IMG_CARD)

    c1, _ = st.columns([1, 3])
    with c1:
        if st.button("Ampliar", key=f"amp_{key}"):
            st.session_state[f"show_{key}"] = True

    if st.session_state.get(f"show_{key}", False):
        abrir_ampliacao(counter, titulo, key)
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
                with cols[j]:
                    plot_card(contador, titulo, key=f"{i}_{j}")
else:
    st.error("❌ Não foi possível carregar os dados da planilha.")
