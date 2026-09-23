# =====================================================================
# MODELO TERMICO DO DISJUNTOR DE ALTA TENSAO (Ficha B8 - foco termico)
# Projeto Gemeo Digital em SEP - ESTEEL0709 - 2026/2
# Equipe: Luiz Victor / Kevin Carlos / Matheus de Freitas
#
# Pergunta central (Ata de Decisao):
#   "Como garantir que uma falha por suposto aumento de temperatura
#    realmente advem do ambiente e nao de sobrecarga, sem exceder a
#    temperatura limite?"
#
# MODELO FISICO (simplificado, adaptado do espirito da IEEE C57.91 e
# da IEC 62271-1 para contatos de disjuntores de AT):
#
#   theta_hotspot(t) = theta_ambiente(t) + delta_theta(I(t))
#
#   delta_theta(I) = delta_theta_ref * (I / I_nominal) ** n
#
# onde:
#   theta_ambiente(t) -> vem da "telemetria" (curva_carga_24h.csv)
#   I(t)               -> vem do fluxo de potencia (corrente na LT-138,
#                          onde o disjuntor esta instalado, protegendo
#                          o trafo TR-01)
#   delta_theta_ref     -> elevacao de temperatura nominal do disjuntor
#                          a corrente nominal (IEC 62271-1: contatos
#                          revestidos a prata -> limite absoluto 105 C
#                          com ambiente de referencia 40 C => elevacao
#                          admissivel de projeto = 65 K)
#   n                   -> expoente de perdas por conveccao/radiacao
#                          (adotado 1.6, mesmo raciocinio qualitativo
#                          do expoente m da IEEE C57.91 para
#                          transformadores; simplificacao assumida e
#                          declarada no documento do projeto)
#
# DECOMPOSICAO (o "coracao" da pergunta central):
#   O acrescimo total de temperatura em relacao ao limite e escrito
#   como soma de duas parcelas independentes:
#     parcela_ambiente = theta_ambiente(t) - theta_ref   (theta_ref=40C)
#     parcela_carga    = delta_theta(I(t))  - delta_theta_ref_a_Inom
#   Cada cenario e' entao classificado comparando essas parcelas com
#   seus proprios limiares -> AMBIENTE, SOBRECARGA, AMBOS ou NORMAL.
# =====================================================================

# ---- Parametros de placa do disjuntor (dados a obter -> valores
# ----  tipicos de catalogo para disjuntor de AT classe 145 kV,
# ----  usados como default ate a equipe confirmar a placa real) -----
THETA_REF_C = 40.0          # ambiente de referencia da norma (IEC 62271-1)
THETA_LIMITE_C = 105.0      # limite absoluto p/ contatos revestidos a prata
DELTA_THETA_REF_K = THETA_LIMITE_C - THETA_REF_C  # 65 K a corrente nominal
N_EXP = 1.6                 # expoente de perdas (conveccao+radiacao)

# Limiares de diagnostico (calibraveis; documentar no relatorio)
LIMIAR_AMBIENTE_C = 33.0    # acima disso, ambiente e' considerado "quente"
FATOR_SOBRECARGA = 1.00     # I/I_nominal > 1.0 => sobrecarga


def delta_theta(i_ka, i_nominal_ka, delta_ref_k=DELTA_THETA_REF_K, n=N_EXP):
    """Elevacao de temperatura (K) acima do ambiente, devido a carga."""
    razao = max(i_ka, 0.0) / i_nominal_ka
    return delta_ref_k * (razao ** n)


def diagnosticar(i_ka, i_nominal_ka, theta_ambiente_c):
    """
    Calcula a temperatura do ponto quente do disjuntor e devolve o
    diagnostico de causa raiz (ambiente x sobrecarga), respondendo
    diretamente a pergunta central do projeto.
    """
    d_theta = delta_theta(i_ka, i_nominal_ka)
    theta_hotspot = theta_ambiente_c + d_theta

    # temperatura hipotetica SE o ambiente estivesse na referencia (40C)
    # -> isola o efeito puro da carga
    theta_so_carga = THETA_REF_C + d_theta

    # temperatura hipotetica SE a corrente fosse exatamente a nominal
    # -> isola o efeito puro do ambiente
    theta_so_ambiente = theta_ambiente_c + delta_theta(i_nominal_ka, i_nominal_ka)

    razao_carga = i_ka / i_nominal_ka
    flag_ambiente = theta_ambiente_c >= LIMIAR_AMBIENTE_C
    flag_sobrecarga = razao_carga > FATOR_SOBRECARGA

    if flag_sobrecarga and flag_ambiente:
        causa = "AMBOS (ambiente quente + sobrecarga)"
    elif flag_sobrecarga:
        causa = "SOBRECARGA"
    elif flag_ambiente:
        causa = "AMBIENTE"
    else:
        causa = "NORMAL"

    violacao = theta_hotspot > THETA_LIMITE_C

    return {
        "i_ka": i_ka,
        "carregamento_pct": 100.0 * razao_carga,
        "theta_ambiente_C": theta_ambiente_c,
        "delta_theta_K": d_theta,
        "theta_hotspot_C": theta_hotspot,
        "theta_so_carga_C": theta_so_carga,
        "theta_so_ambiente_C": theta_so_ambiente,
        "causa_dominante": causa,
        "alarme_temperatura": violacao,
    }
