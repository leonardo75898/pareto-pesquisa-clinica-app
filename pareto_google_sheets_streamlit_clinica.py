# app.py
import json
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
.stMarkdown img { width: 100% !important; }
button.btn-sm {
  padding:.45rem .8rem; border:0; border-radius:.55rem; background:#0e1117; color:#fff; cursor:pointer;
}
button.btn-ghost {
  padding:.45rem .8rem; border:1px solid #ddd; border-radius:.55rem; background:#fff; color:#111; cursor:pointer;
}
.modal-backdrop {
  display:none; position:fixed; inset:0; background:rgba(0,0,0,.7); z-index:9999; align-items:center; justify-content:center;
}
.modal-card {
  background:#fff; padding:12px; border-radius:12px; width: min(96vw, 1200px);
  box-shadow: 0 10px 30px rgba(0,0,0,.25);
}
.modal-head {
  display:flex; justify-content:space-between; align-items:center; gap:1rem; margin-bottom:.5rem;
}
.modal-head h3 { margin:0; font: 600 18px/1.3 system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
</style>
""", unsafe_allow_html=True)

# (opcional) botão para tentar paisagem em mobile
st.components.v1.html("""
<div style="margin:.5rem 0 1rem 0;">
  <button id="landBtn" style="padding:.6rem 1rem;border:0;border-radius:.6rem;background:#0e1117;color:#fff;cursor:pointer;">
    📱 Otimizar para celular (paisagem)
  </button>
  <span id="landMsg" style="margin-left:.5rem;color:#666;"></span>
</div>
<script>
const btn = document.getElementById('landBtn');
const msg = document.getElementById('landMsg');
btn?.addEventListener('click', async () => {
  try {
    const el = document.documentElement;
    if (el.requestFullscreen) await el.requestFullscreen();
    if (screen.orientation && screen.orientation.lock) {
      await screen.orientation.lock('landscape');
      msg.textContent = 'Modo paisagem solicitado ✔️';
    } else {
      msg.textContent = 'Seu navegador não permite bloquear orientação.';
    }
  } catch(e) {
    msg.textContent = 'Não foi possível ativar paisagem automaticamente.';
  }
});
</script>
""", height=80)

# =====================
# FUNÇÕES AUXILIARES
# =====================
def slugify(texto: str) -> str:
    s = re.sub(r"\s+", "_", texto.strip())
    s = re.sub(r"[^\w\-_.()]+", "", s, flags=re.UNICODE)
    return s.lower()

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
        fig.update_layout(margin=dict(l=20,r=20,t=80,b=20), height=360)
        return fig

    labels, valores = zip(*counter.most_common())
    totais = np.array(valores, dtype=float)
    acumulado = np.cumsum(totais)
    p_acum = 100 * acumulado / acumulado[-1]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=list(labels), y=list(totais), name="Frequência"), secondary_y=False)
    fig.add_trace(go.Scatter(x=list(labels), y=list(p_acum), mode="lines+markers", name="% Acumulado"), secondary_y=True)
    fig.add_hline(y=80, line_dash="dash", line_color="gray", secondary_y=True)

    fig.update_yaxes(title_text="Frequência", secondary_y=False)
    fig.update_yaxes(title_text="% Acumulado", range=[0,110], secondary_y=True)
    fig.update_xaxes(tickangle=45)

    # TÍTULO no alto
    fig.update_layout(
        title={"text": titulo, "x": 0.5, "y": 0.98, "xanchor": "center", "yanchor": "top"},
        margin=dict(l=20, r=20, t=90, b=40),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig

def render_plotly_with_modal(fig, titulo: str, filename: str, key: str, height: int = 380):
    """Renderiza o gráfico Plotly + botões (Ampliar/Download) 100% no cliente, sem Kaleido."""
    fig_dict = fig.to_dict()
    html = f"""
<div id="wrap-{key}">
  <div id="chart-{key}" style="width:100%;height:{height}px;"></div>
  <div style="display:flex;gap:.5rem;margin:.4rem 0;">
    <button class="btn-sm" onclick="open_{key}()">Ampliar</button>
    <button class="btn-ghost" onclick="download_{key}(false)">Baixar PNG (2K)</button>
  </div>
</div>

<div id="modal-{key}" class="modal-backdrop">
  <div class="modal-card">
    <div class="modal-head">
      <h3>{titulo}</h3>
      <div style="display:flex;gap:.5rem;">
        <button class="btn-ghost" onclick="download_{key}(true)">Baixar PNG (2K)</button>
        <button class="btn-sm" onclick="close_{key}()">Fechar</button>
      </div>
    </div>
    <div id="chart-big-{key}" style="width:100%; height:72vh;"></div>
  </div>
</div>

<script>
(function(){{
  function ensurePlotly(cb){{
    if (window.Plotly) return cb();
    var s = document.createElement('script');
    s.src = 'https://cdn.plot.ly/plotly-2.30.0.min.js';
    s.onload = cb;
    document.head.appendChild(s);
  }}

  const fig = {json.dumps(fig_dict)};
  const filename = {json.dumps(filename)};
  const conf = {{displayModeBar:true, responsive:true, scrollZoom:true}};

  function render(){{
    const gd = document.getElementById("chart-{key}");
    Plotly.newPlot(gd, fig.data, fig.layout, conf);
    window.addEventListener("resize", ()=>Plotly.Plots.resize(gd));
  }}

  window.open_{key} = function(){{
    const m = document.getElementById("modal-{key}");
    m.style.display = "flex";
    const gdb = document.getElementById("chart-big-{key}");
    const layoutBig = JSON.parse(JSON.stringify(fig.layout || {{}}));
    layoutBig.height = Math.round(window.innerHeight*0.72);
    Plotly.newPlot(gdb, fig.data, layoutBig, conf);
    window.addEventListener("resize", ()=>Plotly.Plots.resize(gdb));
  }};

  window.close_{key} = function(){{
    document.getElementById("modal-{key}").style.display = "none";
  }};

  window.download_{key} = function(big){{
    const id = big ? "chart-big-{key}" : "chart-{key}";
    const gd = document.getElementById(id);
    Plotly.downloadImage(gd, {{
      format: "png",
      filename: filename,
      width: 1920,
      height: 1080,
      scale: 1
    }});
  }};

  ensurePlotly(render);
}})();
</script>
"""
    st.components.v1.html(html, height=height+90)

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
                coluna = perguntas[i + j]
                titulo = f"{i + j + 1}) {coluna}"
                contador = contar_respostas_multipla(df, coluna)
                fig = criar_figura_pareto_plotly(contador, titulo)

                with cols[j]:
                    render_plotly_with_modal(
                        fig=fig,
                        titulo=titulo,
                        filename=slugify(titulo),
                        key=f"g{i}_{j}",
                        height=380
                    )
else:
    st.error("❌ Não foi possível carregar os dados da planilha.")
