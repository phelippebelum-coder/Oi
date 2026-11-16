"""Utilidades geométricas 2D (coordenadas de trabalho do projeto)."""
import math


def fecha(p):
    return p if math.dist(p[0], p[-1]) < 0.5 else list(p) + [p[0]]


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
    pts = poli[:-1] if math.dist(poli[0], poli[-1]) < 1e-6 else poli
    return sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts)


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


def afasta_rotulos(rotulos, LX, LY, iters=80):
    """rotulos: listas [x, y, ...] (modificadas no lugar) - separa caixas sobrepostas."""
    for _ in range(iters):
        mexeu = False
        for i in range(len(rotulos)):
            for j in range(i + 1, len(rotulos)):
                a, b = rotulos[i], rotulos[j]
                dx, dy = b[0] - a[0], b[1] - a[1]
                if abs(dx) < LX and abs(dy) < LY:
                    mexeu = True
                    if abs(dx) / LX > abs(dy) / LY:
                        s = 0.5 * (LX + 0.05 * LX - abs(dx)) * (1 if dx >= 0 else -1)
                        a[0] -= s; b[0] += s
                    else:
                        s = 0.5 * (LY + 0.05 * LY - abs(dy)) * (1 if dy >= 0 else -1)
                        a[1] -= s; b[1] += s
        if not mexeu:
            break
