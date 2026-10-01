# =====================================================================
# PAINEL INTERATIVO (Camada 5) - Gêmeo Digital do Disjuntor de AT
# Executar com:  streamlit run painel_disjuntor.py
# =====================================================================
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from disjuntor_termico import THETA_LIMITE_C, LIMIAR_AMBIENTE_C

st.set_page_config(page_title="Gêmeo Digital - Disjuntor AT", layout="wide")

st.title("Gêmeo Digital - Disjuntor de Alta Tensão (Ficha B8)")
st.caption("Rede Hospedeira UEA-4 Barras | LT-138 B1-B2 protegendo TR-01")

# 1. Carregamento do dataset gerado pelo Gêmeo Digital
try:
    tab = pd.read_csv("resultados_disjuntor.csv")
except FileNotFoundError:
    st.error("Arquivo `resultados_disjuntor.csv` não encontrado! Execute primeiro: `python3 gemeo_dt_disjuntor.py`")
    st.stop()

# ---------------------------------------------------------------------
# 2. SELEÇÃO DE CENÁRIO E NAVEGAÇÃO TEMPORAL
# ---------------------------------------------------------------------
cenario = st.selectbox("Selecione o Cenário de Análise", sorted(tab["cenario"].unique()))
dados = tab[tab["cenario"] == cenario].reset_index(drop=True)

# Captura de clique via estado do componente Plotly no Streamlit
if "grafico_temp" in st.session_state and st.session_state.grafico_temp:
    selecao = st.session_state.grafico_temp.get("selection", {})
    pontos = selecao.get("points", [])
    if pontos:
        hora_clicada = int(pontos[0].get("x"))
        if hora_clicada in dados["hora"].values:
            st.session_state.hora_selecionada = hora_clicada

# Inicialização da hora selecionada
if "hora_selecionada" not in st.session_state:
    st.session_state.hora_selecionada = int(dados["hora"].min())

if st.session_state.hora_selecionada not in dados["hora"].values:
    st.session_state.hora_selecionada = int(dados["hora"].min())

hora_atual = st.session_state.hora_selecionada

# ---------------------------------------------------------------------
# 5. STATUS OPERACIONAL E MÉTRICAS
# ---------------------------------------------------------------------
linha = dados[dados["hora"] == st.session_state.hora_selecionada].iloc[0]

mapa_status = {
    "NORMAL": (
        "🟢 NORMAL",
        "Operação Segura",
        "Corrente e temperatura ambiente dentro das especificações nominais de projeto.",
        "success"
    ),
    "SOBRECARGA": (
        "🟠 ALERTA: SOBRECARGA",
        "Sobrecarga Elétrica",
        "Elevação de temperatura causada por corrente superior à nominal (I > I_nom).",
        "warning"
    ),
    "AMBIENTE": (
        "🟡 ALERTA: AMBIENTE",
        "Estresse Térmico Ambiental",
        "Temperatura ambiente elevada (≥ 33 °C), reduzindo a capacidade de dissipação de calor.",
        "warning"
    ),
    "AMBOS (ambiente quente + sobrecarga)": (
        "🔴 CRÍTICO: SOBRECARGA + AMBIENTE",
        "Condição Crítica Combinada",
        "Combinação perigosa de sobrecarga elétrica e alta temperatura ambiente. Risco iminente de sobreaquecimento!",
        "error"
    )
}

causa_origem = linha["causa_dominante"]
status_badge, status_titulo, status_desc, status_estilo = mapa_status.get(
    causa_origem, (causa_origem, "Status do Disjuntor", "Análise operacional do modelo.", "info")
)

st.divider()
st.subheader(f"Estado Operacional às {int(linha['hora']):02d}:00h")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    label="Corrente no Disjuntor",
    value=f"{linha['i_ka']*1000:.0f} A",
    delta=f"{linha['carregamento_pct']:.1f}% de I_nom",
    delta_color="inverse" if linha['carregamento_pct'] > 100 else "normal"
)

c2.metric(
    label="Temp. Ambiente",
    value=f"{linha['theta_ambiente_C']:.1f} °C",
    delta="Ambiente Quente (≥ 33 °C)" if linha['theta_ambiente_C'] >= LIMIAR_AMBIENTE_C else "Normal (< 33 °C)",
    delta_color="inverse" if linha['theta_ambiente_C'] >= LIMIAR_AMBIENTE_C else "off"
)

c3.metric(
    label="Temp. Ponto Quente (Hotspot)",
    value=f"{linha['theta_hotspot_C']:.1f} °C",
    delta=f"{linha['theta_hotspot_C'] - THETA_LIMITE_C:+.1f} °C vs Limite",
    delta_color="inverse" if linha['theta_hotspot_C'] > THETA_LIMITE_C else "normal"
)

c4.metric(
    label="Status Operacional",
    value=status_badge
)

# ---------------------------------------------------------------------
# 3. GRÁFICO TÉRMICO INTERATIVO (PLOTLY)
# ---------------------------------------------------------------------
st.subheader("Perfil Térmico em 24 Horas")
#st.caption("Clique diretamente sobre qualquer ponto da linha/marcador para selecionar a hora.")

fig = go.Figure()

