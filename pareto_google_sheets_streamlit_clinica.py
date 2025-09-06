# app.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter
import streamlit as st

# =====================
# CONFIGURAÇÃO INICIAL
# =====================
st.set_page_config(layout="wide", page_title="Gráficos de Pareto")

st.title("📊 Gráficos de Pareto")
st.caption("Fonte: Respostas da planilha do Google Sheets (atualiza em tempo real)")

# =====================
# FUNÇÕES AUXILIARES
# =====================

def carregar_planilha_google_sheets(url):
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

        df = pd.read_csv(csv_url)
        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

def contar_respostas_multipla(df, coluna):
    todas_respostas = []
    for resposta in df[coluna].dropna():
        opcoes = [op.strip() for op in str(resposta).split(",")]
        todas_respostas.extend(opcoes)
    return Counter(todas_respostas)

def criar_figura_pareto(counter, titulo):
    if not counter:
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.text(0.5, 0.5, "Sem dados para exibir", ha="center", va="center")
        ax.axis("off")
        fig.suptitle(titulo, fontsize=14)
        fig.tight_layout()
        return fig

    labels, valores = zip(*counter.most_common())
    totais = np.array(valores, dtype=float)
    acumulado = np.cumsum(totais)
    porcentagem_acumulada = 100 * acumulado / acumulado[-1]

    fig, ax1 = plt.subplots(figsize=(8, 3))
    ax1.bar(labels, totais, color="cornflowerblue")
    ax1.set_ylabel("Frequência")
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)

    ax2 = ax1.twinx()
    ax2.plot(range(len(labels)), porcentagem_acumulada, marker="o", linewidth=1.5, color="red")
    ax2.axhline(80, color="gray", linestyle="--", linewidth=1)
    ax2.set_ylabel("% Acumulado")
    ax2.set_ylim(0, 110)

    fig.suptitle(titulo, fontsize=14)
    fig.tight_layout()
    return fig

# =====================
# URL FIXA DA PLANILHA (ALTERE AQUI)
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

    for i, coluna in enumerate(perguntas, start=1):
        contador = contar_respostas_multipla(df, coluna)
        fig = criar_figura_pareto(contador, f"{i}) {coluna}")

        st.markdown(f"### {i}) {coluna}")
        st.pyplot(fig)
        st.markdown("---")
else:
    st.error("❌ Não foi possível carregar os dados da planilha.")
