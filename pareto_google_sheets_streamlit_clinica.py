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

# CSS – melhora o topo no mobile e dá estilo ao modal/controles
st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 2rem; }
[data-testid="column"] { padding: 0.25rem; }

@media (max-width: 640px) {
  .block-container { padding-top: 3rem; }
  h1 { font-size: 1.6rem; line-height: 1.25; margin-top: .25rem; }
}

/* Botões */
.btn-sm{padding:.45rem .8rem;border:0;border-radius:.55rem;background:#0e1117;color:#fff;cursor:pointer;}
.btn-ghost{padding:.45rem .8rem;border:1px solid #ddd;border-radius:.55rem;background:#fff;color:#111;cursor:pointer;}

/* Modal HTML próprio (independente do Streamlit) */
.modal-backdrop{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;align-items:center;justify-content:center;}
.modal-card{background:#fff;padding:12px;border-radius:12px;width:min(96vw,1200px);box-shadow:0 10px 30px rgba(0,0,0,.25);}
.modal-head{display:flex;justify-content:space-between;align-items:center;gap:1rem;margin-bottom:.5rem;}
.modal-head h3{margin:0;font:600 18px/1.3 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;}
</style>
""", unsafe_allow_html=True)

# =====================
# UTILS
# =====================
def slugify(txt: str) -> str:
    s = re.sub(r"\s+", "_", str(txt).strip())
    s = re.sub(r"[^\w\-_.()]+", "", s)
    return s.lower()

def remove_prefixo_numerico(txt: str) -> str:
    return re.sub(r'^\s*\d+\)\s*', '', str(txt).strip())

def wrap_text_br(txt: str, max_chars: int = 18) -> str:
    """Quebra com <br> próximo de espaços (para rótulos do eixo X)."""
    palavras = str(txt).split()
    linhas, linha = [], ""
    for p in palavras:
        if len(linha) + len(p) + (1 if linha else 0) <= max_chars:
            linha = (linha + " " + p).strip()
        else:
            if linha: linhas.append(linha)
            linha = p
    if linha: linhas.append(linha)
    return "<br>".join(linhas)

# =====================
# DADOS
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

# =====================
# FIGURA (Plotly -> dict)
# =====================
def criar_figura_pareto_dict(counter: Counter, titulo: str):
    """Cria figura Plotly (dict) — título e fontes serão ajustados via JS conforme a largura."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.update_layout(template="plotly_white")

    if not counter:
        fig.add_annotation(text="Sem dados para exibir", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(margin=dict(l=60, r=30, t=130, b=120), height=420)
        return fig.to_dict()

    labels, valores = zip(*counter.most_common())
    totais = np.array(valores, dtype=float)
    p_acum = 100 * np.cumsum(totais) / totais.sum()

    # rótulos quebrados (x)
    labels_wrapped = [wrap_text_br(l, 18) for l in labels]

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

    fig.update_xaxes(
        tickmode="array", tickvals=list(labels), ticktext=labels_wrapped,
        automargin=True, ticklabelstandoff=10
    )
    fig.update_yaxes(title_text="Frequência", secondary_y=False, automargin=True)
    fig.update_yaxes(title_text="% Acumulado", range=[0,110], secondary_y=True, automargin=True)

    # título provisório (será refeito em JS com wrap dinâmico e fonte responsiva)
    fig.update_layout(
        title={"text": titulo, "x": 0.5, "y": 0.92, "xanchor": "center", "yanchor": "top",
               "font": {"size": 28}},
        margin=dict(l=60, r=30, t=130, b=120),
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="right", x=1,
                    font=dict(size=12)),
        bargap=0.25,
        font=dict(size=12)
    )
    return fig.to_dict()

# =====================
# RENDER (HTML/JS) – Sem modebar, botões externos, título responsivo
# =====================
def render_plotly_responsivo(counter: Counter, titulo: str, key: str):
    fig_dict = criar_figura_pareto_dict(counter, titulo)
    html = f"""
<div id="wrap-{key}">
  <div id="chart-{key}" style="width:100%;height:420px;"></div>
  <div style="display:flex;gap:.5rem;margin:.5rem 0 1rem 0;">
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

  const baseFig = {json.dumps(fig_dict)};
  const rawTitle = {json.dumps(titulo)};
  const filename = {json.dumps(slugify(titulo))};

  function wrapTitle(t, maxChars){{
    const words = String(t).trim().split(/\\s+/);
    const lines = []; let line = "";
    words.forEach(w => {{
      if ((line + " " + w).trim().length <= maxChars) {{
        line = (line + " " + w).trim();
      }} else {{
        if (line) lines.push(line);
        line = w;
      }}
    }});
    if (line) lines.push(line);
    return lines.join("<br>");
  }}

  function computeFont(w){{
    // escalona fontes conforme a largura do container
    const title = Math.max(16, Math.min(40, Math.round(w/18)));
    const tick  = Math.max(10, Math.min(14, Math.round(w/35)));
    const axis  = Math.max(12, Math.min(16, Math.round(w/28)));
    const leg   = Math.max(11, Math.min(14, Math.round(w/30)));
    return {{title, tick, axis, leg}};
  }}

  function render(id, big){{
    const gd = document.getElementById(id);
    const w  = gd.clientWidth || gd.parentElement.clientWidth || window.innerWidth;
    const f  = computeFont(w);
    const maxChars = w < 420 ? 26 : (w < 768 ? 34 : 48);

    const lay = JSON.parse(JSON.stringify(baseFig.layout || {{}}));
    lay.title = lay.title || {{}};
    lay.title.text = wrapTitle(rawTitle, maxChars);  // título com <br> dinâmico
    lay.title.font = {{size: f.title}};
    lay.margin = lay.margin || {{}};
    lay.margin.t = Math.max(110, Math.round(f.title * 3.2));  // mantém espaço SEMPRE acima do gráfico
    lay.height  = big ? Math.min(740, Math.round(window.innerHeight*0.72))
                      : Math.max(360, Math.round(w*0.62));

    lay.legend = Object.assign({{}}, lay.legend || {{}}, {{font: {{size: f.leg}}}});
    lay.xaxis  = Object.assign({{}}, lay.xaxis || {{}},  {{tickfont: {{size: f.tick}}, titlefont: {{size: f.axis}}}});
    lay.yaxis  = Object.assign({{}}, lay.yaxis || {{}},  {{tickfont: {{size: f.tick}}, titlefont: {{size: f.axis}}}});
    lay.yaxis2 = Object.assign({{}}, lay.yaxis2 || {{}}, {{tickfont: {{size: f.tick}}, titlefont: {{size: f.axis}}, range:[0,110]}});

    const conf = {{displayModeBar:false, responsive:true, scrollZoom:true}}; // SEM modebar → não sobrepõe o título
    Plotly.newPlot(gd, baseFig.data, lay, conf);

    // Responsividade em resize
    function onResize(){{
      const w2  = gd.clientWidth || gd.parentElement.clientWidth || window.innerWidth;
      const f2  = computeFont(w2);
      const mCh = w2 < 420 ? 26 : (w2 < 768 ? 34 : 48);
      Plotly.relayout(gd, {{
        'title.text': wrapTitle(rawTitle, mCh),
        'title.font.size': f2.title,
        'margin.t': Math.max(110, Math.round(f2.title*3.2)),
        'height': big ? Math.min(740, Math.round(window.innerHeight*0.72))
                      : Math.max(360, Math.round(w2*0.62)),
        'xaxis.tickfont.size': f2.tick, 'xaxis.titlefont.size': f2.axis,
        'yaxis.tickfont.size': f2.tick, 'yaxis.titlefont.size': f2.axis,
        'yaxis2.tickfont.size': f2.tick, 'yaxis2.titlefont.size': f2.axis
      }});
      Plotly.Plots.resize(gd);
    }}
    window.addEventListener('resize', onResize);
  }}

  // Ações dos botões
  window.open_{key} = function(){{
    const m = document.getElementById("modal-{key}");
    m.style.display = "flex";
    render("chart-big-{key}", true);
  }};
  window.close_{key} = function(){{
    document.getElementById("modal-{key}").style.display = "none";
  }};
  window.download_{key} = function(big){{
    const id = big ? "chart-big-{key}" : "chart-{key}";
    const gd = document.getElementById(id);
    // baixa SEM modebar, com resolução alta
    Plotly.downloadImage(gd, {{format:"png", filename:{json.dumps(slugify(titulo))}, width:2560, height:1440, scale:1}});
  }};

  ensurePlotly(()=>render("chart-{key}", false));
}})();
</script>
"""
    st.components.v1.html(html, height=520)

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

    perguntas = df.columns[1:8]  # ajuste conforme necessário

    for i in range(0, len(perguntas), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(perguntas):
                col_raw = perguntas[i + j]
                titulo = f"{i + j + 1}) {remove_prefixo_numerico(col_raw)}"
                contador = contar_respostas_multipla(df, col_raw)
                with cols[j]:
                    render_plotly_responsivo(contador, titulo, key=f"{i}_{j}")
else:
    st.error("❌ Não foi possível carregar os dados da planilha.")
