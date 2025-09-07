# app.py
import pandas as pd
import numpy as np
from collections import Counter
import streamlit as st
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# =====================
# CONFIGURAÇÃO INICIAL
# =====================
st.set_page_config(layout="wide", page_title="Gráficos de Pareto")
st.title("📊 Gráficos de Pareto")
st.caption("Fonte: Respostas da planilha do Google Sheets (atualiza em tempo real)")

# Pequeno CSS para ‘limpar’ margens em colunas e tornar imagens/iframes 100% largura
st.markdown("""
<style>
/* remove padding lateral excessivo nas colunas */
.block-container { padding-top: 1rem; padding-bottom: 2rem; }
[data-testid="column"] { padding: 0.25rem; }
/* garante que elementos visual ocupem toda a coluna */
.stPlotlyChart, .stImage, .stMarkdown img { width: 100% !important; }
</style>
""", unsafe_allow_html=True)

# ======================================
# BOTÃO: tentar orientar para paisagem
# (só funciona onde o navegador permitir)
# ======================================
st.components.v1.html("""
<div style="margin: .5rem 0 1rem 0;">
  <button id="landBtn" style="
    padding:.6rem 1rem;border:0;border-radius:.6rem;
    background:#0e1117;color:#fff;cursor:pointer;">
    📱 Otimizar para celular (paisagem)
  </button>
  <span id="landMsg" style="margin-left:.5rem;color:#666;"></span>
</div>
<script>
const btn = document.getElementById('landBtn');
const msg = document.getElementById('landMsg');
btn?.addEventListener('click', async () => {
  try {
    // Tenta full screen (exige gesto do usuário)
    const el = document.documentElement;
    if (el.requestFullscreen) await el.requestFullscreen();
    else if (el.webkitRequestFullscreen) await el.webkitRequestFullscreen();
    // Tenta travar paisagem (PWA/alguns Android)
    if (screen.orientation && screen.orientation.lock) {
      await screen.orientation.lock('landscape');
      msg.textContent = 'Modo paisagem solicitado ✔️';
    } else {
      msg.textContent = 'Seu navegador não permite bloquear orientação. Use o modo paisagem manualmente.';
    }
  } catch(e) {
    msg.textContent = 'Não foi possível ativar paisagem automaticamente. Gire o aparelho manualmente.';
  }
});
</script>
""", height=80)

# =====================
# FUNÇÕES AUXILIARES
# =====================
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

def criar_figura_pareto_plotly(counter: Counter, titulo: str):
    if not counter:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_annotation(text="Sem dados para exibir", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title=titulo, margin=dict(l=20,r=20,t=50,b=20), height=360)
        return fig

    labels, valores = zip(*counter.most_common())
    totais = np.array(valores, dtype=float)
    acumulado = np.cumsum(totais)
    p_acum = 100 * acumulado / acumulado[-1]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Barras (frequência)
    fig.add_trace(
        go.Bar(x=list(labels), y=list(totais), name="Frequência"),
        secondary_y=False
    )
    # Linha (% acumulado)
    fig.add_trace(
        go.Scatter(x=list(labels), y=list(p_acum), mode="lines+markers", name="% Acumulado"),
        secondary_y=True
    )
    # Linha 80/20
    fig.add_hline(y=80, line_dash="dash", line_color="gray", secondary_y=True)

    fig.update_yaxes(title_text="Frequência", secondary_y=False)
    fig.update_yaxes(title_text="% Acumulado", range=[0,110], secondary_y=True)
    fig.update_xaxes(tickangle=45)

    fig.update_layout(
        title=titulo,
        margin=dict(l=20, r=20, t=50, b=40),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig

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

    # Ajuste conforme suas colunas (1..7 perguntas)
    perguntas = df.columns[1:8]

    # Define se usamos 2 colunas (desktop) ou 1 (mobile).
    # Heurística simples: se a janela for estreita, role em 1 coluna.
    # Dica: o Streamlit já “quebra” para 1 coluna no mobile, mas este switch garante alturas adequadas.
    largura_aprox = st.get_option("browser.gatherUsageStats")  # só para ter uma chamada; não entrega width
    # Vamos sempre criar pares, o Streamlit no mobile empilha automaticamente.
    for i in range(0, len(perguntas), 2):
        colunas = st.columns(2)
        for j in range(2):
            if i + j < len(perguntas):
                coluna = perguntas[i + j]
                contador = contar_respostas_multipla(df, coluna)
                fig = criar_figura_pareto_plotly(contador, f"{i + j + 1}) {coluna}")
                with colunas[j]:
                    st.markdown(f"### {i + j + 1}) {coluna}")
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        config={
                            "displayModeBar": True,
                            "scrollZoom": True,      # pinch/scroll zoom em desktop e mobile
                            "responsive": True,
                        }
                    )

else:
    st.error("❌ Não foi possível carregar os dados da planilha.")
