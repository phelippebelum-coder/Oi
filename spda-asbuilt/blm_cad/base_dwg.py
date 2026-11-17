"""Importa a planta do cliente em DWG/DXF como base no modelo do nosso documento.

As entidades das camadas escolhidas são copiadas para a camada de base (cor por camada),
com uma transformação opcional (escala/rotação/translação) e recortadas por uma janela
retangular. Blocos (INSERT) são mantidos como blocos; textos passam para o estilo da folha.

Também traz o ajuste por mínimos quadrados (similaridade) entre dois sistemas de
coordenadas, usado quando o levantamento foi feito sobre o PDF e a base vem do DWG.
"""
from __future__ import annotations

import math
import pathlib
import re
import shutil
import subprocess
import tempfile

import ezdxf
import numpy as np
from ezdxf import bbox
from ezdxf.addons import Importer
from ezdxf.math import Matrix44
from ezdxf.path import make_path

from .base_pdf import recorta

CAMADAS_PADRAO = ("Predios", "Textos", "Terreno", "Ruas", "Muro", "Vegetação", "Jardim")
_CURVAS = ("LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE")
_FONTE_INLINE = re.compile(r"\\[Ff][^;]*;")


# ------------------------------------------------------------------ transformação
class Similaridade:
    """p' = s * R(ang) * p + t   (ang em radianos)."""

    def __init__(self, s=1.0, ang=0.0, tx=0.0, ty=0.0):
        self.s, self.ang, self.tx, self.ty = s, ang, tx, ty
        self._a, self._b = s * math.cos(ang), s * math.sin(ang)

    def __call__(self, p):
        x, y = p[0], p[1]
        return (self._a * x - self._b * y + self.tx, self._b * x + self._a * y + self.ty)

    def matriz(self) -> Matrix44:
        return Matrix44.chain(Matrix44.scale(self.s, self.s, 1), Matrix44.z_rotate(self.ang),
                              Matrix44.translate(self.tx, self.ty, 0))

    def __repr__(self):
        return (f"Similaridade(escala={self.s:.6f}, rot={math.degrees(self.ang):.4f} graus, "
                f"t=({self.tx:.3f}, {self.ty:.3f}))")


def ajusta_similaridade(origem, destino) -> Similaridade:
    """Mínimos quadrados: similaridade que leva os pontos de origem aos de destino."""
    a, b = np.asarray(origem, float), np.asarray(destino, float)
    ca, cb = a.mean(0), b.mean(0)
    za = (a[:, 0] - ca[0]) + 1j * (a[:, 1] - ca[1])
    zb = (b[:, 0] - cb[0]) + 1j * (b[:, 1] - cb[1])
    w = (np.conj(za) * zb).sum() / (np.abs(za) ** 2).sum()
    t = complex(*cb) - w * complex(*ca)
    return Similaridade(abs(w), math.atan2(w.imag, w.real), t.real, t.imag)


def _vertices(p):
    p = np.asarray(p, float)
    if len(p) > 1 and np.allclose(p[0], p[-1], atol=1e-6):
        p = p[:-1]
    return p


