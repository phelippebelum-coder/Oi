"""Gera o as built de SPDA da Fundação Bradesco - Jd. Conceição (DXF + PDF + DWG).

Base: contornos traçados sobre a imagem aérea (sem planta do cliente).
Uso:  python gerar.py
"""
import argparse
import math
import pathlib
import sys

AQUI = pathlib.Path(__file__).parent
sys.path.insert(0, str(AQUI.parents[1]))

from ezdxf.enums import TextEntityAlignment  # noqa: E402

from blm_cad import folha  # noqa: E402
from blm_cad.geom import afasta_rotulos, centroide, fecha, proj_poli  # noqa: E402
import levantamento as L  # noqa: E402

C = TextEntityAlignment


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default=str(AQUI / "saida"))
    args = ap.parse_args()
    P = L.PROJETO
    s, H = P["m_por_px"], P["alt_img"]
    SF = P["escala"] / 500  # símbolos e textos proporcionais à escala da folha

    def m(x, y):
        return (x * s, (H - y) * s)

    doc = folha.novo_documento()
    msp = doc.modelspace()

    # ---------------- base (traçada da imagem aérea)
    pol = {k: fecha(e["poli"]) for k, e in L.EDIF.items()}
    for k, e in L.EDIF.items():
        msp.add_lwpolyline([m(*q) for q in pol[k]], close=True, dxfattribs={"layer": "ARQ-BASE", "lineweight": 35})
        for ln in e.get("linhas_internas", []):
            msp.add_lwpolyline([m(*q) for q in ln], dxfattribs={"layer": "ARQ-BASE", "lineweight": 13})
        txt = e["nome"] + (f"\\P{e['obs']}" if e.get("obs") else "")
        mt = msp.add_mtext(txt, dxfattribs={"layer": "SPDA-TEXTO", "style": folha.ESTILO,
                                             "char_height": 0.85 * SF * 2, "width": 24})
        mt.set_location(m(*e["rotulo"]), attachment_point=5)
    for chave in ("piso", "quadra"):
        msp.add_lwpolyline([m(*q) for q in L.QUADRA[chave]], close=True,
                           dxfattribs={"layer": "ARQ-BASE", "lineweight": 18 if chave == "quadra" else 13})
    for q, t in L.TEXTOS_BASE:
        folha.texto(msp, t, m(*q), 1.0 * SF * 2, "ARQ-BASE", C.MIDDLE_CENTER)

    resumo = {k: dict(desc=0, frank=0, mini=0) for k in list(L.EDIF) + ["QUADRA"]}

    # ---------------- gaiolas + minicaptores
    segs_gaiola = {}
    for k, e in L.EDIF.items():
        if not e.get("gaiola"):
            continue
        linhas = [pol[k]] + [list(l) for l in e.get("gaiola_internas", [])]
        segs_gaiola[k] = linhas
        msp.add_lwpolyline([m(*q) for q in pol[k]], close=True, dxfattribs={"layer": "SPDA-CAPTACAO-GAIOLA"})
        for ln in e.get("gaiola_internas", []):
            msp.add_lwpolyline([m(*q) for q in ln], dxfattribs={"layer": "SPDA-CAPTACAO-GAIOLA"})
    for x, y, k in L.MINICAPTORES:
        d, q = min((proj_poli((x, y), ln) for ln in segs_gaiola[k]), key=lambda r: r[0])
        folha.insere(msp, "BLM_MINICAPTOR", m(*(q if d < 10 else (x, y))), "SPDA-CAPTACAO-MINICAPTOR", SF * 1.8)
        resumo[k]["mini"] += 1

    # ---------------- captores Franklin (posição marcada)
    for x, y, k in L.FRANKLIN:
        folha.insere(msp, "BLM_FRANKLIN", m(x, y), "SPDA-CAPTACAO-FRANKLIN", SF * 1.4)
        resumo[k]["frank"] += 1

    # ---------------- descidas (projetadas na fachada) + numeração
    rot = []
    for n, (x, y, k) in enumerate(L.DESCIDAS, 1):
        d, q = proj_poli((x, y), pol[k])
        q = q if d < 14 else (x, y)
        xy = m(*q)
        folha.insere(msp, "BLM_DESCIDA", xy, "SPDA-DESCIDA", SF * 1.4)
        cx, cy = m(*centroide(pol[k]))
        vx, vy = xy[0] - cx, xy[1] - cy
        l = math.hypot(vx, vy) or 1
        rot.append([xy[0] + 3.2 * vx / l, xy[1] + 3.2 * vy / l, f"D{n:02d}"])
        resumo[k]["desc"] += 1
    for n, (x, y, k) in enumerate(L.DESCIDAS_ESTRUTURAIS, len(L.DESCIDAS) + 1):
        xy = m(x, y)
        folha.insere(msp, "BLM_DESCIDA_ESTRUTURAL", xy, "SPDA-DESCIDA", SF * 1.4)
        cx, cy = m(*centroide(pol[k]))
        vx, vy = xy[0] - cx, xy[1] - cy
        l = math.hypot(vx, vy) or 1
        rot.append([xy[0] + 3.2 * vx / l, xy[1] + 3.2 * vy / l, f"D{n:02d}"])
        resumo[k]["desc"] += 1
    afasta_rotulos(rot, 3.0, 1.4)
    for lx, ly, t in rot:
        folha.texto(msp, t, (lx, ly), 1.1 * SF * 2 * 0.5, "SPDA-DESCIDA-ID", C.MIDDLE_CENTER)

    # ---------------- quadros
    situ = {
        "A": "FRANKLIN + DESC. APARENTES", "B": "DESC. APARENTES", "C": "GAIOLA + DESC. ESTRUTURAIS",
        "D": "GAIOLA + DESC. ESTRUTURAIS", "E": "GAIOLA + DESC. ESTRUTURAIS", "QUADRA": "POSTES C/ FRANKLIN",
    }
    resumo_q = [["EDIFICAÇÃO", "DESC.", "FRANK.", "MINIC.", "SITUAÇÃO"]]
    tot = dict(desc=0, frank=0, mini=0)
    for k in list(L.EDIF) + ["QUADRA"]:
        r = resumo[k]
        for c in tot:
            tot[c] += r[c]
        nome = L.EDIF[k]["nome"] if k in L.EDIF else "QUADRA EXTERNA"
        resumo_q.append([nome, str(r["desc"]), str(r["frank"]), str(r["mini"]), situ[k]])
    resumo_q.append(["TOTAL", str(tot["desc"]), str(tot["frank"]), str(tot["mini"]), ""])
    ensaio_q = [["PONTO", "RESISTÊNCIA", "RESULTADO (REF. ≤ 200 mΩ)"]]
    for p, v in L.ENSAIO:
        if v is None:
            ensaio_q.append([str(p), "SEM LEITURA", "NÃO CONFORME - ATERRAMENTO NÃO CONSTATADO"])
        else:
            ensaio_q.append([str(p), f"{v:.1f} mΩ".replace(".", ","),
                             "CONFORME" if v <= L.LIMITE_MOHM else "NÃO CONFORME"])

    notas = [
        "DESENHO ELABORADO A PARTIR DE LEVANTAMENTO VISUAL EM CAMPO (14/11/2026) E IMAGEM AÉREA. NÃO HÁ "
        "PLANTA ARQUITETÔNICA DE BASE: CONTORNOS DAS EDIFICAÇÕES E ESCALA SÃO APROXIMADOS. CONFERIR "
        "MEDIDAS NA OBRA.",
        "POSIÇÕES DE CAPTORES FRANKLIN, MINICAPTORES, GAIOLAS E DESCIDAS CONFORME LEVANTAMENTO DE CAMPO.",
        "NOS BLOCOS C, D E E AS DESCIDAS SÃO NATURAIS (ARMADURA ESTRUTURAL), NÃO VISÍVEIS NO LEVANTAMENTO: "
        "POSIÇÃO INDICATIVA NAS EXTREMIDADES DOS BLOCOS. QUANTIDADE TOTAL DE DESCIDAS (16) CONFORME AS "
        "CONEXÕES DE ENSAIO REGISTRADAS NO RELATÓRIO BLM-SPDA-2026-004.",
        "CONDUTORES DE INTERLIGAÇÃO NA COBERTURA DO BLOCO A (ENTRE CAPTORES FRANKLIN E DESCIDAS) NÃO "
        "LEVANTADOS - NÃO REPRESENTADOS.",
        "DESCIDAS APARENTES EM CABO DE COBRE NU 35 mm² (LAUDO DE INSPEÇÃO DE 16/01/2026).",
        "ATERRAMENTO: ANEL DE ATERRAMENTO NÃO CONSTATADO (LAUDO DE 16/01/2026). NO PONTO 9 O ENSAIO NÃO "
        "APRESENTOU LEITURA NO LADO DO ATERRAMENTO (CIRCUITO ABERTO) - ADEQUAÇÃO PRIORITÁRIA.",
        "MANUTENÇÃO CORRETIVA EXECUTADA EM 11/2026: CONECTORES DA CAPTAÇÃO (C1 A C7) E DAS CONEXÕES DE "
        "ENSAIO SUBSTITUÍDOS COM PARAFUSARIA EM AÇO INOX; CAPTORES (A1 A A10 E DEMAIS) APRUMADOS E "
        "REFIXADOS - VER RELATÓRIO BLM-SPDA-2026-004.",
        "MANUTENÇÃO PREVENTIVA ANUAL. PRÓXIMA INSPEÇÃO ATÉ 14/11/2027.",
    ]
    legenda = [
        folha.ItemLegenda("bloco", "MINICAPTOR (TERMINAL AÉREO) NA GAIOLA", "BLM_MINICAPTOR",
                          "SPDA-CAPTACAO-MINICAPTOR"),
        folha.ItemLegenda("bloco", "CAPTOR FRANKLIN (NA COBERTURA OU EM POSTE)", "BLM_FRANKLIN",
                          "SPDA-CAPTACAO-FRANKLIN"),
        folha.ItemLegenda("bloco", "DESCIDA APARENTE EM CABO DE COBRE NU 35 mm² (Dxx = IDENTIFICAÇÃO)",
                          "BLM_DESCIDA", "SPDA-DESCIDA"),
        folha.ItemLegenda("bloco", "DESCIDA NATURAL/ESTRUTURAL (ARMADURA) - POSIÇÃO INDICATIVA",
                          "BLM_DESCIDA_ESTRUTURAL", "SPDA-DESCIDA"),
        folha.ItemLegenda("linha", "GAIOLA DE FARADAY - CONDUTOR DE CAPTAÇÃO", camada="SPDA-CAPTACAO-GAIOLA"),
        folha.ItemLegenda("linha", "CONTORNO DAS EDIFICAÇÕES (TRAÇADO DA IMAGEM AÉREA)", camada="ARQ-BASE"),
    ]

    jx0, jy1 = m(*P["janela_px"][:2])
    jx1, jy0 = m(*P["janela_px"][2:])
    car = folha.Carimbo(codigo=f"{P['codigo']}_R{int(P['revisao']):02d}", titulo=P["titulo"],
                        cliente=P["cliente"], escala=f"1:{P['escala']}", data=P["data"], revisao=P["revisao"],
                        folha=f"{P['formato']} - 01/01",
                        revisoes=[("0", P["data"], "EMISSÃO INICIAL - AS BUILT (CORRETIVA 2026)")])
    psp, vp = folha.prancha(
        doc, P["formato"], car, notas, legenda, None, (jx0, jy0, jx1, jy1), P["escala"], faixa_inferior=40,
        quadros_extra=[("QUADRO RESUMO - LEVANTAMENTO", resumo_q, [52, 18, 18, 18, 94], (0, 4)),
                       ("ENSAIO DE CONTINUIDADE - CORRETIVA 14/11/2026", ensaio_q, [22, 40, 138], (2,))],
        detalhes=(7, 2))
    W, Hf, me, mg = folha.FORMATOS[P["formato"]]
    folha.texto(psp, "IMPLANTAÇÃO - SPDA EXISTENTE (AS BUILT)", (me + 8, mg + 27), 5.0, "FOLHA-TITULO")
    folha.texto(psp, f"ESCALA 1:{P['escala']} (APROXIMADA - BASE TRAÇADA DE IMAGEM AÉREA)", (me + 8, mg + 20),
                3.0, "FOLHA-TEXTO")
    folha.escala_grafica(psp, me + 8, mg + 7, P["escala"], total_m=25, passo_m=5)
    xn = W - mg - 200 - 25
    rn_deg = P.get("rot_norte", 0)
    folha.insere(psp, "BLM_NORTE", (xn, mg + 20), "FOLHA-TEXTO", escala=7.0, rot=rn_deg)
    rn = math.radians(rn_deg + 90)
    folha.texto(psp, "N", (xn + 13.5 * math.cos(rn), mg + 20 + 13.5 * math.sin(rn)), 4.0, "FOLHA-TEXTO",
                C.MIDDLE_CENTER)

    out = pathlib.Path(args.saida); out.mkdir(parents=True, exist_ok=True)
    nome = f"{P['codigo']}_R{int(P['revisao']):02d}"
    doc.set_modelspace_vport(height=jy1 - jy0, center=((jx0 + jx1) / 2, (jy0 + jy1) / 2))
    doc.saveas(out / f"{nome}.dxf")
    folha.exporta_pdf(doc, psp.name, out / f"{nome}.pdf", P["formato"])
    dwg = folha.exporta_dwg(out / f"{nome}.dxf")
    print("ok:", out / f"{nome}.dxf", out / f"{nome}.pdf", dwg or "(sem DWG)")
    print("resumo:", tot)


if __name__ == "__main__":
    main()
