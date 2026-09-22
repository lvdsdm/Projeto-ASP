# =====================================================================
# REDE HOSPEDEIRA UEA-4 BARRAS - Template oficial do projeto
# Disciplina: Analise de Sistemas de Potencia I (ESTEEL0709) - 2026/2
# Prof. Dr. Israel Gondres Torne
# Requisitos: Python 3 + pandapower  (pip install pandapower)
# =====================================================================
import pandapower as pp
import pandas as pd

def criar_rede():
    net = pp.create_empty_network(sn_mva=100)  # base 100 MVA

    # ---- Barras -----------------------------------------------------
    b1 = pp.create_bus(net, vn_kv=138.0, name="B1 Rede Externa 138 kV")
    b2 = pp.create_bus(net, vn_kv=138.0, name="B2 SE AT 138 kV")
    b3 = pp.create_bus(net, vn_kv=13.8,  name="B3 SE MT 13,8 kV")
    b4 = pp.create_bus(net, vn_kv=13.8,  name="B4 Carga MT 13,8 kV")

    # ---- Rede externa (slack) ---------------------------------------
    pp.create_ext_grid(net, bus=b1, vm_pu=1.02, name="Equivalente 138 kV")

    # ---- Linha de transmissao 138 kV: B1 -> B2 (40 km) --------------
    pp.create_line_from_parameters(
        net, from_bus=b1, to_bus=b2, length_km=40.0,
        r_ohm_per_km=0.12, x_ohm_per_km=0.40, c_nf_per_km=9.5,
        max_i_ka=0.60, name="LT-138 B1-B2")

    # ---- Transformador 25 MVA 138/13,8 kV: B2 -> B3 -----------------
    pp.create_transformer_from_parameters(
        net, hv_bus=b2, lv_bus=b3, sn_mva=25.0,
        vn_hv_kv=138.0, vn_lv_kv=13.8,
        vk_percent=8.5, vkr_percent=0.5,
        pfe_kw=20.0, i0_percent=0.1, name="TR-01 25 MVA")

    # ---- Alimentador 13,8 kV: B3 -> B4 (5 km) -----------------------
    pp.create_line_from_parameters(
        net, from_bus=b3, to_bus=b4, length_km=5.0,
        r_ohm_per_km=0.40, x_ohm_per_km=0.35, c_nf_per_km=10.0,
        max_i_ka=0.40, name="AL-01 B3-B4")

    # ---- Cargas (caso base = ponta) ---------------------------------
    pp.create_load(net, bus=b3, p_mw=8.0, q_mvar=3.0, name="Carga B3")
    pp.create_load(net, bus=b4, p_mw=6.0, q_mvar=2.5, name="Carga B4")

    # ---- Banco de capacitores B4 (2 Mvar) - inicia DESLIGADO --------
    pp.create_shunt(net, bus=b4, q_mvar=-2.0, p_mw=0.0,
                    in_service=False, name="BC-01 2 Mvar")
    return net

def rodar(net, tag):
    pp.runpp(net, algorithm="nr")
    print(f"\n===== CASO: {tag} =====")
    vb = net.res_bus[["vm_pu", "va_degree"]].round(4)
    vb.index = net.bus.name
    print(vb)
    print("Trafo: carregamento = %.2f %%" % net.res_trafo.loading_percent.iloc[0])
    print("LT-138: carregamento = %.2f %% | AL-01: %.2f %%" %
          (net.res_line.loading_percent.iloc[0], net.res_line.loading_percent.iloc[1]))
    perdas = net.res_line.pl_mw.sum() + net.res_trafo.pl_mw.sum()
    print("Perdas totais = %.4f MW" % perdas)
    print("Slack: P = %.4f MW | Q = %.4f Mvar" %
          (net.res_ext_grid.p_mw.iloc[0], net.res_ext_grid.q_mvar.iloc[0]))
    return net

if __name__ == "__main__":
    # Caso 1: base (ponta), capacitor desligado
    net = criar_rede(); rodar(net, "BASE (ponta, BC desligado)")
    # Caso 2: base + capacitor ligado
    net = criar_rede(); net.shunt.in_service = True
    rodar(net, "BASE + BC-01 ligado")
    # Caso 3: carga leve (60% da ponta), BC desligado
    net = criar_rede(); net.load.scaling = 0.60
    rodar(net, "CARGA LEVE (60%)")