# Temp. Ambiente
fig.add_trace(go.Scatter(
    x=dados["hora"],
    y=dados["theta_ambiente_C"],
    mode="lines+markers",
    name="Temp. Ambiente (°C)",
    line=dict(color="#29b6f6", width=2),
    marker=dict(size=10, symbol="circle")
))

# Hotspot do Disjuntor
fig.add_trace(go.Scatter(
    x=dados["hora"],
    y=dados["theta_hotspot_C"],
    mode="lines+markers",
    name="Hotspot do Disjuntor (°C)",
    line=dict(color="#ff7043", width=3),
    marker=dict(size=11, symbol="diamond")
))

# Limite Normativo IEC 62271-1 (105 °C)
fig.add_trace(go.Scatter(
    x=[dados["hora"].min(), dados["hora"].max()],
    y=[THETA_LIMITE_C, THETA_LIMITE_C],
    mode="lines",
    name=f"Limite Normativo ({THETA_LIMITE_C:.0f} °C)",
    line=dict(color="#ef5350", width=2, dash="dot")
))

# Linha vertical do marcador atual
fig.add_vline(
    x=hora_atual,
    line_width=3,
    line_dash="solid",
    line_color="#ffd54f",
    annotation_text=f" Selecionado: {hora_atual:02d}:00h",
    annotation_position="top left"
)

fig.update_layout(
    xaxis=dict(title="Hora do Dia (h)", tickmode="linear", tick0=0, dtick=1),
    yaxis=dict(title="Temperatura (°C)"),
    hovermode="x unified",
    clickmode="event+select",
    height=380,
    margin=dict(l=20, r=20, t=30, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

# Renderização com a nova sintaxe width="stretch"
st.plotly_chart(
    fig,
    width="stretch",
    on_select="rerun",
    selection_mode="points",
    key="grafico_temp"
)

# ---------------------------------------------------------------------
# 4. BARRAS E CONTROLES DE LINHA DO TEMPO
# ---------------------------------------------------------------------

#col_b1, col_b2, col_b3, col_b4 = st.columns([1, 1, 1, 3])
#
#with col_b1:
#    if st.button("⏪ -1 Hora", width="stretch", disabled=(hora_atual == 0)):
#        st.session_state.hora_selecionada = max(0, hora_atual - 1)
#        st.rerun()
#
#with col_b2:
#    if st.button("⏩ +1 Hora", width="stretch", disabled=(hora_atual == 23)):
#        st.session_state.hora_selecionada = min(23, hora_atual + 1)
#        st.rerun()
#
#with col_b3:
#    hora_pico = int(dados.loc[dados["theta_hotspot_C"].idxmax(), "hora"])
#    if st.button(f"🔥 Pico ({hora_pico:02d}:00h)", width="stretch"):
#        st.session_state.hora_selecionada = hora_pico
#        st.rerun()

seletor_hora = st.slider(
    "Selecione a hora pela barra deslizante:",
    min_value=0,
    max_value=23,
    value=hora_atual,
    format="%d:00h",
    key="slider_tempo_direto"
)

if seletor_hora != st.session_state.hora_selecionada:
    st.session_state.hora_selecionada = seletor_hora
    st.rerun()



st.markdown("---")
col_alarme, col_diag = st.columns([1.2, 1.8])

with col_alarme:
    if linha["alarme_temperatura"]:
        st.error(f"**ALARME CRÍTICO DISPARADO!**\n\nHotspot ({linha['theta_hotspot_C']:.1f} °C) superou o limite normativo da IEC 62271-1 ({THETA_LIMITE_C:.0f} °C).")
    else:
        st.success(f"**Operação Dentro do Limite**\n\nHotspot em {linha['theta_hotspot_C']:.1f} °C (Limite Normativo: {THETA_LIMITE_C:.0f} °C).")

with col_diag:
    if status_estilo == "error":
        st.error(f"**{status_titulo}**\n\n{status_desc}")
    elif status_estilo == "warning":
        st.warning(f"**{status_titulo}**\n\n{status_desc}")
    else:
        st.info(f"**{status_titulo}**\n\n{status_desc}")

with st.expander("Guia de Interpretação dos Status Operacionais"):
    st.markdown("""
    | Status Operacional | Condição de Disparo | Ação / Diagnóstico |
    | :--- | :--- | :--- |
    | **🟢 NORMAL** | $I \le I_{nom}$ e $\theta_{amb} < 33^\circ\text{C}$ | Operação normal dentro da capacidade nominal contínua. |
    | **🟠 ALERTA: SOBRECARGA** | $I > I_{nom}$ e $\theta_{amb} < 33^\circ\text{C}$ | Perdas Joule elevadas. Avaliar alívio de carga na linha. |
    | **🟡 ALERTA: AMBIENTE** | $I \le I_{nom}$ e $\theta_{amb} \ge 33^\circ\text{C}$ | Capacidade de dissipação reduzida devido à elevada temperatura externa. |
    | **🔴 CRÍTICO: COMBINADO** | $I > I_{nom}$ e $\theta_{amb} \ge 33^\circ\text{C}$ | Estresse térmico duplo. Riscos de sobreaquecimento nos contatos. |
    """)