def ajusta_por_contornos(contornos, polilinhas, tol_caixa=0.6, tol_ponto=1.0):
    """Acha a similaridade que leva `contornos` (dict nome -> pontos) às `polilinhas` do DWG.

    1) chute inicial: para cada rotação de 0/90/180/270 graus, casa contornos e polilinhas
       com caixa envolvente de mesmo tamanho e fica com a translação mais votada;
    2) refino: vértices homólogos (vizinho mais próximo dentro de `tol_ponto`) e mínimos
       quadrados, repetido até estabilizar.
    Devolve (Similaridade, relatório) com resíduos em unidades do destino (metros).
    """
    cont = {k: _vertices(v) for k, v in contornos.items()}
    pols = [_vertices(p) for p in polilinhas if len(p) > 2]
    pcx = [((p.min(0) + p.max(0)) / 2, np.ptp(p, axis=0)) for p in pols]
    melhor = None
    for r in range(4):
        ang = r * math.pi / 2
        rot = Similaridade(1.0, ang)
        votos = []
        for v in cont.values():
            q = np.array([rot(p) for p in v])
            cen, dim = (q.min(0) + q.max(0)) / 2, np.ptp(q, axis=0)
            cands = [c for c, d in pcx if np.all(np.abs(d - dim) < tol_caixa)]
            if len(cands) == 1:  # só os casamentos sem ambiguidade votam
                votos.append(cands[0] - cen)
        if not votos:
            continue
        votos = np.array(votos)
        med = np.median(votos, axis=0)
        n = int((np.linalg.norm(votos - med, axis=1) < 3.0).sum())
        if melhor is None or n > melhor[0]:
            melhor = (n, Similaridade(1.0, ang, med[0], med[1]))
    if melhor is None:
        raise ValueError("Não foi possível casar os contornos do PDF com as polilinhas do DWG")
    T = melhor[1]
    alvo = np.vstack(pols)
    pares = []
    for it in range(12):
        tol = max(tol_ponto, 3.0 - 0.5 * it)  # começa folgado e aperta
        pares = []
        for nome, v in cont.items():
            for p in v:
                q = np.array(T(p))
                d = np.linalg.norm(alvo - q, axis=1)
                j = int(d.argmin())
                if d[j] < tol:
                    pares.append((nome, tuple(p), tuple(alvo[j])))
        if len(pares) < 3:
            raise ValueError("Poucos pontos homólogos entre PDF e DWG")
        T = ajusta_similaridade([a for _, a, _ in pares], [b for _, _, b in pares])
    res = np.array([math.dist(T(a), b) for _, a, b in pares])
    por_nome = {}
    for (nome, a, b), e in zip(pares, res):
        por_nome.setdefault(nome, []).append(e)
    rel = dict(n=len(res), rms=float(np.sqrt((res ** 2).mean())), max=float(res.max()),
               media=float(res.mean()), sem_par=sorted(set(cont) - set(por_nome)),
               por_contorno={k: (len(v), float(max(v))) for k, v in por_nome.items()})
    return T, rel


# ------------------------------------------------------------------ leitura
def converte_dwg(caminho_dwg, pasta_saida) -> pathlib.Path:
    """DWG -> DXF (ODA File Converter). Devolve o caminho do DXF gerado."""
    exe = shutil.which("ODAFileConverter")
    if not exe:
        raise RuntimeError("ODAFileConverter não instalado: converta o DWG para DXF e passe o DXF")
    dwg = pathlib.Path(caminho_dwg)
    with tempfile.TemporaryDirectory() as ent:
        shutil.copy(dwg, pathlib.Path(ent) / "base.dwg")
        cmd = [exe, ent, str(pasta_saida), "ACAD2018", "DXF", "0", "1", "*.dwg"]
        if shutil.which("xvfb-run"):
            cmd = ["xvfb-run", "-a"] + cmd
        subprocess.run(cmd, check=False, capture_output=True, timeout=600)
    dxf = pathlib.Path(pasta_saida) / "base.dxf"
    if not dxf.exists():
        raise RuntimeError(f"Falha ao converter {dwg.name} para DXF")
    return dxf


