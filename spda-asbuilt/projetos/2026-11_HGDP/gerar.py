"""Gera o as built de SPDA do HGDP (DXF + PDF).

Uso:  python gerar.py --base /caminho/HGDP-Imp_1.500.pdf [--base-dwg /caminho/HGDP-Imp_1.500.dwg]

--base      PDF vetorial da implantação: é sobre ele que o levantamento foi marcado (coordenadas em pt).
--base-dwg  DWG/DXF do cliente (opcional): a base arquitetônica passa a vir do DWG, nas coordenadas
            do DWG (metros reais). O levantamento é convertido PDF -> DWG por mínimos quadrados
            sobre os cantos das edificações; sem esta opção a base é a do PDF.
"""
import argparse
import math
import pathlib
import sys

AQUI = pathlib.Path(__file__).parent
sys.path.insert(0, str(AQUI.parents[1]))

from ezdxf.enums import TextEntityAlignment  # noqa: E402

from blm_cad import folha  # noqa: E402
from blm_cad.base_dwg import BaseDWG, ajusta_por_contornos  # noqa: E402
from blm_cad.base_pdf import BasePDF  # noqa: E402
import levantamento as L  # noqa: E402


# ---------------------------------------------------------------- geometria (pt)
def maior_poli(polis):
    return max(polis, key=lambda p: sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1)))


def anel(polis, tol=0.6):
    """Encadeia as polilinhas de um contorno (pontas coincidentes) num anel único."""
    resto = [list(p) for p in polis if len(p) > 1]
    if not resto:
        return []
    resto.sort(key=lambda p: -sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1)))
    r = resto.pop(0)
    while resto:
        melhor = None
        for i, p in enumerate(resto):
            for inv in (False, True):
                q = p[::-1] if inv else p
                d = math.dist(r[-1], q[0])
                if melhor is None or d < melhor[0]:
                    melhor = (d, i, q)
        if melhor[0] > tol:
            break
        r.extend(melhor[2][1:])
        resto.pop(melhor[1])
    return r


def fecha(p):
    return p if math.dist(p[0], p[-1]) < 0.5 else p + [p[0]]


def proj_seg(p, a, b):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy or 1e-9
    t = max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    q = (ax + t * dx, ay + t * dy)
    return math.dist(p, q), q


def proj_poli(p, poli):
    return min((proj_seg(p, poli[i], poli[i + 1]) for i in range(len(poli) - 1)), key=lambda r: r[0])


