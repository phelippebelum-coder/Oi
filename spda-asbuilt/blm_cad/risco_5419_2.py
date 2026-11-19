"""Gerenciamento de risco - método da ABNT NBR 5419-2 (componentes RA...RZ, risco R1).

Tabelas e fórmulas conforme a ABNT NBR 5419-2:2015 (equivalente à IEC 62305-2:2010).
A edição 2026 (base IEC 62305-2:2024) altera o método (inclui frequência de dano F) e o NG:
os resultados daqui são de referência e devem ser conferidos com o texto vigente.

Uso: montar Estrutura + Linhas + Medidas e chamar avalia(); devolve dict com N, P, L, R por componente.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------- tabelas (NBR 5419-2:2015)
CD = {"cercada_mais_altos": 0.25, "cercada_mesma_altura": 0.5, "isolada": 1.0, "isolada_topo_colina": 2.0}
CI = {"aerea": 1.0, "enterrada": 0.5, "enterrada_malha": 0.01}
CT = {"bt_telecom": 1.0, "at_com_trafo": 0.2}
CE = {"rural": 1.0, "suburbano": 0.5, "urbano": 0.1, "urbano_edificios_20m": 0.01}
PB = {None: 1.0, "IV": 0.2, "III": 0.1, "II": 0.05, "I": 0.02}
PSPD = {None: 1.0, "III-IV": 0.05, "II": 0.02, "I": 0.01, "I+": 0.005, "I++": 0.001}
PEB = PSPD
PTA = {None: 1.0, "avisos": 0.1, "isolacao_descida": 0.01, "equip_solo": 0.01}
PTU = {None: 1.0, "avisos": 0.1, "isolacao": 0.01}
KS3 = {"sem_cuidado": 1.0, "evita_grandes_lacos": 0.2, "evita_lacos": 0.01, "blindado": 0.0001}
PLI = {"energia": {1.0: 1.0, 1.5: 0.6, 2.5: 0.3, 4.0: 0.16, 6.0: 0.1},
       "telecom": {1.0: 1.0, 1.5: 0.5, 2.5: 0.2, 4.0: 0.08, 6.0: 0.04}}
LT = 1e-2
LF = {"hospital_hotel_escola_civico": 1e-1, "entretenimento_igreja_museu": 5e-2,
      "industrial_comercial": 2e-2, "outros": 1e-2}
LO = {None: 0.0, "hospital_uti_centro_cirurgico": 1e-2, "hospital_outras_partes": 1e-3}
RT = {"agricola_concreto": 1e-2, "marmore_ceramica": 1e-3, "brita_carpete": 1e-4, "asfalto_madeira": 1e-5}
RP = {None: 1.0, "manual": 0.5, "automatica": 0.2}
RF = {"incendio_alto": 1e-1, "incendio_normal": 1e-2, "incendio_baixo": 1e-3, "nenhum": 0.0}
HZ = {"sem_perigo": 1, "panico_baixo": 2, "panico_medio": 5, "evacuacao_dificil": 5, "panico_alto": 10}
RISCO_TOLERAVEL_R1 = 1e-5


@dataclass
class Linha:
    nome: str
    tipo: str = "energia"            # energia | telecom
    instalacao: str = "enterrada"    # chave de CI
    ambiente: str = "urbano"         # chave de CE
    transformador: str = "bt_telecom"  # chave de CT
    LL: float = 1000.0               # m (1000 quando desconhecido)
    CLD: float = 1.0                 # linha não blindada
    CLI: float = 1.0
    PLD: float = 1.0
    adj: tuple | None = None         # (L, W, H, chave CD) da estrutura adjacente na outra ponta


@dataclass
class Estrutura:
    nome: str
    L: float
    W: float
    H: float
    localizacao: str = "cercada_mesma_altura"
    LF: str = "hospital_hotel_escola_civico"
    LO: str | None = "hospital_outras_partes"
    rt: str = "agricola_concreto"
    rp: str | None = "manual"
    rf: str = "incendio_normal"
    hz: str = "evacuacao_dificil"
    nz_nt: float = 1.0
    tz: float = 8760.0
    linhas: list = field(default_factory=list)


@dataclass
class Medidas:
    spda: str | None = None          # classe I..IV
    dps: str | None = None           # nível do sistema de DPS coordenados (PSPD)
    dps_entrada: str | None = None   # DPS na entrada das linhas (PEB)
    pta: str | None = None
    ptu: str | None = None
    ks3: str = "sem_cuidado"
    uw_kv: float = 1.5               # tensão suportável de impulso dos equipamentos
    ks1: float = 1.0
    ks2: float = 1.0


def area_AD(L, W, H):
    return L * W + 2 * 3 * H * (L + W) + math.pi * (3 * H) ** 2


def area_AM(L, W):
    return 2 * 500 * (L + W) + math.pi * 500 ** 2


def avalia(e: Estrutura, m: Medidas, NG: float):
    AD = area_AD(e.L, e.W, e.H)
    AM = area_AM(e.L, e.W)
    ND = NG * AD * CD[e.localizacao] * 1e-6
    NM = NG * AM * 1e-6
    fz = e.nz_nt * e.tz / 8760
    LA = LU = RT[e.rt] * LT * fz
    LB = LV = RP[e.rp] * RF[e.rf] * HZ[e.hz] * LF[e.LF] * fz
    Lo = LO[e.LO] * fz
    pb = PB[m.spda]
    pspd = PSPD[m.dps]
    peb = PEB[m.dps_entrada]
    PA = PTA[m.pta] * pb
    PC_tot = 0.0
    ks4 = 1.0 / m.uw_kv
    PMS = (m.ks1 * m.ks2 * KS3[m.ks3] * ks4) ** 2
    PM = pspd * PMS
    r = {"AD": AD, "AM": AM, "ND": ND, "NM": NM, "LA": LA, "LB": LB, "LO": Lo,
         "PA": PA, "PB": pb, "PM": PM, "PMS": PMS}
    RA = ND * PA * LA
    RB = ND * pb * LB
    # PC combinado das linhas: 1 - prod(1 - PCi)
    prod = 1.0
    RU = RV = RW = RZ = 0.0
    det_linhas = []
    for ln in e.linhas:
        AL = 40 * ln.LL
        AI = 4000 * ln.LL
        c = CI[ln.instalacao] * CE[ln.ambiente] * CT[ln.transformador]
        NL = NG * AL * c * 1e-6
        NI = NG * AI * c * 1e-6
        NDJ = 0.0
        if ln.adj:
            l2, w2, h2, loc = ln.adj
            NDJ = NG * area_AD(l2, w2, h2) * CD[loc] * CT[ln.transformador] * 1e-6
        PCi = pspd * ln.CLD
        prod *= (1 - PCi)
        PU = PTU[m.ptu] * peb * ln.PLD * ln.CLD
        PV = peb * ln.PLD * ln.CLD
        PW = pspd * ln.PLD * ln.CLD
        uw = min(PLI[ln.tipo], key=lambda k: abs(k - m.uw_kv))
        PZ = pspd * PLI[ln.tipo][uw] * ln.CLI
        ru = (NL + NDJ) * PU * LU
        rv = (NL + NDJ) * PV * LV
        rw = (NL + NDJ) * PW * Lo
        rz = NI * PZ * Lo
        RU += ru; RV += rv; RW += rw; RZ += rz
        det_linhas.append({"linha": ln.nome, "AL": AL, "AI": AI, "NL": NL, "NI": NI, "NDJ": NDJ,
                           "PU": PU, "PV": PV, "PW": PW, "PZ": PZ, "RU": ru, "RV": rv, "RW": rw, "RZ": rz})
    PC_tot = 1 - prod
    RC = ND * PC_tot * Lo
    RM = NM * PM * Lo
    r.update({"PC": PC_tot, "RA": RA, "RB": RB, "RC": RC, "RM": RM, "RU": RU, "RV": RV, "RW": RW, "RZ": RZ,
              "linhas": det_linhas})
    r["R1"] = RA + RB + RC + RM + RU + RV + RW + RZ
    r["atende"] = r["R1"] <= RISCO_TOLERAVEL_R1
    return r
