"""Padrão de prancha BLM Engenharia para SPDA (DXF via ezdxf).

Tudo que é "identidade" da empresa fica aqui: camadas, cores, símbolos, carimbo,
legenda, notas-padrão e normas. Para atualizar norma, logo ou carimbo, mexa só
neste arquivo (e em assets/), e regenere os projetos.
"""
from __future__ import annotations

import json
import math
import pathlib
from dataclasses import dataclass, field

import ezdxf
from ezdxf import colors
from ezdxf.enums import TextEntityAlignment

AQUI = pathlib.Path(__file__).parent

# --------------------------------------------------------------------------
# Dados da empresa / normas  (ATUALIZAR AQUI)
# --------------------------------------------------------------------------
EMPRESA = {
    "nome": "BLM ENGENHARIA LTDA",
    "endereco": ["RUA SÃO LADISLAU, 37 - VILA PRADO", "CEP: 02558-050 - SÃO PAULO - SP",
                 "www.blmengenharia.com.br"],
    "resp_tecnico": "ENG. ELETRICISTA PHELIPPE BELUM CASTRO DIAS",
    "crea": "CREA-SP 5070878575",
}

NORMAS = [
    "ABNT NBR 5419-1:2026 - PROTEÇÃO CONTRA DESCARGAS ATMOSFÉRICAS - PRINCÍPIOS GERAIS",
    "ABNT NBR 5419-2:2026 - GERENCIAMENTO DE RISCO",
    "ABNT NBR 5419-3:2026 - DANOS FÍSICOS A ESTRUTURAS E PERIGOS À VIDA",
    "ABNT NBR 5419-4:2026 - SISTEMAS ELÉTRICOS E ELETRÔNICOS INTERNOS NA ESTRUTURA",
    "ABNT NBR 13571:2024 - HASTE DE ATERRAMENTO AÇO-COBRE",
    "ABNT NBR 16254:2024 - MATERIAIS PARA SISTEMA DE ATERRAMENTO",
    "ABNT NBR 5410:2004 (VERSÃO CORRIGIDA 2008) - INSTALAÇÕES ELÉTRICAS DE BAIXA TENSÃO",
    "NR-10 - SEGURANÇA EM INSTALAÇÕES E SERVIÇOS EM ELETRICIDADE",
]

# Formatos ABNT NBR 10068 (mm): largura, altura, margem esquerda, demais margens
FORMATOS = {
    "A0": (1189, 841, 25, 10),
    "A1": (841, 594, 25, 10),
    "A2": (594, 420, 25, 7),
    "A3": (420, 297, 25, 7),
}

# --------------------------------------------------------------------------
# Camadas e cores (true color: legível em fundo branco e preto)
# --------------------------------------------------------------------------
COR = {
    "base": (140, 140, 140),
    "gaiola": (232, 89, 12),
    "minicaptor": (47, 158, 68),
    "franklin": (47, 158, 68),
    "descida": (201, 42, 42),
    "texto": (28, 63, 148),
    "semspda": (201, 42, 42),
    "moldura": (0, 0, 0),
    "titulo": (28, 63, 148),
}

CAMADAS = {
    # nome: (cor, lineweight em 1/100 mm, linetype)
    "ARQ-BASE": (COR["base"], 13, "Continuous"),
    "SPDA-CAPTACAO-GAIOLA": (COR["gaiola"], 50, "Continuous"),
    "SPDA-CAPTACAO-MINICAPTOR": (COR["minicaptor"], 25, "Continuous"),
    "SPDA-CAPTACAO-FRANKLIN": (COR["franklin"], 25, "Continuous"),
    "SPDA-DESCIDA": (COR["descida"], 35, "Continuous"),
    "SPDA-DESCIDA-ID": (COR["descida"], 18, "Continuous"),
    "SPDA-SEM-SPDA": (COR["semspda"], 18, "Continuous"),
    "SPDA-TEXTO": (COR["texto"], 18, "Continuous"),
    "FOLHA-MOLDURA": (COR["moldura"], 50, "Continuous"),
    "FOLHA-LINHAS": (COR["moldura"], 18, "Continuous"),
    "FOLHA-TEXTO": ((0, 0, 0), 18, "Continuous"),
    "FOLHA-TITULO": (COR["titulo"], 25, "Continuous"),
    "FOLHA-LOGO": ((0, 0, 0), 0, "Continuous"),
    "VIEWPORT": ((0, 0, 0), 0, "Continuous"),
}

