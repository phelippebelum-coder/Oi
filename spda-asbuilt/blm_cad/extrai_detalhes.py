"""Extrai os detalhes típicos de uma prancha DXF da BLM para a biblioteca de blocos.

Uso:  python -m blm_cad.extrai_detalhes prancha.dxf
Gera assets/detalhes_tipicos.dxf (blocos BLM_DET_nn) e assets/detalhes_tipicos.json (tamanho/título).
As regiões abaixo são as da prancha VALE-VITORIA-ELE-SPDA-E-001 (2 linhas x 4 colunas).
"""
import json
import pathlib
import sys

import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer

AQUI = pathlib.Path(__file__).parent

# (número, título, xmin, ymin, xmax, ymax) nas coordenadas do modelo da prancha da Vale
REGIOES = [
    (1, "DESCIDA APARENTE COM BARRA CHATA DE ALUMÍNIO 7/8\"x1/8\"", 0, 70000, 86000, 146500),
    (5, "INSTALAÇÃO DO MINICAPTOR E BARRA CHATA DE ALUMÍNIO NA ALVENARIA", 86000, 70000, 160000, 146500),
    (3, "PILAR METÁLICO COMO DESCIDA NATURAL E MALHA DE ATERRAMENTO", 160000, 70000, 233000, 146500),
    (7, "DESCIDA APARENTE COM CABO DE COBRE NU 35 mm²", 233000, 70000, 300000, 146500),
    (2, "INSTALAÇÃO DO MINICAPTOR E CABO DE COBRE NU 35 mm² NA ALVENARIA", 0, 0, 86000, 70000),
    (6, "MASTRO CAPTOR COM ESTAIAMENTO RÍGIDO", 86000, 0, 160000, 70000),
    (4, "FIXAÇÃO DO TERMINAL AÉREO EM TELHA METÁLICA", 160000, 0, 233000, 70000),
    (8, "HASTE E MALHA DE ATERRAMENTO", 233000, 0, 300000, 70000),
]
CAMADAS_IGNORADAS = {"FORMATO"}


def main(origem):
    src = ezdxf.readfile(origem)
    msp = src.modelspace()
    caixas = []
    for e in msp:
        if e.dxf.layer in CAMADAS_IGNORADAS:
            continue
        try:
            b = bbox.extents([e], fast=True)
        except Exception:
            continue
        if b.has_data:
            caixas.append((e, b))
    dst = ezdxf.new("R2018", setup=True)
    imp = Importer(src, dst)
    info = {}
    for num, titulo, x0, y0, x1, y1 in REGIOES:
        def dentro(e, b):
            if e.dxftype() in ("TEXT", "MTEXT"):  # título longo pode passar da coluna: vale o ponto de inserção
                p = e.dxf.insert
                return x0 <= p.x <= x1 and y0 <= p.y <= y1
            return b.extmin.x >= x0 and b.extmax.x <= x1 and b.extmin.y >= y0 and b.extmax.y <= y1
        sel = [e for e, b in caixas if dentro(e, b)]
        b = bbox.extents([e for e in sel], fast=True)
        nome = f"BLM_DET_{num:02d}"
        blk = dst.blocks.new(nome, base_point=(b.extmin.x, b.extmin.y))
        imp.import_entities(sel, blk)
        info[nome] = {"numero": num, "titulo": titulo, "larg": b.size.x, "alt": b.size.y, "n": len(sel)}
        print(nome, len(sel), round(b.size.x), round(b.size.y))
    imp.finalize()
    dst.saveas(AQUI / "assets/detalhes_tipicos.dxf")
    json.dump(info, open(AQUI / "assets/detalhes_tipicos.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
