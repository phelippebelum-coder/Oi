"""Importa uma planta vetorial em PDF (plotada do AutoCAD) como base no modelo DXF.

Coordenadas de trabalho = pontos PDF na orientação de exibição (x para a direita,
y para baixo). Conversão para metros pela escala de plotagem informada.
"""
from __future__ import annotations

import pymupdf

PT_MM = 25.4 / 72


class BasePDF:
    def __init__(self, caminho, escala_den, pagina=0):
        self.doc = pymupdf.open(caminho)
        self.pg = self.doc[pagina]
        self.M = self.pg.rotation_matrix
        self.alt = self.pg.rect.height
        self.k = PT_MM * escala_den / 1000.0  # metros por ponto
        self.paths = []  # [(indice, largura, [polilinhas em pt])]
        for i, d in enumerate(self.pg.get_drawings()):
            polis, atual = [], []
            for it in d["items"]:
                if it[0] == "l":
                    a, b = it[1] * self.M, it[2] * self.M
                    seg = [(a.x, a.y), (b.x, b.y)]
                elif it[0] == "c":
                    a, b, c, e = [q * self.M for q in it[1:5]]
                    seg = []
                    for j in range(9):
                        t = j / 8
                        p = a * (1 - t) ** 3 + b * 3 * t * (1 - t) ** 2 + c * 3 * t * t * (1 - t) + e * t ** 3
                        seg.append((p.x, p.y))
                elif it[0] in ("qu", "re"):
                    q = it[1] if it[0] == "qu" else pymupdf.Quad(it[1])
                    seg = [((q.ul * self.M).x, (q.ul * self.M).y), ((q.ur * self.M).x, (q.ur * self.M).y),
                           ((q.lr * self.M).x, (q.lr * self.M).y), ((q.ll * self.M).x, (q.ll * self.M).y),
                           ((q.ul * self.M).x, (q.ul * self.M).y)]
                else:
                    continue
                if atual and abs(atual[-1][0] - seg[0][0]) < 0.05 and abs(atual[-1][1] - seg[0][1]) < 0.05:
                    atual.extend(seg[1:])
                else:
                    if len(atual) > 1:
                        polis.append(atual)
                    atual = list(seg)
            if len(atual) > 1:
                polis.append(atual)
            self.paths.append((i, round(d.get("width") or 0, 2), polis))

    def m(self, x, y):
        """pt (exibição) -> metros no modelo (y para cima)."""
        return (x * self.k, (self.alt - y) * self.k)

    def contorno(self, indice):
        """Polilinhas (pt) do caminho de índice dado."""
        return self.paths[indice][2]

    def desenha(self, msp, camada, janela_pt, excluir_pt=()):
        """Desenha a base no modelo, recortada pela janela e sem os trechos excluídos."""
        n = 0
        for i, w, polis in self.paths:
            for p in polis:
                xs = [q[0] for q in p]
                ys = [q[1] for q in p]
                if any(min(xs) >= a and max(xs) <= c and min(ys) >= b and max(ys) <= d
                       for a, b, c, d in excluir_pt):
                    continue
                lw = 35 if w >= 1.0 else (18 if w >= 0.4 else 13)
                for trecho in recorta(p, janela_pt):
                    msp.add_lwpolyline([self.m(*q) for q in trecho],
                                       dxfattribs={"layer": camada, "lineweight": lw})
                    n += 1
        return n

    def desenha_textos(self, msp, camada, janela_pt, estilo, excluir_pt=()):
        """Textos reais do PDF (nomes de ruas etc.) como TEXT, com rotação."""
        import math
        x0, y0, x1, y1 = janela_pt
        n = 0
        for b in self.pg.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                s = "".join(sp["text"] for sp in ln["spans"]).strip()
                if not s:
                    continue
                sp = ln["spans"][0]
                o = pymupdf.Point(sp["origin"]) * self.M
                d = pymupdf.Point(ln["dir"]) * self.M - pymupdf.Point(0, 0) * self.M
                if not (x0 <= o.x <= x1 and y0 <= o.y <= y1):
                    continue
                if any(a <= o.x <= c and bb <= o.y <= dd for a, bb, c, dd in excluir_pt):
                    continue
                ang = -math.degrees(math.atan2(d.y, d.x))
                t = msp.add_text(s, height=sp["size"] * 0.72 * self.k,
                                 dxfattribs={"layer": camada, "style": estilo, "rotation": ang})
                t.dxf.insert = self.m(o.x, o.y)
                n += 1
        return n


def recorta(p, jan):
    """Recorta uma polilinha por um retângulo (Liang-Barsky por segmento)."""
    x0, y0, x1, y1 = jan
    out, atual = [], []
    for (ax, ay), (bx, by) in zip(p[:-1], p[1:]):
        dx, dy = bx - ax, by - ay
        t0, t1, ok = 0.0, 1.0, True
        for pp, qq in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
            if pp == 0:
                if qq < 0:
                    ok = False
                    break
            else:
                r = qq / pp
                if pp < 0:
                    t0 = max(t0, r)
                else:
                    t1 = min(t1, r)
        if not ok or t0 > t1:
            if len(atual) > 1:
                out.append(atual)
            atual = []
            continue
        a2 = (ax + t0 * dx, ay + t0 * dy)
        b2 = (ax + t1 * dx, ay + t1 * dy)
        if atual and abs(atual[-1][0] - a2[0]) < 1e-6 and abs(atual[-1][1] - a2[1]) < 1e-6:
            atual.append(b2)
        else:
            if len(atual) > 1:
                out.append(atual)
            atual = [a2, b2]
        if t1 < 1.0:
            out.append(atual)
            atual = []
    if len(atual) > 1:
        out.append(atual)
    return out