ESTILO = "BLM"


def novo_documento() -> ezdxf.document.Drawing:
    doc = ezdxf.new("R2018", setup=True, units=6)  # 6 = metros
    doc.header["$MEASUREMENT"] = 1
    doc.styles.add(ESTILO, font="arial.ttf")
    for nome, (rgb, lw, lt) in CAMADAS.items():
        ly = doc.layers.add(nome)
        ly.rgb = rgb
        ly.dxf.lineweight = lw
        ly.dxf.linetype = lt
    doc.layers.get("VIEWPORT").off()
    _cria_blocos(doc)
    return doc


# --------------------------------------------------------------------------
# Símbolos (unidade do bloco = metro de modelo; na folha 1:500, 1 m = 2 mm)
# --------------------------------------------------------------------------
R_MINI = 0.45
R_FRANK = 0.95
R_DESC = 0.85


def _cria_blocos(doc):
    b = doc.blocks.new("BLM_MINICAPTOR")
    b.add_circle((0, 0), R_MINI, dxfattribs={"layer": "0", "color": 0})

    b = doc.blocks.new("BLM_FRANKLIN")
    b.add_circle((0, 0), R_FRANK, dxfattribs={"layer": "0", "color": 0})
    for a0 in (0, 180):
        h = b.add_hatch(color=0, dxfattribs={"layer": "0"})
        pts = [(0, 0)] + [(R_FRANK * math.cos(math.radians(a0 + t)),
                           R_FRANK * math.sin(math.radians(a0 + t))) for t in range(0, 91, 10)]
        h.paths.add_polyline_path(pts, is_closed=True)

    b = doc.blocks.new("BLM_DESCIDA")
    b.add_circle((0, 0), R_DESC, dxfattribs={"layer": "0", "color": 0})
    h = b.add_hatch(color=0, dxfattribs={"layer": "0"})
    h.paths.add_polyline_path([(0.42 * math.cos(math.radians(t)), 0.42 * math.sin(math.radians(t)))
                               for t in range(0, 360, 20)], is_closed=True)
    # raio estilizado (seta de descida)
    b.add_lwpolyline([(R_DESC * 0.7, R_DESC * 0.7), (2.0, 1.2), (1.6, 2.0), (2.9, 2.6)],
                     dxfattribs={"layer": "0", "color": 0})

    b = doc.blocks.new("BLM_NORTE")
    b.add_circle((0, 0), 1.0, dxfattribs={"layer": "0", "color": 0})
    h = b.add_hatch(color=0, dxfattribs={"layer": "0"})
    h.paths.add_polyline_path([(0, 1.35), (0.35, -0.6), (0, -0.25), (-0.35, -0.6)], is_closed=True)


def insere(msp, bloco, xy, camada, escala=1.0, rot=0.0):
    return msp.add_blockref(bloco, xy, dxfattribs={"layer": camada, "xscale": escala,
                                                    "yscale": escala, "rotation": rot})


def texto(esp, s, xy, h, camada="FOLHA-TEXTO", alin=TextEntityAlignment.LEFT, rgb=None, larg=0.9):
    t = esp.add_text(s, height=h, dxfattribs={"layer": camada, "style": ESTILO, "width": larg})
    t.set_placement(xy, align=alin)
    if rgb:
        t.rgb = rgb
    return t


def mtexto(esp, s, xy, h, largura, camada="FOLHA-TEXTO", espac=1.0):
    m = esp.add_mtext(s, dxfattribs={"layer": camada, "style": ESTILO, "char_height": h,
                                      "width": largura, "line_spacing_factor": espac})
    m.set_location(xy, attachment_point=ezdxf.enums.MTextEntityAlignment.TOP_LEFT)
    return m


def linha(esp, a, b, camada="FOLHA-LINHAS"):
    esp.add_line(a, b, dxfattribs={"layer": camada})


def retangulo(esp, x0, y0, x1, y1, camada="FOLHA-LINHAS"):
    esp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True,
                       dxfattribs={"layer": camada})


def logo(esp, x, y, largura, camada="FOLHA-LOGO"):
    """Insere o logo vetorizado (hatch sólido) com canto inferior esquerdo em (x, y)."""
    dados = json.load(open(AQUI / "assets/logo_blm.json"))
    s = largura / dados["aspect"]
    for cam in dados["camadas"]:
        h = esp.add_hatch(dxfattribs={"layer": camada})
        h.rgb = tuple(cam["rgb"])
        for p in cam["polys"]:
            if len(p) >= 3:
                h.paths.add_polyline_path([(x + u * s, y + v * s) for u, v in p], is_closed=True)
    return s  # altura


