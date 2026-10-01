# =====================================================================
# GEMEO DIGITAL - DISJUNTOR DE ALTA TENSAO (Ficha B8, foco termico)
# Rede hospedeira: UEA-4 Barras (rede_hospedeira.py, template oficial)
# Camada 3 (dados): curva_carga_24h.csv + curva_de_carga_24h_sobrecarga.csv + vcb_sensor_data.csv
# =====================================================================
import os
import pandas as pd
import pandapower as pp

from rede_hospedeira import criar_rede
from disjuntor_termico import diagnosticar, DELTA_THETA_REF_K, N_EXP, THETA_LIMITE_C

LINHA_DISJUNTOR = "LT-138 B1-B2"

def carregar_cenarios(caminho_csv):
    df = pd.read_csv(caminho_csv)
    esperadas = {"hora", "fator_carga", "temp_ambiente_C", "vento_m_s"}
    faltando = esperadas - set(df.columns)
    if faltando:
        raise ValueError(f"CSV '{caminho_csv}' sem as colunas esperadas: {faltando}")
    return df

def rodar_gemeo(cenarios: pd.DataFrame, delta_ambiente_C: float = 0.0, tag: str = "BASE"):
    """Roda simulacao orientada por curva de carga de 24h."""
    net = criar_rede()
    idx_linha = net.line.index[net.line.name == LINHA_DISJUNTOR][0]
    i_nominal_ka = net.line.max_i_ka[idx_linha]

    linhas_resultado = []
    for _, row in cenarios.iterrows():
        h = int(row["hora"])
        net.load.scaling = row["fator_carga"]
        theta_amb = row["temp_ambiente_C"] + delta_ambiente_C

        pp.runpp(net, algorithm="nr")

        i_ka = net.res_line.i_ka[idx_linha]
        diag = diagnosticar(i_ka, i_nominal_ka, theta_amb)

        linhas_resultado.append({
            "cenario": tag,
            "hora": h,
            "fator_carga": row["fator_carga"],
            "vento_m_s": row.get("vento_m_s", 1.0),
            "v_min_pu": net.res_bus.vm_pu.min(),
            "v_max_pu": net.res_bus.vm_pu.max(),
            "trafo_carreg_pct": net.res_trafo.loading_percent.iloc[0],
            "perdas_MW": net.res_line.pl_mw.sum() + net.res_trafo.pl_mw.sum(),
            **diag,
        })

    return pd.DataFrame(linhas_resultado), i_nominal_ka


def resumo_alarmes(tab: pd.DataFrame, tag: str):
    alarmes = tab[tab["alarme_temperatura"]]
    print(f"\n===== CENARIO: {tag} =====")
    print(f"Registros com hotspot acima do limite ({THETA_LIMITE_C:.0f} C): {len(alarmes)} de {len(tab)}")
    if len(alarmes):
        cols = ["hora", "theta_ambiente_C", "carregamento_pct", "theta_hotspot_C", "causa_dominante"]
        print(alarmes[cols].head(10).to_string(index=False))
    print("\nDistribuicao da causa dominante:")
    print(tab["causa_dominante"].value_counts().to_string())


if __name__ == "__main__":
    tabelas = []

    # 1. Curva Típica Padrão (curva_carga_24h.csv)
    try:
        cenarios_base = carregar_cenarios("curva_carga_24h.csv")
        tab_base, i_nom = rodar_gemeo(cenarios_base, delta_ambiente_C=0.0, tag="DIA TIPICO (curva_carga)")
        resumo_alarmes(tab_base, "DIA TIPICO (curva_carga)")
        tabelas.append(tab_base)

        tab_calor, _ = rodar_gemeo(cenarios_base, delta_ambiente_C=8.0, tag="CALOR EXTREMO (+8 C)")
        resumo_alarmes(tab_calor, "CALOR EXTREMO (+8 C)")
        tabelas.append(tab_calor)
    except FileNotFoundError:
        print("[ALERTA] curva_carga_24h.csv nao encontrado.")

    # 2. Curva Dedicada de Sobrecarga (curva_de_carga_24h_sobrecarga.csv)
    cenarios_sobrecarga = carregar_cenarios("curva_de_carga_24h_sobrecarga.csv")
    tab_sobrecarga, i_nom = rodar_gemeo(cenarios_sobrecarga, delta_ambiente_C=0.0, tag="SOBRECARGA SEVERA (24H)")
    resumo_alarmes(tab_sobrecarga, "SOBRECARGA SEVERA (24H)")
    tabelas.append(tab_sobrecarga)

    # Consolida e salva todos os resultados
    resultados = pd.concat(tabelas, ignore_index=True)
    resultados.to_csv("resultados_disjuntor.csv", index=False)
    print("\nResultados consolidados salvos em 'resultados_disjuntor.csv'.")