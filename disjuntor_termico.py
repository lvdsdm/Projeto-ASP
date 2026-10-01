# =====================================================================
# MODELO TERMICO DO DISJUNTOR DE ALTA TENSAO (Ficha B8 - foco termico)
# Projeto Gemeo Digital em SEP - ESTEEL0709 - 2026/2
# Equipe: Luiz Victor / Kevin Carlos / Matheus de Freitas
# =====================================================================
import math

# ---- Parametros de placa do disjuntor (IEC 62271-1) ------------------
THETA_REF_C = 40.0          # ambiente de referencia da norma (IEC 62271-1)
THETA_LIMITE_C = 105.0      # limite absoluto p/ contatos revestidos a prata
DELTA_THETA_REF_K = THETA_LIMITE_C - THETA_REF_C  # 65 K a corrente nominal
N_EXP = 1.6                 # expoente de perdas (conveccao + radiacao)

# Limiares de diagnostico
LIMIAR_AMBIENTE_C = 33.0    # acima disso, ambiente e' considerado "quente"
FATOR_SOBRECARGA = 1.00     # I/I_nominal > 1.0 => sobrecarga
LIMIAR_DESVIO_RESIDUO_C = 5.0  # desvio (em C) para alarme de degradacao de contato


def delta_theta(i_ka, i_nominal_ka, delta_ref_k=DELTA_THETA_REF_K, n=N_EXP):
    """Elevacao de temperatura (K) acima do ambiente, devido a carga."""
    razao = max(i_ka, 0.0) / i_nominal_ka if i_nominal_ka > 0 else 0.0
    return delta_ref_k * (razao ** n)


def diagnosticar(i_ka, i_nominal_ka, theta_ambiente_c, theta_medida_c=None):
    """
    Calcula a temperatura do ponto quente do disjuntor e compara com
    a telemetria real do sensor VCB (se disponivel).
    """
    d_theta = delta_theta(i_ka, i_nominal_ka)
    theta_hotspot = theta_ambiente_c + d_theta

    # Temperaturas hipoteticas para isolamento de causa raiz
    theta_so_carga = THETA_REF_C + d_theta
    theta_so_ambiente = theta_ambiente_c + delta_theta(i_nominal_ka, i_nominal_ka)

    razao_carga = i_ka / i_nominal_ka if i_nominal_ka > 0 else 0.0
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

    # Diagnostico comparativo com sensor
    residuo = None
    alerta_degradacao = False
    if theta_medida_c is not None and not (isinstance(theta_medida_c, float) and math.isnan(theta_medida_c)):
        residuo = theta_medida_c - theta_hotspot
        if residuo > LIMIAR_DESVIO_RESIDUO_C:
            alerta_degradacao = True

    return {
        "i_ka": i_ka,
        "carregamento_pct": 100.0 * razao_carga,
        "theta_ambiente_C": theta_ambiente_c,
        "delta_theta_K": d_theta,
        "theta_hotspot_C": theta_hotspot,
        "theta_so_carga_C": theta_so_carga,
        "theta_so_ambiente_C": theta_so_ambiente,
        "theta_medida_C": theta_medida_c,
        "residuo_C": residuo,
        "alerta_degradacao": alerta_degradacao,
        "causa_dominante": causa,
        "alarme_temperatura": violacao,
    }