# --------------------------------------------------------------------------
# Prancha
# --------------------------------------------------------------------------
@dataclass
class Carimbo:
    codigo: str
    titulo: list[str]
    cliente: list[str]
    escala: str
    data: str
    revisao: str = "0"
    folha: str = "01/01"
    des: str = "BLM"
    verif: str = ""
    aprov: str = "PHELIPPE"
    art: str = ""
    revisoes: list[tuple[str, str, str]] = field(default_factory=list)


@dataclass
class ItemLegenda:
    tipo: str          # "bloco" | "linha" | "hachura" | "texto"
    descricao: str
    bloco: str = ""
    camada: str = ""


def _barra(psp, x0, x1, y, titulo):
    """Faixa de título de seção; devolve o y de baixo."""
    linha(psp, (x0, y), (x1, y), "FOLHA-MOLDURA")
    texto(psp, titulo, ((x0 + x1) / 2, y - 3.6), 3.0, "FOLHA-TITULO", TextEntityAlignment.MIDDLE_CENTER)
    linha(psp, (x0, y - 7), (x1, y - 7), "FOLHA-MOLDURA")
    return y - 7


def prancha(doc, formato, carimbo: Carimbo, notas: list[str], legenda: list[ItemLegenda],
            quadro: list[list[str]] | None, janela_modelo, escala_den: int, nome_layout=None,
            larg_coluna=200, faixa_inferior=0.0, quadros_extra=()):
    """quadros_extra: [(titulo, linhas, larguras_relativas, colunas_alinhadas_a_esquerda)]"""
    """Cria o layout (paperspace) com moldura, coluna lateral BLM e viewport do modelo.

    janela_modelo = (xmin, ymin, xmax, ymax) em metros (modelo).
    """
    W, H, me, m = FORMATOS[formato]
    nome_layout = nome_layout or f"FOLHA {formato}"
    psp = doc.layouts.new(nome_layout)
    psp.page_setup(size=(W, H), margins=(0, 0, 0, 0), units="mm")
    for e in list(psp):
        psp.delete_entity(e)  # remove viewport padrão
    if "Layout1" in doc.layouts:
        doc.layouts.delete("Layout1")

    x0, y0, x1, y1 = me, m, W - m, H - m
    retangulo(psp, x0, y0, x1, y1, "FOLHA-MOLDURA")
    cx0 = x1 - larg_coluna
    linha(psp, (cx0, y0), (cx0, y1), "FOLHA-MOLDURA")

    # viewport
    jx0, jy0, jx1, jy1 = janela_modelo
    k = 1000 / escala_den  # mm de papel por metro
    vw, vh = (jx1 - jx0) * k, (jy1 - jy0) * k
    ax0, ax1, ay0, ay1 = x0, cx0, y0 + faixa_inferior, y1
    if faixa_inferior:
        linha(psp, (x0, ay0), (cx0, ay0), "FOLHA-MOLDURA")
    if vw > ax1 - ax0 + 0.01 or vh > ay1 - ay0 + 0.01:
        raise ValueError(f"Janela não cabe na folha {formato} 1:{escala_den}: {vw:.0f}x{vh:.0f} mm")
    vp = psp.add_viewport(center=((ax0 + ax1) / 2, (ay0 + ay1) / 2), size=(ax1 - ax0, ay1 - ay0),
                          view_center_point=((jx0 + jx1) / 2, (jy0 + jy1) / 2),
                          view_height=(ay1 - ay0) / k, dxfattribs={"layer": "VIEWPORT"})
    vp.dxf.status = 2
    try:
        vp.dxf.flags = vp.dxf.flags | 16384  # display locked
    except Exception:
        pass

    # escala gráfica + norte ficam a cargo do projeto (dependem do modelo)
    cl = cx0 + 3
    y = y1
    # --- normas
    y = _barra(psp, cx0, x1, y, "REFERÊNCIAS NORMATIVAS")
    yy = y - 4.2
    for n in NORMAS:
        texto(psp, n, (cl, yy), 2.3)
        yy -= 4.2
    y = yy - 1.5
    # --- notas
    y = _barra(psp, cx0, x1, y, "NOTAS")
    yy = y - 3
    hn = 2.4
    for i, n in enumerate(notas, 1):
        mtexto(psp, f"{i} - {n}", (cl, yy), hn, larg_coluna - 7)
        nlin = max(1, math.ceil((len(n) + 4) * hn * 0.86 / (larg_coluna - 9)))
        yy -= nlin * hn * 1.67 + 1.8
    y = yy - 1
    # --- legenda
    y = _barra(psp, cx0, x1, y, "LEGENDA (EXISTENTE - AS BUILT)")
    yy = y - 6
    for it in legenda:
        sx = cl + 8
        if it.tipo == "bloco":
            insere(psp, it.bloco, (sx, yy), it.camada, escala=3.0)
        elif it.tipo == "linha":
            psp.add_line((cl + 1, yy), (cl + 15, yy), dxfattribs={"layer": it.camada})
        elif it.tipo == "hachura":
            hh = psp.add_hatch(dxfattribs={"layer": it.camada})
            hh.set_pattern_fill("ANSI31", scale=0.6)
            hh.paths.add_polyline_path([(cl + 1, yy - 2.2), (cl + 15, yy - 2.2), (cl + 15, yy + 2.2),
                                        (cl + 1, yy + 2.2)], is_closed=True)
            retangulo(psp, cl + 1, yy - 2.2, cl + 15, yy + 2.2, it.camada)
        elif it.tipo == "texto":
            texto(psp, it.bloco, (sx, yy), 1.8, it.camada, TextEntityAlignment.MIDDLE_CENTER)
        mtexto(psp, it.descricao, (cl + 20, yy + 2.0), 2.4, larg_coluna - 26)
        nlin = max(1, math.ceil(len(it.descricao) * 2.4 * 0.78 / (larg_coluna - 27)))
        yy -= max(10.0, nlin * 4.0 + 5.0)
    y = yy + 2
    # --- quadros
    tabelas = []
    if quadro:
        tabelas.append(("QUADRO RESUMO - LEVANTAMENTO", quadro, [80, 21, 21, 23, 55], (0, 4)))
    tabelas.extend(quadros_extra)
    for titulo, linhas_q, larg, esq in tabelas:
        y = _barra(psp, cx0, x1, y, titulo)
        tot = sum(larg)
        cols = [cx0]
        for l in larg:
            cols.append(cols[-1] + l * larg_coluna / tot)
        hl = 5.2
        yy = y
        for i, row in enumerate(linhas_q):
            for j, c in enumerate(row):
                al = TextEntityAlignment.MIDDLE_LEFT if j in esq else TextEntityAlignment.MIDDLE_CENTER
                xx = cols[j] + 1.5 if j in esq else (cols[j] + cols[j + 1]) / 2
                negrito = i == 0 or row[0] == "TOTAL"
                texto(psp, c, (xx, yy - hl / 2), 2.2 if not negrito else 2.3,
                      "FOLHA-TITULO" if negrito else "FOLHA-TEXTO", al)
            yy -= hl
            linha(psp, (cx0, yy), (x1, yy))
        for c in cols[1:-1]:
            linha(psp, (c, y), (c, yy))
        y = yy - 1

    # --- base: carimbo (de baixo para cima)
    hc = 34
    yc = y0 + hc
    _carimbo(psp, cx0, y0, x1, yc, carimbo)
    # revisões
    nrev = 4
    y_rev_top = yc + 7 + 3.6 * (nrev + 1)
    _barra(psp, cx0, x1, y_rev_top, "REVISÕES")
    revs = [("REV.", "DATA", "DESCRIÇÃO")] + carimbo.revisoes + [("-", "-", "-")] * (nrev - len(carimbo.revisoes))
    yy = y_rev_top - 7
    cr = [cx0, cx0 + 14, cx0 + 38, x1]
    for i, (r, d, c) in enumerate(revs[:nrev + 1]):
        texto(psp, r, ((cr[0] + cr[1]) / 2, yy - 1.8), 1.6, "FOLHA-TEXTO", TextEntityAlignment.MIDDLE_CENTER)
        texto(psp, d, ((cr[1] + cr[2]) / 2, yy - 1.8), 1.6, "FOLHA-TEXTO", TextEntityAlignment.MIDDLE_CENTER)
        texto(psp, c, (cr[2] + 2, yy - 1.8), 1.6, "FOLHA-TEXTO", TextEntityAlignment.MIDDLE_LEFT)
        yy -= 3.6
        linha(psp, (cx0, yy), (x1, yy))
    for c in cr[1:-1]:
        linha(psp, (c, y_rev_top - 7), (c, yy))
    # empresa
    y_emp = y_rev_top + 7 + 40
    _barra(psp, cx0, x1, y_emp, "EMPRESA RESPONSÁVEL PELO PROJETO")
    hlogo = logo(psp, cx0 + 10, y_emp - 7 - 17, 92)
    tx = cx0 + 110
    texto(psp, EMPRESA["nome"], (tx, y_emp - 11), 2.8)
    for i, l in enumerate(EMPRESA["endereco"]):
        texto(psp, l, (tx, y_emp - 15.5 - 3.2 * i), 1.8)
    texto(psp, "RESPONSÁVEL TÉCNICO:", (cx0 + 3, y_rev_top + 11), 1.6)
    texto(psp, f"{EMPRESA['resp_tecnico']} - {EMPRESA['crea']}", (cx0 + 3, y_rev_top + 7.5), 1.9)
    texto(psp, f"ART Nº: {carimbo.art or '____________________'}", (cx0 + 130, y_rev_top + 11), 1.6)
    texto(psp, "ASS.: ____________________", (cx0 + 130, y_rev_top + 7.5), 1.6)
    linha(psp, (cx0, y_emp - 7 - 33), (x1, y_emp - 7 - 33))

    if y < y_emp + 2:
        print(f"ATENÇÃO: coluna lateral sobrepõe ({y:.1f} < {y_emp:.1f}) - reduzir notas/legenda")
    return psp, vp


