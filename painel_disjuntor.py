# =====================================================================
# PAINEL (Camada 5) - Gemeo Digital do Disjuntor de AT (Ficha B8)
# Executar com:  streamlit run painel_disjuntor.py
# Pre-requisito: rodar antes  python3 gemeo_dt_disjuntor.py
#                (gera resultados_disjuntor.csv)
# =====================================================================
import pandas as pd
import streamlit as st

from disjuntor_termico import THETA_LIMITE_C, LIMIAR_AMBIENTE_C

st.set_page_config(page_title="Gemeo Digital - Disjuntor AT", layout="wide")
st.title("Gemeo Digital - Disjuntor de Alta Tensao (Ficha B8)")
st.caption("Rede hospedeira UEA-4 Barras | disjuntor na LT-138 B1-B2, protegendo o TR-01")

try:
    tab = pd.read_csv("resultados_disjuntor.csv")
except FileNotFoundError:
    st.error("resultados_disjuntor.csv nao encontrado. Rode antes: "
             "`python3 gemeo_dt_disjuntor.py`")
    st.stop()

cenario = st.selectbox("Cenario", sorted(tab["cenario"].unique()))
dados = tab[tab["cenario"] == cenario].sort_values("hora").reset_index(drop=True)

h = st.slider("Hora do dia", 0, 23, 12)
linha = dados[dados["hora"] == h].iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Corrente no disjuntor", f"{linha['i_ka']*1000:.0f} A",
            f"{linha['carregamento_pct']:.1f}% de I_nominal")
col2.metric("Temp. ambiente", f"{linha['theta_ambiente_C']:.1f} C")
col3.metric("Temp. ponto quente (hotspot)", f"{linha['theta_hotspot_C']:.1f} C",
            f"{linha['theta_hotspot_C'] - THETA_LIMITE_C:+.1f} C vs limite")
col4.metric("Causa dominante", linha["causa_dominante"])

if linha["alarme_temperatura"]:
    st.error(f"ALARME: hotspot ({linha['theta_hotspot_C']:.1f} C) acima do "
              f"limite normativo ({THETA_LIMITE_C:.0f} C)!")
else:
    st.success(f"Dentro do limite ({THETA_LIMITE_C:.0f} C).")

st.subheader("Perfil ao longo do dia")
st.line_chart(dados.set_index("hora")[["theta_ambiente_C", "theta_hotspot_C"]])

st.subheader("Decomposicao ambiente x carga (diagnostico da pergunta central)")
decomp = dados.set_index("hora")[["theta_so_carga_C", "theta_so_ambiente_C", "theta_hotspot_C"]]
decomp.columns = ["so' efeito da carga (amb=40C)", "so' efeito do ambiente (I=Inom)", "real (combinado)"]
st.line_chart(decomp)
st.caption(
    "Se a curva 'real' acompanha de perto a curva 'so' efeito do ambiente', o "
    "aquecimento daquele dia e' predominantemente climatico. Se acompanha a "
    "curva 'so' efeito da carga', e' predominantemente sobrecarga."
)

st.subheader("Causa dominante por hora")
st.bar_chart(dados["causa_dominante"].value_counts())

with st.expander("Premissas do modelo termico"):
    st.markdown(f"""
    - theta_hotspot(t) = theta_ambiente(t) + delta_theta(I(t))
    - delta_theta(I) = 65 K x (I / I_nominal) ^ 1.6  (IEC 62271-1: limite 105 C,
      ambiente de referencia 40 C, contatos revestidos a prata)
    - I_nominal adotado = ampacidade da LT-138 B1-B2 (0,60 kA)
    - Limiar de "ambiente quente": {LIMIAR_AMBIENTE_C:.0f} C
    - Estes valores sao defaults de catalogo e devem ser substituidos pela
      placa real do disjuntor escolhido pela equipe (Camada 1 / Materiais
      e Metodos).
    """)