def dentro(p, poli):
    x, y = p; c = False
    for i in range(len(poli) - 1):
        (x1, y1), (x2, y2) = poli[i], poli[i + 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            c = not c
    return c


def centroide(poli):
    xs = [q[0] for q in poli[:-1]]; ys = [q[1] for q in poli[:-1]]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def reamostra(poli, n):
    segs = [(poli[i], poli[i + 1], math.dist(poli[i], poli[i + 1])) for i in range(len(poli) - 1)]
    total = sum(s[2] for s in segs)
    out, passo = [], total / n
    for k in range(n):
        alvo, acc = (k + 0.5) * passo, 0
        for a, b, l in segs:
            if acc + l >= alvo:
                t = (alvo - acc) / (l or 1)
                out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
                break
            acc += l
    return out


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="PDF vetorial da implantação (referência do levantamento)")
    ap.add_argument("--base-dwg", help="DWG/DXF do cliente: usa como base arquitetônica no lugar do PDF")
    ap.add_argument("--saida", default=str(AQUI / "saida"))
    args = ap.parse_args()
    P = L.PROJETO
    base = BasePDF(args.base, P["escala"])
    doc = folha.novo_documento()
    msp = doc.modelspace()

    # contornos das edificações (pt do PDF) -> gaiolas e projeção das descidas
    cont = {}
    for chave, e in {**L.EDIF, **L.SEM_SPDA}.items():
        cont[chave] = fecha(anel([q for i in e["paths"] for q in base.contorno(i)]))

    if args.base_dwg:
        # base do DWG, desenhada nas coordenadas do próprio DWG; levantamento (pt) -> DWG
        dwg = BaseDWG(args.base_dwg, L.CAMADAS_DWG)
        T, rel = ajusta_por_contornos({c: [base.m(*q) for q in p] for c, p in cont.items()},
                                      dwg.polilinhas(L.CAMADA_PREDIOS_DWG))
        print(f"ajuste PDF->DWG: {T}")
        print(f"  {rel['n']} pontos homólogos | resíduo RMS {rel['rms']:.3f} m | médio {rel['media']:.3f} m "
              f"| máx {rel['max']:.3f} m | contornos sem par: {rel['sem_par'] or 'nenhum'}")
        if rel["rms"] > 0.5 or rel["sem_par"]:
            raise SystemExit("Ajuste PDF->DWG ruim (resíduo > 0,5 m ou edificação sem par): conferir a base")

        def xy_m(x, y):
            return T(base.m(x, y))
    else:
        xy_m = base.m

    def ret_m(r):
        """Retângulo em pt (x0, y0, x1, y1; y para baixo) -> metros no modelo (xmin, ymin, xmax, ymax)."""
        (ax, ay), (bx, by) = xy_m(r[0], r[1]), xy_m(r[2], r[3])
        return (min(ax, bx), min(ay, by), max(ax, bx), max(ay, by))

    if args.base_dwg:
        n = dwg.desenha(msp, "ARQ-BASE", ret_m(P["janela_pt"]), excluir=[ret_m(r) for r in P["excluir_pt"]],
                        estilo=folha.ESTILO, pesos=L.PESOS_DWG)
        print("base DWG:", ", ".join(f"{v} {k}" for k, v in sorted(n.items())))
    else:
        nb = base.desenha(msp, "ARQ-BASE", P["janela_pt"], P["excluir_pt"])
        nt = base.desenha_textos(msp, "ARQ-BASE", P["janela_pt"], folha.ESTILO, P["excluir_pt"])
        print("base PDF:", nb, "polilinhas,", nt, "textos")

    def edif_mais_proxima(p, chaves):
        return min(chaves, key=lambda c: (0 if dentro(p, cont[c]) else 1, proj_poli(p, cont[c])[0]))

    # --- gaiola + minicaptores
    resumo = {c: dict(desc=0, frank=0, mini=0) for c in L.EDIF}
    for c, e in L.EDIF.items():
        poli = cont[c]
        if e.get("gaiola", True) and e["mini"] > 0:
            msp.add_lwpolyline([xy_m(*q) for q in poli], close=True,
                               dxfattribs={"layer": "SPDA-CAPTACAO-GAIOLA"})
            for q in reamostra(poli, e["mini"]):
                folha.insere(msp, "BLM_MINICAPTOR", xy_m(*q), "SPDA-CAPTACAO-MINICAPTOR")
            resumo[c]["mini"] += e["mini"]
        for q in e.get("pontos_mini", []):
            folha.insere(msp, "BLM_MINICAPTOR", xy_m(*q), "SPDA-CAPTACAO-MINICAPTOR")
            resumo[c]["mini"] += 1

    # --- descidas: projeta na fachada mais próxima, numera por edificação (sentido horário)
    por_edif = {c: [] for c in L.EDIF}
    for p in L.DESCIDAS:
        c = edif_mais_proxima(p, [k for k, e in L.EDIF.items() if e.get("aceita_descidas", True)])
        d, q = proj_poli(p, cont[c])
        por_edif[c].append(q if d < 40 else p)
    desc_m, rotulos = [], []
    n = 0
    for c in L.EDIF:
        cx, cy = centroide(cont[c])
        pts = sorted(por_edif[c], key=lambda q: (math.degrees(math.atan2(q[1] - cy, q[0] - cx)) + 135) % 360)
        for q in pts:
            n += 1
            xy = xy_m(*q)
            desc_m.append(xy)
            folha.insere(msp, "BLM_DESCIDA", xy, "SPDA-DESCIDA")
            vx, vy = q[0] - cx, q[1] - cy
            l = math.hypot(vx, vy) or 1
            # rótulo para fora da edificação (em metros, y para cima)
            rotulos.append([xy[0] + 3.4 * vx / l, xy[1] - 3.4 * vy / l, f"D{n:02d}", xy])
            resumo[c]["desc"] += 1
    # afasta rótulos que se sobrepõem (relaxação simples)
    for _ in range(60):
        mexeu = False
        for i in range(len(rotulos)):
            for j in range(i + 1, len(rotulos)):
                a, b = rotulos[i], rotulos[j]
                dx, dy = b[0] - a[0], b[1] - a[1]
                LX, LY = 4.4, 1.9
                if abs(dx) < LX and abs(dy) < LY:
                    mexeu = True
                    if abs(dx) / LX > abs(dy) / LY:
                        s = 0.5 * (LX + 0.1 - abs(dx)) * (1 if dx >= 0 else -1)
                        a[0] -= s; b[0] += s
                    else:
                        s = 0.5 * (LY + 0.1 - abs(dy)) * (1 if dy >= 0 else -1)
                        a[1] -= s; b[1] += s
        if not mexeu:
            break
    for lx, ly, s, xy in rotulos:
        folha.texto(msp, s, (lx, ly), 1.1, "SPDA-DESCIDA-ID", TextEntityAlignment.MIDDLE_CENTER)
    print("descidas:", n)

    # --- captores Franklin
    nf = 0
    for p in L.FRANKLIN:
        c = edif_mais_proxima(p, list(L.EDIF))
        poli = cont[c]
        d, q = proj_poli(p, poli)
        alvo = q if (not dentro(p, poli) or d < 6) else p
        xy = xy_m(*alvo)
        # afasta de descida coincidente
        for dx, dy in desc_m:
            if math.dist(xy, (dx, dy)) < 1.9:
                cx, cy = xy_m(*centroide(poli))
                v = (cx - xy[0], cy - xy[1]); l = math.hypot(*v) or 1
                xy = (xy[0] + 2.0 * v[0] / l, xy[1] + 2.0 * v[1] / l)
        folha.insere(msp, "BLM_FRANKLIN", xy, "SPDA-CAPTACAO-FRANKLIN")
        resumo[c]["frank"] += 1
        nf += 1
    print("franklin:", nf)

    # --- sem SPDA
    for c, e in L.SEM_SPDA.items():
        poli = cont[c]
        h = msp.add_hatch(dxfattribs={"layer": "SPDA-SEM-SPDA"})
        h.set_pattern_fill("ANSI31", scale=0.35)
        h.paths.add_polyline_path([xy_m(*q) for q in poli], is_closed=True)
        cx, cy = xy_m(*centroide(poli))
        folha.texto(msp, "SEM SPDA", (cx, cy - 2.5), 1.6, "SPDA-SEM-SPDA", TextEntityAlignment.MIDDLE_CENTER)
    for q in L.COBERTURAS_SEM_SPDA:
        folha.texto(msp, "(SEM SPDA)", xy_m(*q), 0.9, "SPDA-SEM-SPDA", TextEntityAlignment.MIDDLE_LEFT)
    for q, s, h in L.TEXTOS:
        folha.texto(msp, s, xy_m(*q), h, "SPDA-TEXTO", TextEntityAlignment.MIDDLE_CENTER)

    # --- quadro resumo
    quadro = [["EDIFICAÇÃO", "DESCIDAS", "FRANKLIN", "MINICAPT.", "SITUAÇÃO"]]
    tot = dict(desc=0, frank=0, mini=0)
    for c, e in L.EDIF.items():
        r = resumo[c]
        for k in tot:
            tot[k] += r[k]
        quadro.append([e["nome"], str(r["desc"]), str(r["frank"]), str(r["mini"]),
                       e.get("situacao", "COM SPDA")])
    for c, e in L.SEM_SPDA.items():
        quadro.append([e["nome"], "-", "-", "-", "SEM SPDA"])
    quadro.append(["COBERTURAS (PASSARELAS)", "-", "-", "-", "SEM SPDA"])
    quadro.append(["TOTAL", str(tot["desc"]), str(tot["frank"]), str(tot["mini"]), ""])

    notas = [
        "DESENHO ELABORADO A PARTIR DE LEVANTAMENTO VISUAL EM CAMPO E IMAGENS AÉREAS, SOBRE A PLANTA "
        "DE IMPLANTAÇÃO FORNECIDA PELO CLIENTE (SANTA CASA DE SÃO PAULO - HGDP, 26/06/2002"
        + (", ARQUIVO DWG ORIGINAL, COORDENADAS DO CLIENTE" if args.base_dwg else ", ESC. 1:500")
        + "). CONFERIR MEDIDAS NA OBRA.",
        "POSIÇÕES DE DESCIDAS E CAPTORES FRANKLIN CONFORME LEVANTAMENTO DE CAMPO. MINICAPTORES "
        "REPRESENTADOS NO PERÍMETRO DA COBERTURA NA QUANTIDADE LEVANTADA; POSIÇÃO INDICATIVA.",
        "CAPTAÇÃO EXISTENTE: CAPTORES FRANKLIN E GAIOLA DE FARADAY EM BARRA CHATA DE ALUMÍNIO, COM "
        "CAPTAÇÃO NATURAL POR CHAPAS METÁLICAS (LAUDO BLM DE 11/10/2024). CONDUTORES DA MALHA INTERNA "
        "DAS COBERTURAS NÃO LEVANTADOS - REPRESENTADO APENAS O PERÍMETRO.",
        "DESCIDAS APARENTES EM BARRA CHATA DE ALUMÍNIO.",
        "ATERRAMENTO EXISTENTE: HASTES COPPERWELD E MALHA EM CABO DE COBRE NU 50 mm² (LAUDO 2024). "
        "TRAÇADO DA MALHA ENTERRADA NÃO LEVANTADO - NÃO REPRESENTADO.",
        "EDIFICAÇÕES INDICADAS COMO \"SEM SPDA\" NÃO POSSUÍAM SISTEMA INSTALADO NA DATA DO LEVANTAMENTO. "
        "EDIFICAÇÕES SEM INDICAÇÃO NÃO FORAM OBJETO DESTE LEVANTAMENTO.",
        "TODAS AS MASSAS METÁLICAS EXPOSTAS NAS COBERTURAS DEVEM SER EQUIPOTENCIALIZADAS AO SPDA.",
        "O SISTEMA DEVERÁ TER MANUTENÇÃO PREVENTIVA ANUAL E INSPEÇÃO SEMPRE QUE ATINGIDO POR "
        "DESCARGAS ATMOSFÉRICAS.",
    ]
    legenda = [
        folha.ItemLegenda("bloco", "MINICAPTOR (TERMINAL AÉREO)", "BLM_MINICAPTOR", "SPDA-CAPTACAO-MINICAPTOR"),
        folha.ItemLegenda("bloco", "CAPTOR FRANKLIN EM HASTE/MASTRO", "BLM_FRANKLIN", "SPDA-CAPTACAO-FRANKLIN"),
        folha.ItemLegenda("bloco", "DESCIDA APARENTE EM BARRA CHATA DE ALUMÍNIO (Dxx = IDENTIFICAÇÃO)",
                          "BLM_DESCIDA", "SPDA-DESCIDA"),
        folha.ItemLegenda("linha", "CONDUTOR PERIMETRAL DA COBERTURA - GAIOLA DE FARADAY "
                          "(BARRA CHATA DE ALUMÍNIO)", camada="SPDA-CAPTACAO-GAIOLA"),
        folha.ItemLegenda("hachura", "EDIFICAÇÃO SEM SPDA", camada="SPDA-SEM-SPDA"),
        folha.ItemLegenda("linha", "BASE ARQUITETÔNICA (FORNECIDA PELO CLIENTE)", camada="ARQ-BASE"),
    ]

    jx0, jy0, jx1, jy1 = ret_m(P["janela_pt"])
    car = folha.Carimbo(codigo=f"{P['codigo']}_R{int(P['revisao']):02d}", titulo=P["titulo"],
                        cliente=P["cliente"], escala=f"1:{P['escala']}", data=P["data"],
                        revisao=P["revisao"], folha=f"{P['formato']} - 01/01",
                        revisoes=[("0", P["data"], "EMISSÃO INICIAL - AS BUILT")])
    psp, vp = folha.prancha(doc, P["formato"], car, notas, legenda, quadro,
                            (jx0, jy0, jx1, jy1), P["escala"], faixa_inferior=40,
                            detalhes=(1, 5))
    W, H, me, m = folha.FORMATOS[P["formato"]]
    folha.texto(psp, "IMPLANTAÇÃO GERAL - SPDA EXISTENTE (AS BUILT)", (me + 8, m + 27), 5.0, "FOLHA-TITULO")
    folha.texto(psp, f"ESCALA 1:{P['escala']}", (me + 8, m + 20), 3.0, "FOLHA-TEXTO")
    folha.escala_grafica(psp, me + 8, m + 7, P["escala"])
    # norte (conforme planta do cliente: norte para a esquerda da folha)
    xn = W - m - 200 - 25
    folha.insere(psp, "BLM_NORTE", (xn, m + 20), "FOLHA-TEXTO", escala=7.0, rot=P.get("rot_norte", 90))
    rn = math.radians(P.get("rot_norte", 90) + 90)
    folha.texto(psp, "N", (xn + 13.5 * math.cos(rn), m + 20 + 13.5 * math.sin(rn)), 4.0, "FOLHA-TEXTO",
                TextEntityAlignment.MIDDLE_CENTER)

    out = pathlib.Path(args.saida); out.mkdir(parents=True, exist_ok=True)
    nome = f"{P['codigo']}_R{int(P['revisao']):02d}"
    doc.set_modelspace_vport(height=jy1 - jy0, center=((jx0 + jx1) / 2, (jy0 + jy1) / 2))
    doc.saveas(out / f"{nome}.dxf")
    folha.exporta_pdf(doc, psp.name, out / f"{nome}.pdf", P["formato"])
    dwg = folha.exporta_dwg(out / f"{nome}.dxf")
    if dwg:
        print("dwg:", dwg)
    print("ok:", out / f"{nome}.dxf", out / f"{nome}.pdf")


if __name__ == "__main__":
    main()