def _carimbo(psp, x0, y0, x1, y1, c: Carimbo):
    retangulo(psp, x0, y0, x1, y1, "FOLHA-MOLDURA")
    xa, xb = x0 + 40, x0 + 105
    linha(psp, (xa, y0), (xa, y1), "FOLHA-MOLDURA")
    linha(psp, (xb, y0), (xb, y1), "FOLHA-MOLDURA")
    ym = y0 + 13
    linha(psp, (xa, ym), (x1, ym), "FOLHA-MOLDURA")
    # cliente
    texto(psp, "CLIENTE", (x0 + 2, y1 - 3), 1.4)
    for i, l in enumerate(c.cliente):
        texto(psp, l, ((x0 + xa) / 2, y1 - 9 - i * 3.6), 2.0 if i == 0 else 1.6, "FOLHA-TEXTO",
              TextEntityAlignment.MIDDLE_CENTER)
    # tabela des/verif/aprov
    cols = [xa, xa + 13, xa + 30, xa + 50, xb]
    rows = [y1, y1 - 5, y1 - 10.3, y1 - 15.6, ym]
    for r in rows[1:-1]:
        linha(psp, (xa, r), (xb, r))
    for cc in cols[1:-1]:
        linha(psp, (cc, y1), (cc, ym))
    cab = ["", "DATA", "NOME", "ASS."]
    for j, s in enumerate(cab):
        texto(psp, s, ((cols[j] + cols[j + 1]) / 2, y1 - 2.5), 1.4, "FOLHA-TEXTO", TextEntityAlignment.MIDDLE_CENTER)
    for i, (rot, nome) in enumerate([("DES.", c.des), ("VERIF.", c.verif), ("APROV.", c.aprov)]):
        yy = (rows[i + 1] + rows[i + 2]) / 2
        texto(psp, rot, (xa + 1, yy), 1.5, "FOLHA-TEXTO", TextEntityAlignment.MIDDLE_LEFT)
        texto(psp, c.data if nome else "", ((cols[1] + cols[2]) / 2, yy), 1.5, "FOLHA-TEXTO",
              TextEntityAlignment.MIDDLE_CENTER)
        texto(psp, nome, ((cols[2] + cols[3]) / 2, yy), 1.5, "FOLHA-TEXTO", TextEntityAlignment.MIDDLE_CENTER)
    texto(psp, "FORMATO / FOLHA", (xa + 1, ym - 3), 1.4)
    texto(psp, c.folha, ((xa + xb) / 2, ym - 8.5), 2.5, "FOLHA-TEXTO", TextEntityAlignment.MIDDLE_CENTER)
    # título
    texto(psp, "TÍTULO", (xb + 1.5, y1 - 3), 1.4)
    for i, l in enumerate(c.titulo):
        texto(psp, l, ((xb + x1) / 2, y1 - 7.5 - i * 3.6), 2.2 if i == 0 else 2.0, "FOLHA-TEXTO",
              TextEntityAlignment.MIDDLE_CENTER)
    xc, xd = x1 - 32, x1 - 16
    linha(psp, (xc, y0), (xc, ym))
    linha(psp, (xd, y0), (xd, ym))
    texto(psp, "DESENHO Nº", (xb + 1.5, ym - 3), 1.4)
    texto(psp, c.codigo, ((xb + xc) / 2, y0 + 5), 2.2, "FOLHA-TEXTO", TextEntityAlignment.MIDDLE_CENTER)
    texto(psp, "REV.", (xc + 1.5, ym - 3), 1.4)
    texto(psp, c.revisao, ((xc + xd) / 2, y0 + 5), 3.0, "FOLHA-TEXTO", TextEntityAlignment.MIDDLE_CENTER)
    texto(psp, "ESCALA", (xd + 1.5, ym - 3), 1.4)
    texto(psp, c.escala, ((xd + x1) / 2, y0 + 5), 2.2, "FOLHA-TEXTO", TextEntityAlignment.MIDDLE_CENTER)


