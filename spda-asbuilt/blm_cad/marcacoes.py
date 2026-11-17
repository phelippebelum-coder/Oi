"""Lê as marcações coloridas de um print aéreo marcado e gera o rascunho do levantamento.

Convenção (padrão BLM):  azul = captor Franklin | vermelho = descida | verde = minicaptor | amarelo = gaiola

Uso:
    python -m blm_cad.marcacoes print_marcado.png [saida_dir]
Gera:
    marcacoes.json   pontos por classe (px) + contornos amarelos aproximados (gaiolas)
    conferencia.png  imagem com cada ponto detectado numerado, para conferir antes de gerar a prancha

Os pontos ainda precisam ser associados às edificações (campo "edif") no levantamento.py.
"""
import json
import pathlib
import sys

import cv2
import numpy as np

# faixas de cor em RGB (ajustáveis). Cada classe: função(R,G,B) -> máscara booleana, área mín/máx (px)
CLASSES = {
    "franklin": (lambda R, G, B: (B > 200) & (R < 120) & (G > 100) & (G < 190), 20, 900),
    "descida": (lambda R, G, B: (R > 170) & (G < 70) & (B < 70) & (R - G > 130), 3, 400),
    "minicaptor": (lambda R, G, B: (G > 180) & (R < 140) & (B < 110) & (G - R > 70), 6, 300),
}
COR_DESENHO = {"franklin": (255, 120, 0), "descida": (0, 0, 255), "minicaptor": (0, 160, 0)}


def le(caminho, saida=None):
    im = cv2.imread(str(caminho))
    if im is None:
        raise SystemExit(f"não consegui abrir {caminho}")
    B, G, R = [im[..., i].astype(int) for i in range(3)]
    out = {"imagem": str(caminho), "tamanho": [im.shape[1], im.shape[0]]}
    vis = (im * 0.55 + 255 * 0.45).astype(np.uint8)
    for nome, (f, amin, amax) in CLASSES.items():
        m = f(R, G, B).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        n, _, st, c = cv2.connectedComponentsWithStats(m)
        pts = [[round(float(c[i][0]), 1), round(float(c[i][1]), 1)] for i in range(1, n)
               if amin <= st[i][4] <= amax]
        pts.sort(key=lambda p: (round(p[1] / 25), p[0]))
        out[nome] = pts
        for k, (x, y) in enumerate(pts, 1):
            cv2.circle(vis, (int(x), int(y)), 7, COR_DESENHO[nome], 2)
            cv2.putText(vis, f"{nome[0].upper()}{k}", (int(x) + 8, int(y) - 6), cv2.FONT_HERSHEY_SIMPLEX,
                        0.38, COR_DESENHO[nome], 1, cv2.LINE_AA)
    # gaiolas (amarelo): contornos externos simplificados
    am = ((R > 200) & (G > 200) & (B < 90)).astype(np.uint8)
    am = cv2.morphologyEx(am, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    cs, _ = cv2.findContours(am, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    gaiolas = []
    for ct in cs:
        if cv2.contourArea(ct) < 400:
            continue
        ap = cv2.approxPolyDP(ct, 4, True).reshape(-1, 2).tolist()
        gaiolas.append(ap)
        cv2.polylines(vis, [np.array(ap)], True, (0, 200, 255), 1)
    out["gaiolas_contorno_externo"] = gaiolas
    saida = pathlib.Path(saida or pathlib.Path(caminho).parent)
    saida.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(saida / "marcacoes.json", "w"), indent=1)
    cv2.imwrite(str(saida / "conferencia.png"), vis)
    print({k: len(v) for k, v in out.items() if isinstance(v, list) and k != "tamanho"})
    return out


if __name__ == "__main__":
    le(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
