"""Calcula o gerenciamento de risco do HGDP e grava risco_resultados.json (insumo do documento)."""
import json, copy
from dados_risco import *
from blm_cad.risco_5419_2 import avalia, Medidas, RISCO_TOLERAVEL_R1, area_AD

SEM = Medidas()
ADOTADA = Medidas(spda="II", dps="I++", dps_entrada="I++", ks3="evita_grandes_lacos", uw_kv=1.5)
CRITICA = "U1522"

res = {"NG": NG_2026, "NG_2015": NG_2015, "RT": RISCO_TOLERAVEL_R1, "edificacoes": [], "medidas": vars(ADOTADA)}
for k, uso, e in estruturas():
    s = avalia(e, SEM, NG_2026); a = avalia(e, ADOTADA, NG_2026); a11 = avalia(e, ADOTADA, NG_2015)
    res["edificacoes"].append({"id": k, "nome": e.nome, "uso": CAT[uso][5], "L": e.L, "W": e.W, "H": e.H,
                               "rf": e.rf, "hz": e.hz, "LO": e.LO, "LF": e.LF,
                               "R1_sem": s["R1"], "R1_com": a["R1"], "R1_com_ng11": a11["R1"],
                               "atende": a["atende"]})
    if k == CRITICA:
        def limpa(r): return {x: y for x, y in r.items()}
        res["critica"] = {"id": k, "nome": e.nome, "L": e.L, "W": e.W, "H": e.H, "rf": e.rf, "hz": e.hz,
                          "sem": limpa(s), "com": limpa(a)}
cab = cabine_primaria()
res["cabine"] = {"sem": avalia(cab, SEM, NG_2026)["R1"], "com": avalia(cab, ADOTADA, NG_2026)["R1"]}
res["pior_com"] = max(res["edificacoes"], key=lambda d: d["R1_com"])
res["pior_sem"] = max(res["edificacoes"], key=lambda d: d["R1_sem"])
json.dump(res, open("risco_resultados.json", "w"), ensure_ascii=False, indent=1, default=float)
print("pior sem:", res["pior_sem"]["nome"], f'{res["pior_sem"]["R1_sem"]:.2e}')
print("pior com:", res["pior_com"]["nome"], f'{res["pior_com"]["R1_com"]:.2e}', "todas atendem:", all(d["atende"] for d in res["edificacoes"]))