def escala_grafica(psp, x, y, escala_den, total_m=50, passo_m=10):
    k = 1000 / escala_den
    n = int(total_m / passo_m)
    for i in range(n):
        h = psp.add_hatch(color=7 if i % 2 == 0 else 0, dxfattribs={"layer": "FOLHA-TEXTO"})
        if i % 2 == 0:
            h.paths.add_polyline_path([(x + i * passo_m * k, y), (x + (i + 1) * passo_m * k, y),
                                       (x + (i + 1) * passo_m * k, y + 1.5), (x + i * passo_m * k, y + 1.5)],
                                      is_closed=True)
        else:
            psp.delete_entity(h)
        retangulo(psp, x + i * passo_m * k, y, x + (i + 1) * passo_m * k, y + 1.5, "FOLHA-TEXTO")
        texto(psp, f"{i * passo_m}", (x + i * passo_m * k, y + 2.5), 1.6, "FOLHA-TEXTO",
              TextEntityAlignment.BOTTOM_CENTER)
    texto(psp, f"{total_m} m", (x + total_m * k, y + 2.5), 1.6, "FOLHA-TEXTO", TextEntityAlignment.BOTTOM_CENTER)
    texto(psp, f"ESCALA GRÁFICA 1:{escala_den}", (x, y - 3.5), 1.8)


