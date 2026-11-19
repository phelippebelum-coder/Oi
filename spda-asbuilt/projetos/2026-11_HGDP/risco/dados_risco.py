"""Dados de entrada do gerenciamento de risco - HGDP (NBR 5419-2).

Dimensões L x W: retângulo envolvente do contorno de cada edificação no DWG do cliente (m).
Alturas: estimadas pelas fotos do laudo 2024 (pavilhões com 2 pavimentos + telhado) [A CONFIRMAR].
"""
import json, pathlib, sys
AQUI = pathlib.Path(__file__).parent
sys.path.insert(0, str(AQUI.parents[2]))
from blm_cad.risco_5419_2 import Estrutura, Linha  # noqa: E402

NG_2026 = 20.0   # São Paulo - novo mapa NBR 5419:2026 (projeto 2025: 20) [A CONFIRMAR na tabela publicada]
NG_2015 = 11.0   # São Paulo - NBR 5419-2:2015

DIMS = json.load(open(AQUI / "dimensoes.json", encoding="utf-8"))

# Carga de incêndio (IT 14/2019 CBPMESP, Anexo A): hospitais em geral H-1/H-3 = 300 MJ/m²; asilos H-2 = 350 MJ/m²
#   -> < 400 MJ/m² = risco de incêndio BAIXO (rf = 1e-3, NBR 5419-2 tab. C.5). Demais usos: NORMAL (conservador).
RF_USO = {"internacao": "incendio_baixo", "hospitalar_dia": "incendio_baixo"}
# categoria: (H [m], LF, LO, hz, tz, descrição do uso)
CAT = {
    "internacao": (10.0, "hospital_hotel_escola_civico", "hospital_outras_partes", "evacuacao_dificil", 8760,
                   "Internação / hospitalar (pacientes 24 h)"),
    "hospitalar_dia": (10.0, "hospital_hotel_escola_civico", "hospital_outras_partes", "evacuacao_dificil", 8760,
                       "Apoio hospitalar (farmácia, ambulatório)"),
    "creche": (6.0, "hospital_hotel_escola_civico", None, "evacuacao_dificil", 8760, "Creche"),
    "capela": (12.0, "entretenimento_igreja_museu", None, "panico_baixo", 8760, "Capela"),
    "apoio": (8.0, "hospital_hotel_escola_civico", None, "panico_baixo", 8760, "Administrativo / apoio"),
    "portaria": (4.0, "hospital_hotel_escola_civico", None, "panico_baixo", 8760, "Portaria"),
}
USO = {
    "FARM": "hospitalar_dia", "RES": "internacao", "SESMT": "apoio", "U1920": "internacao", "U1617": "internacao",
    "U1314": "internacao", "U1112": "internacao", "U23": "internacao", "ADM": "apoio", "U1522": "internacao",
    "CAP": "capela", "U0708": "internacao", "U0506": "internacao", "U0304": "internacao", "U0102": "internacao",
    "U09": "internacao", "CRE": "creche", "PORT2": "portaria", "PORTE": "portaria", "PORTD": "portaria",
    "AMB": "hospitalar_dia", "CARP": "apoio", "SAL2": "apoio",
}
CABINE = (10.0, 6.0, 4.0, "cercada_mesma_altura")   # estrutura adjacente na ponta da linha BT [A CONFIRMAR]


def linhas_padrao():
    """Linhas que entram em cada edificação: energia BT e telecom, subterrâneas, a partir da cabine/rack."""
    return [Linha("Energia BT (subterrânea, da cabine primária)", "energia", "enterrada", "urbano", "bt_telecom",
                  1000.0, adj=CABINE),
            Linha("Telecom / dados (subterrânea)", "telecom", "enterrada", "urbano", "bt_telecom", 1000.0)]


def estruturas():
    out = []
    for k, uso in USO.items():
        d = DIMS[k]
        H, lf, lo, hz, tz, _ = CAT[uso]
        out.append((k, uso, Estrutura(d["nome"], d["L"], d["W"], H, "cercada_mesma_altura", lf, lo,
                                      "agricola_concreto", "manual", RF_USO.get(uso, "incendio_normal"), hz, 1.0, tz,
                                      linhas_padrao())))
    return out


def cabine_primaria():
    """Cabine primária: entrada aérea em 13,8 kV (linha AT com trafo AT/BT), ocupação eventual."""
    return Estrutura("CABINE PRIMÁRIA 13,8 kV", 10.0, 6.0, 4.0, "cercada_mesma_altura", "industrial_comercial",
                     None, "agricola_concreto", "manual", "incendio_normal", "sem_perigo", 1.0, 365.0,
                     [Linha("Entrada aérea 13,8 kV (Enel)", "energia", "aerea", "urbano", "at_com_trafo", 1000.0)])
