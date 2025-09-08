# app.py
import re
import io
import zipfile
from collections import Counter
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# =====================
# CONFIGURAÇÃO INICIAL
# =====================
st.set_page_config(layout="wide", page_title="Gráficos de Pareto")

st.markdown(
    """
    <style>
    .block-container { padding-top: .8rem; padding-bottom: 2rem; }
    [data-testid="column"] { padding: 0.25rem; }
    .toolbar { display:flex; justify-content:flex-end; gap:.5rem; }
    .tip { font-size:0.85rem; color:#4b5563; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Gráficos de Pareto")
st.caption("Fonte: respostas de formulário no Google Sheets (atualiza em tempo real)")

# =====================
# FUNÇÕES AUXILIARES
# =====================
def remove_prefixo_numerico(txt: str) -> str:
    return re.sub(r'^\s*\d+\)\s*', '', str(txt).strip())

def wrap_text(txt: str, largura: int) -> str:
    """Quebra em <br> sem estourar; largura é em caracteres approx."""
    palavras = str(txt).split()
    linhas, linha = [], ""
    for p in palavras:
        if len(linha) + len(p) + (1 if linha else 0) <= largura:
            linha = (linha + " " + p).strip()
        else:
            if linha:
                linhas.append(linha)
            linha = p
    if linha:
        linhas.append(linha)
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
def figura_pareto_horizontal(counter: Counter, titulo: str, largura_rotulo=24, ampliado=False) -> go.Figure:
    """
    Barras HORIZONTAIS (x=frequência), eixo x2 superior para % acumulado.
    Título em faixa azul (quebra automática se for longo).
    Compatível com Plotly 5.0.0.
    """
    fig = go.Figure()

    if not counter:
        fig.add_annotation(text="Sem dados para exibir", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template="plotly_white", height=420,
                          margin=dict(l=140, r=80, t=200, b=80))
        return fig

    labels, valores = zip(*counter.most_common())
    totais = np.array(valores, dtype=float)
    p_acum = 100 * np.cumsum(totais) / totais.sum()

    labels_wrapped = [wrap_text(l, largura_rotulo) for l in labels]

    base_h = 48 * len(labels) + 260
    height = max(480, base_h)
    if ampliado:
        height = int(height * 1.25)

    # Barras horizontais
    fig.add_trace(go.Bar(
        orientation="h",
        x=list(totais),
        y=labels_wrapped,
        name="Frequência",
        marker=dict(color="rgba(59,130,246,0.88)"),
        hovertemplate="%{y}<br>Frequência: %{x}<extra></extra>"
    ))

    # Linha % acumulado (x2)
    fig.add_trace(go.Scatter(
        x=list(p_acum),
        y=labels_wrapped,
        mode="lines+markers",
        name="% Acumulado",
        line=dict(color="rgba(17,24,39,1)", width=3),
        xaxis="x2",
        hovertemplate="% Acumulado: %{x:.1f}%<extra></extra>"
    ))

    # Eixo X (frequência)
    fig.update_xaxes(
        title_text="Frequência",
        showgrid=True,
        zeroline=False,
        anchor="y",
        domain=[0, 1],
        title_font=dict(size=20),
        tickfont=dict(size=16)
    )

    # Eixo X2 (topo) % acumulado  <<< correção: usar title={'text','font'} em vez de titlefont
    fig.update_layout(xaxis2=dict(
        title=dict(text="% Acumulado", font=dict(size=20)),
        overlaying="x",
        side="top",
        range=[0, 110],
        tickmode="array",
        tickvals=[0, 20, 40, 60, 80, 100],
        tickfont=dict(size=16)
    ))

    # Eixo Y (categorias)
    fig.update_yaxes(
        title_text="",
        automargin=True,
        categoryorder="array",
        categoryarray=labels_wrapped,
        autorange="reversed",
        tickfont=dict(size=16)
    )

    # Linha 80% (vertical no x2)
    fig.add_shape(
        type="line",
        xref="x2", yref="paper",
        x0=80, x1=80, y0=0, y1=1,
        line=dict(color="gray", width=2, dash="dash")
    )

    # Título com faixa azul (quebra em 2+ linhas se necessário)
    titulo_env = wrap_text(titulo, 70)
    fig.update_layout(
        template="plotly_white",
        title={
            "text": f"<span style='background-color:#1d4ed8; color:white; padding:8px 18px; border-radius:8px; display:inline-block;'>{titulo_env}</span>",
            "x": 0.5, "y": 0.96, "xanchor": "center", "yanchor": "top",
            "font": {"size": 28 if not ampliado else 32}
        },
        height=height,
        margin=dict(l=180, r=100, t=160, b=100),
        bargap=0.25,
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="right", x=1,
                    font=dict(size=16))
    )
    return fig

# =====================
# EXPORTAÇÃO
# =====================
def fig_to_png_bytes(fig: go.Figure, filename: str, width=1920, height=1080, scale=2) -> Tuple[str, bytes]:
    """Renderiza PNG via kaleido. Se kaleido faltar, avisa e evita quebrar a execução."""
    try:
        buf = io.BytesIO()
        fig.write_image(buf, format="png", width=width, height=height, scale=scale)
        buf.seek(0)
        return f"{filename}.png", buf.read()
    except Exception as e:
        st.error("Falha ao exportar PNG. Instale o pacote **kaleido** (`pip install -U kaleido`).")
        raise e

def zip_bytes(files: List[Tuple[str, bytes]]) -> bytes:
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in files:
            zf.writestr(name, data)
    mem.seek(0)
    return mem.read()

# =====================
# UI: CARTÃO DO GRÁFICO
# =====================
def plot_card(counter: Counter, titulo: str, key: str, exports: Dict[str, bytes]):
    fig = figura_pareto_horizontal(counter, titulo, largura_rotulo=24, ampliado=False)

    config = {
        "displayModeBar": True,
        "scrollZoom": True,
        "responsive": True,
        "toImageButtonOptions": {"format": "png", "filename": titulo, "height": 1080, "width": 1920, "scale": 2},
    }

    st.plotly_chart(fig, use_container_width=True, config=config, key=f"plot_{key}")

    # Download individual
    fname, data = fig_to_png_bytes(fig, filename=titulo, width=1920, height=1080, scale=2)
    exports[fname] = data
    st.download_button(
        "⬇️ Baixar este gráfico (PNG)",
        data=data,
        file_name=fname,
        mime="image/png",
        key=f"dl_{key}"
    )

    # Ampliar (compatível com 1.25.0: usa checkbox)
    expand = st.checkbox("Ampliar", key=f"amp_{key}")
    if expand:
        fig_big = figura_pareto_horizontal(counter, titulo, largura_rotulo=26, ampliado=True)
        st.plotly_chart(fig_big, use_container_width=True, config=config, key=f"plot_big_{key}")

# =====================
# URL DA PLANILHA
# =====================
URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSKwCflZovzD_0UAlLsDplKqWz2-WKs3agK-HaDQFmT6jx9RkkUAXNbUJvsD622uqUWTpXUTQ8XgILV/pub?output=csv"

# =====================
# CARREGAR DADOS E RENDERIZAR
# =====================
df = carregar_planilha_google_sheets(URL_GOOGLE_SHEETS)

# Toolbar (canto superior direito) – o botão ZIP aparece após gerar os gráficos
toolbar = st.container()

if df is not None:
    st.success("✅ Planilha carregada com sucesso.")
    st.caption(f"Linhas carregadas: {len(df)}")

    perguntas = df.columns[1:8]  # ajuste se precisar

    # onde acumulamos os arquivos exportados
    exports: Dict[str, bytes] = {}

    # grade 2 x N
    for i in range(0, len(perguntas), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(perguntas):
                col_raw = perguntas[i + j]
                titulo = f"{i + j + 1}) {remove_prefixo_numerico(col_raw)}"
                counter = contar_respostas_multipla(df, col_raw)
                with cols[j]:
                    plot_card(counter, titulo, key=f"{i}_{j}", exports=exports)

    # botão ZIP no topo direito
    if exports:
        files = list(exports.items())
        zip_data = zip_bytes(files)
        with toolbar:
            c1, c2 = st.columns([6, 1])
            with c2:
                st.download_button(
                    "⬇️ Baixar todas (ZIP)",
                    data=zip_data,
                    file_name="graficos_pareto.zip",
                    mime="application/zip",
                    key="dl_all_zip",
                    help="Exporta todos os gráficos em PNG (1920x1080) para uso no PowerPoint."
                )
        st.markdown('<p class="tip">Dica: títulos e rótulos foram dimensionados para leitura em sala.</p>',
                    unsafe_allow_html=True)
else:
    st.error("❌ Não foi possível carregar os dados da planilha.")
