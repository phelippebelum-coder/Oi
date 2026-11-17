"""Verificações rápidas NBR 5419-3 para conferência interna (não vai para a prancha).

Distância média entre descidas (NBR 5419-3, tabela de espaçamento por classe do SPDA):
    Classe I e II: 10 m   |   Classe III: 15 m   |   Classe IV: 20 m
Conferir os valores com a edição vigente da norma antes de usar em laudo.
"""
import math

ESPACAMENTO = {"I": 10, "II": 10, "III": 15, "IV": 20}


def perimetro(poli_m):
    return sum(math.dist(poli_m[i], poli_m[(i + 1) % len(poli_m)]) for i in range(len(poli_m)))


def descidas(nome, poli_m, n_desc):
    """Linha de relatório: perímetro, descidas, espaçamento médio e mínimo exigido por classe."""
    p = perimetro(poli_m)
    if n_desc == 0:
        return f"{nome:<34} perímetro {p:6.1f} m | 0 descidas"
    med = p / n_desc
    minimo = {c: max(2, math.ceil(p / d)) for c, d in ESPACAMENTO.items()}
    atende = [c for c in ("I", "III", "IV") if n_desc >= minimo[c]]
    return (f"{nome:<34} perímetro {p:6.1f} m | {n_desc:2d} descidas | média {med:5.1f} m | "
            f"mín. classe I/II {minimo['I']}, III {minimo['III']}, IV {minimo['IV']} | "
            f"atende: {', '.join(atende) if atende else 'nenhuma'}")
