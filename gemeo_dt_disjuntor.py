# =====================================================================
# GEMEO DIGITAL - DISJUNTOR DE ALTA TENSAO (Ficha B8, foco termico)
# Rede hospedeira: UEA-4 Barras (rede_hospedeira.py, template oficial)
# Camada 3 (dados): curva_carga_24h.csv -> fator_carga, temp_ambiente_C
# Camada 4 (motor de calculo): fluxo de potencia (pandapower/NR) a cada
#           hora + modelo termico acoplado do disjuntor
# =====================================================================
import pandas as pd
import pandapower as pp

from rede_hospedeira import criar_rede
from disjuntor_termico import diagnosticar, DELTA_THETA_REF_K, N_EXP, THETA_LIMITE_C

# ---------------------------------------------------------------------
# Local do disjuntor na rede hospedeira: instalado no lado de 138 kV,
# em serie com a LT-138 B1-B2, protegendo o TR-01 (disjuntor de "alta
# tensao" propriamente dito). A corrente que passa pelo disjuntor e'
# portanto a corrente calculada para essa linha pelo fluxo de potencia.
# ---------------------------------------------------------------------
LINHA_DISJUNTOR = "LT-138 B1-B2"


def carregar_cenarios(caminho_csv="curva_carga_24h.csv"):
    df = pd.read_csv(caminho_csv)
    esperadas = {"hora", "fator_carga", "temp_ambiente_C", "vento_m_s"}
    faltando = esperadas - set(df.columns)
    if faltando:
        raise ValueError(f"CSV de cenarios sem as colunas: {faltando}")
    return df


def rodar_gemeo(cenarios: pd.DataFrame, delta_ambiente_C: float = 0.0, tag: str = "BASE"):
    """
    Executa o laco 'para cada hora: aplicar carga -> rodar fluxo ->
    diagnosticar o disjuntor' (Camada 4). delta_ambiente_C permite
    simular o cenario extraordinario 'dia de calor extremo' somando
    um offset a serie de temperatura ambiente sem alterar o CSV oficial.
    """
    net = criar_rede()
    idx_linha = net.line.index[net.line.name == LINHA_DISJUNTOR][0]
    i_nominal_ka = net.line.max_i_ka[idx_linha]  # ampacidade da linha = corrente nominal do disjuntor

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
            "vento_m_s": row["vento_m_s"],
            "v_min_pu": net.res_bus.vm_pu.min(),
            "v_max_pu": net.res_bus.vm_pu.max(),
            "trafo_carreg_pct": net.res_trafo.loading_percent.iloc[0],
            "perdas_MW": net.res_line.pl_mw.sum() + net.res_trafo.pl_mw.sum(),
            **diag,
        })

    return pd.DataFrame(linhas_resultado), i_nominal_ka


def validar_caso_base(net_builder=criar_rede):
    """Passo 3 da apostila: roda 1 fluxo (caso base, sem variacao de
    carga) e imprime as tensoes para conferencia manual."""
    net = net_builder()
    pp.runpp(net, algorithm="nr")
    print("\n===== VALIDACAO - CASO BASE (rede hospedeira, sem variacao) =====")
    tab = net.res_bus[["vm_pu", "va_degree"]].round(4)
    tab.index = net.bus.name
    print(tab)
    print("Convergiu:", net.converged)


def teste_sintetico_diagnostico(i_nominal_ka: float):
    """
    A rede UEA-4 barras e' pequena: mesmo na ponta, a LT-138 carrega
    so' ~11% de I_nominal, entao o cenario real nunca produz SOBRECARGA
    nem AMBOS. Este teste sintetico (nao e' um cenario da rede, e' um
    teste unitario do motor de diagnostico) injeta correntes/ambientes
    hipoteticos para provar que as 4 causas (NORMAL, AMBIENTE,
    SOBRECARGA, AMBOS) sao corretamente distinguidas antes de confiar
    no diagnostico nos cenarios reais.
    """
    casos = [
        ("NORMAL esperado",        i_nominal_ka * 0.50, 28.0),
        ("AMBIENTE esperado",      i_nominal_ka * 0.50, 38.0),
        ("SOBRECARGA esperado",    i_nominal_ka * 1.30, 28.0),
        ("AMBOS esperado",         i_nominal_ka * 1.30, 38.0),
    ]
    print("\n===== TESTE SINTETICO DO MOTOR DE DIAGNOSTICO (nao e' cenario real) =====")
    for nome, i_ka, theta_amb in casos:
        d = diagnosticar(i_ka, i_nominal_ka, theta_amb)
        print(f"{nome:22s} -> causa_dominante = {d['causa_dominante']:30s} "
              f"(I/Inom={i_ka/i_nominal_ka:.2f}, theta_amb={theta_amb:.0f}C, "
              f"hotspot={d['theta_hotspot_C']:.1f}C)")


def resumo_alarmes(tab: pd.DataFrame, tag: str):
    alarmes = tab[tab["alarme_temperatura"]]
    print(f"\n===== CENARIO: {tag} =====")
    print(f"Corrente nominal do disjuntor (I_nominal): usa a ampacidade da "
          f"linha '{LINHA_DISJUNTOR}' como referencia de placa.")
    print(f"Horas com hotspot acima do limite ({THETA_LIMITE_C:.0f} C): "
          f"{len(alarmes)} de {len(tab)}")
    if len(alarmes):
        print(alarmes[["hora", "theta_ambiente_C", "carregamento_pct",
                        "theta_hotspot_C", "causa_dominante"]].to_string(index=False))
    print("\nDistribuicao da causa dominante (todas as horas):")
    print(tab["causa_dominante"].value_counts().to_string())


if __name__ == "__main__":
    validar_caso_base()

    cenarios = carregar_cenarios("curva_carga_24h.csv")

    # Cenario 1: dia tipico (dados oficiais do CSV, sem alteracao)
    tab_base, i_nom = rodar_gemeo(cenarios, delta_ambiente_C=0.0, tag="DIA TIPICO")
    resumo_alarmes(tab_base, "DIA TIPICO")

    # Cenario 2 (extraordinario, previsto na Ata): dia de calor extremo
    # em Manaus -> soma-se um offset de +8 C a serie de temperatura
    # ambiente medida, mantendo a mesma curva de carga.
    tab_calor, _ = rodar_gemeo(cenarios, delta_ambiente_C=8.0, tag="CALOR EXTREMO (+8 C)")
    resumo_alarmes(tab_calor, "CALOR EXTREMO (+8 C)")

    resultados = pd.concat([tab_base, tab_calor], ignore_index=True)
    resultados.to_csv("resultados_disjuntor.csv", index=False)
    print(f"\nCorrente nominal (I_nominal) adotada para o disjuntor: {i_nom:.3f} kA")
    print(f"Elevacao de referencia a corrente nominal: {DELTA_THETA_REF_K:.0f} K "
          f"(expoente n={N_EXP})")
    print("\nResultados completos salvos em resultados_disjuntor.csv")

    teste_sintetico_diagnostico(i_nom)
