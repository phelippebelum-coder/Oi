"""Vetoriza o logo BLM (PNG) em contornos por cor -> JSON usado como HATCH no CAD.
Rodar de novo sempre que trocar o logo:  python -m blm_cad.vetoriza_logo caminho/logo.png
"""
import json, sys, pathlib
import cv2, numpy as np

AQUI = pathlib.Path(__file__).parent

def vetoriza(png, saida, n_cores=2, eps=0.8):
    im = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 4:  # fundo transparente -> branco
        a = im[..., 3:4] / 255.0
        im = (im[..., :3] * a + 255 * (1 - a)).astype(np.uint8)
    h, w = im.shape[:2]
    px = im.reshape(-1, 3).astype(np.float32)
    nao_branco = px.sum(1) < 600
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
    _, lab, cent = cv2.kmeans(px[nao_branco], n_cores, None, crit, 5, cv2.KMEANS_PP_CENTERS)
    rotulos = np.full(len(px), -1); rotulos[nao_branco] = lab.ravel()
    camadas = []
    for k, c in enumerate(cent):
        m = (rotulos.reshape(h, w) == k).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        cs, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
        polys = []
        for i, ct in enumerate(cs):
            if cv2.contourArea(ct) < 12:
                continue
            ap = cv2.approxPolyDP(ct, eps, True).reshape(-1, 2)
            # y para cima, normalizado pela altura
            polys.append([[float(x) / h, float(h - y) / h] for x, y in ap])
        b, g, r = [int(v) for v in c]
        camadas.append({"rgb": [r, g, b], "polys": polys})
    json.dump({"aspect": w / h, "camadas": camadas}, open(saida, "w"))
    print(saida, [len(c["polys"]) for c in camadas])

if __name__ == "__main__":
    png = sys.argv[1] if len(sys.argv) > 1 else AQUI / "assets/logo_blm.png"
    vetoriza(png, AQUI / "assets/logo_blm.json")