def exporta_pdf(doc, nome_layout, caminho_pdf, formato):
    from ezdxf.addons.drawing import Frontend, RenderContext, config, layout, pymupdf
    W, H, _, _ = FORMATOS[formato]
    psp = doc.layouts.get(nome_layout)
    ctx = RenderContext(doc)
    ctx.set_current_layout(psp)
    be = pymupdf.PyMuPdfBackend()
    cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE,
                               color_policy=config.ColorPolicy.COLOR,
                               lineweight_policy=config.LineweightPolicy.ABSOLUTE,
                               lineweight_scaling=1.0,
                               min_lineweight=0.08)
    Frontend(ctx, be, config=cfg).draw_layout(psp, finalize=True)
    pg = layout.Page(W, H, layout.Units.mm, margins=layout.Margins.all(0))
    pdf = be.get_pdf_bytes(pg, settings=layout.Settings(fit_page=False, scale=1.0))
    pathlib.Path(caminho_pdf).write_bytes(pdf)


def exporta_dwg(caminho_dxf, versao="ACAD2018"):
    """Converte o DXF em DWG com o ODA File Converter (gratuito). Devolve o caminho ou None."""
    import shutil, subprocess, tempfile
    exe = shutil.which("ODAFileConverter")
    if not exe:
        print("ODAFileConverter não instalado - DWG não gerado (abra o DXF no AutoCAD e salve como DWG)")
        return None
    dxf = pathlib.Path(caminho_dxf)
    with tempfile.TemporaryDirectory() as ent, tempfile.TemporaryDirectory() as sai:
        shutil.copy(dxf, ent)
        cmd = [exe, ent, sai, versao, "DWG", "0", "1", "*.dxf"]
        if shutil.which("xvfb-run"):
            cmd = ["xvfb-run", "-a"] + cmd
        subprocess.run(cmd, check=False, capture_output=True, timeout=600)
        gerado = pathlib.Path(sai) / (dxf.stem + ".dwg")
        if not gerado.exists():
            print("Falha na conversão para DWG")
            return None
        destino = dxf.with_suffix(".dwg")
        shutil.copy(gerado, destino)
        return destino