class BaseDWG:
    def __init__(self, caminho, camadas=CAMADAS_PADRAO):
        caminho = pathlib.Path(caminho)
        if caminho.suffix.lower() == ".dwg":
            with tempfile.TemporaryDirectory() as tmp:
                self.doc = ezdxf.readfile(converte_dwg(caminho, tmp))
        else:
            self.doc = ezdxf.readfile(caminho)
        self.camadas = tuple(camadas)
        self.msp = self.doc.modelspace()

    def entidades(self):
        return [e for e in self.msp if e.dxf.layer in self.camadas]

    def polilinhas(self, camada):
        """Vértices das LWPOLYLINE de uma camada (coordenadas do DWG)."""
        return [[(p[0], p[1]) for p in e.get_points("xy")]
                for e in self.msp.query("LWPOLYLINE") if e.dxf.layer == camada]

    def desenha(self, msp, camada, janela, transf: Similaridade | None = None, excluir=(),
                estilo="Standard", pesos=None):
        """Copia a base para `msp` na camada `camada`.

        janela  = (xmin, ymin, xmax, ymax) nas coordenadas de destino (depois de `transf`);
                  o que fica totalmente fora é descartado e as linhas que cruzam a borda são cortadas.
        excluir = retângulos (destino); entidades inteiramente dentro (ou textos com ponto de
                  inserção dentro) não são copiadas.
        pesos   = {camada de origem: espessura em 1/100 mm}; o resto fica "por camada".
        Devolve um dicionário com a contagem por tipo de entidade.
        """
        dst = msp.doc
        x0, y0, x1, y1 = janela
        origem = self.entidades()
        cam_origem = [e.dxf.layer for e in origem]
        for e in origem:  # neutraliza recursos do cliente antes de copiar
            e.dxf.layer = "0"
            for attr in ("linetype", "true_color", "color", "transparency"):
                e.dxf.discard(attr)
            if e.dxf.hasattr("style"):
                e.dxf.style = "Standard"
            if e.dxftype() == "MTEXT":
                e.text = _FONTE_INLINE.sub("", e.text)
        antes = len(msp)
        imp = Importer(self.doc, dst)
        imp.import_entities(origem, msp)
        imp.finalize()
        novas = list(msp)[antes:]
        if len(novas) != len(origem):
            raise RuntimeError("Importação da base: nem todas as entidades foram copiadas")
        m44 = transf.matriz() if transf else None
        cont = {}
        blocos = set()

        def dentro_de(caixa, ret):
            return (caixa.extmin.x >= ret[0] and caixa.extmin.y >= ret[1]
                    and caixa.extmax.x <= ret[2] and caixa.extmax.y <= ret[3])

        for e, cam in zip(novas, cam_origem):
            tipo = e.dxftype()
            e.dxf.layer = camada
            if e.dxf.hasattr("style"):
                e.dxf.style = estilo
            if pesos and cam in pesos:
                e.dxf.lineweight = pesos[cam]
            try:
                if m44 is not None:
                    e.transform(m44)
                caixa = bbox.extents([e], fast=tipo not in ("INSERT", "ARC"))
            except Exception:
                msp.delete_entity(e)
                continue
            if not caixa.has_data:
                msp.delete_entity(e)
                continue
            pt = e.dxf.insert if e.dxf.hasattr("insert") else caixa.center
            fora = caixa.extmax.x < x0 or caixa.extmin.x > x1 or caixa.extmax.y < y0 or caixa.extmin.y > y1
            apagado = any(dentro_de(caixa, r) or (tipo in ("TEXT", "MTEXT")
                                                   and r[0] <= pt.x <= r[2] and r[1] <= pt.y <= r[3])
                          for r in excluir)
            if fora or apagado:
                msp.delete_entity(e)
                continue
            if not dentro_de(caixa, janela):
                if tipo in _CURVAS:  # cruza a borda: corta na janela
                    pts = [(p.x, p.y) for p in make_path(e).flattening(0.02)]
                    attrs = {"layer": camada}
                    if e.dxf.hasattr("lineweight"):
                        attrs["lineweight"] = e.dxf.lineweight
                    msp.delete_entity(e)
                    for trecho in recorta(pts, janela):
                        msp.add_lwpolyline(trecho, dxfattribs=attrs)
                        cont["LWPOLYLINE (cortada)"] = cont.get("LWPOLYLINE (cortada)", 0) + 1
                    continue
                if not (x0 <= pt.x <= x1 and y0 <= pt.y <= y1):  # texto/bloco/hachura na borda
                    msp.delete_entity(e)
                    continue
            if tipo == "INSERT":
                blocos.add(e.dxf.name)
            cont[tipo] = cont.get(tipo, 0) + 1

        # conteúdo dos blocos: camada 0 + cor por camada (herdam a camada da base)
        vistos = set()

        def padroniza(nome):
            if nome in vistos or nome not in dst.blocks:
                return
            vistos.add(nome)
            for b in dst.blocks[nome]:
                b.dxf.layer = "0"
                for attr in ("linetype", "true_color", "transparency"):
                    b.dxf.discard(attr)
                b.dxf.color = 256
                if b.dxf.hasattr("style"):
                    b.dxf.style = estilo
                if b.dxftype() == "INSERT":
                    padroniza(b.dxf.name)
        for nome in blocos:
            padroniza(nome)
        return cont
