"""Diagrama unifilar - subestação 13,8 kV / 500 kVA - pontos de aterramento temporário (padrão BLM).

Redesenho do unifilar do projeto de origem (Conectar Engenharia) com simbologia IEC 60617 e
funções de proteção pela numeração ANSI/IEEE C37.2. Modelo em milímetros de papel (sem escala).
Uso:  python gerar.py
"""
import math
import pathlib
import sys

AQUI = pathlib.Path(__file__).parent
sys.path.insert(0, str(AQUI.parents[1]))

from ezdxf.enums import TextEntityAlignment as A  # noqa: E402

from blm_cad import folha  # noqa: E402

CLIENTE = ["[CLIENTE - A PREENCHER]", "SUBESTAÇÃO 13,8 kV - 500 kVA", "", ""]
CODIGO = "SE500-ELE-UNIF-AT-001"
DATA = "22/11/2026"
VERM = (201, 42, 42)

doc = folha.novo_documento()
for nome, rgb, lw, lt in [("UNIF-DIAGRAMA", (0, 0, 0), 35, "Continuous"), ("UNIF-TEXTO", (0, 0, 0), 18, "Continuous"),
                          ("UNIF-CUBICULO", (110, 110, 110), 18, "DASHED"), ("UNIF-CONTROLE", (60, 60, 60), 13, "DASHED"),
                          ("UNIF-AT", VERM, 35, "Continuous"), ("UNIF-AT-TEXTO", VERM, 25, "Continuous"),
                          ("UNIF-TITULO", folha.COR["titulo"], 25, "Continuous")]:
    ly = doc.layers.add(nome)
    ly.rgb = rgb
    ly.dxf.lineweight = lw
    ly.dxf.linetype = lt
doc.header["$LTSCALE"] = 3.0
msp = doc.modelspace()
B = doc.blocks


# ---------------------------------------------------------------- símbolos IEC 60617 (mm, horizontais)
def bl(nome):
    return B.new(nome)


def ln(b, *pts, lay="0"):
    b.add_lwpolyline(pts, dxfattribs={"layer": lay, "color": 0})


s = bl("U_SECC")            # seccionador (IEC 07-13-06)
ln(s, (-6, 0), (-3, 0)); ln(s, (-3, 0), (3.6, 3.4)); ln(s, (3, 0), (6, 0)); ln(s, (3, -1.3), (3, 1.3))
s = bl("U_SECC_TERRA")      # seccionador com lâmina de aterramento (07-13-06 + 07-13-07 + 02-15-01)
ln(s, (-6, 0), (-3, 0)); ln(s, (-3, 0), (3.6, 3.4)); ln(s, (3, 0), (6, 0)); ln(s, (3, -1.3), (3, 1.3))
ln(s, (4.5, 0), (4.5, -3)); ln(s, (4.5, -3), (6.4, -6.2)); ln(s, (4.5, -6.5), (4.5, -9))
ln(s, (2.5, -9), (6.5, -9)); ln(s, (3.3, -10), (5.7, -10)); ln(s, (4.1, -11), (4.9, -11))
s = bl("U_DJ")              # disjuntor (IEC 07-13-05)
ln(s, (-6, 0), (-3, 0)); ln(s, (-3, 0), (3.6, 3.4)); ln(s, (3, 0), (6, 0))
ln(s, (2.1, -0.9), (3.9, 0.9)); ln(s, (2.1, 0.9), (3.9, -0.9))
s = bl("U_CHFUS")           # chave fusível / seccionador-fusível (IEC 07-21-07)
ln(s, (-6, 0), (-3, 0)); ln(s, (-3, 0), (3.6, 3.4)); ln(s, (3, 0), (6, 0)); ln(s, (3, -1.3), (3, 1.3))
c, si = math.cos(math.radians(27.4)), math.sin(math.radians(27.4))
ln(s, (-1.0 * c - 0.7 * si, -1.0 * si + 0.7 * c), (2.6 * c - 0.7 * si, 2.6 * si + 0.7 * c),
   (2.6 * c + 0.7 * si, 2.6 * si - 0.7 * c), (-1.0 * c + 0.7 * si, -1.0 * si - 0.7 * c),
   (-1.0 * c - 0.7 * si, -1.0 * si + 0.7 * c))
s = bl("U_TC")              # transformador de corrente (IEC 06-13-01)
s.add_circle((0, 0), 2.6, dxfattribs={"layer": "0", "color": 0})
s = bl("U_TP")              # transformador de potencial (IEC 06-09-01), vertical, conexão em (0,0)
s.add_circle((0, -3.2), 2.4, dxfattribs={"layer": "0", "color": 0})
s.add_circle((0, -6.6), 2.4, dxfattribs={"layer": "0", "color": 0})
s = bl("U_PR")              # para-raios (IEC 07-22-03), vertical, conexão em (0,0), terra embaixo
ln(s, (0, 0), (0, -2)); ln(s, (-1.4, -2), (1.4, -2), (1.4, -8), (-1.4, -8), (-1.4, -2))
ln(s, (0, -3), (0, -6.4)); ln(s, (-0.7, -5.6), (0, -6.8), (0.7, -5.6))
ln(s, (0, -8), (0, -10)); ln(s, (-2, -10), (2, -10)); ln(s, (-1.2, -11), (1.2, -11)); ln(s, (-0.4, -12), (0.4, -12))
s = bl("U_MUFLA")           # terminação de cabo (IEC 03-04-03), apontando para o cabo (+x)
ln(s, (-2, -2), (2, 0), (-2, 2), (-2, -2))
s = bl("U_TERRA")           # terra (IEC 02-15-01), conexão em (0,0)
ln(s, (0, 0), (0, -3)); ln(s, (-2.5, -3), (2.5, -3)); ln(s, (-1.6, -4), (1.6, -4)); ln(s, (-0.7, -5), (0.7, -5))
s = bl("U_AT")              # ponto de aterramento temporário: conjunto de aterramento + terra
ln(s, (0, 0), (0, -1.5)); s.add_circle((0, -2.3), 0.8, dxfattribs={"layer": "0", "color": 0})
ln(s, (0, -3.1), (0, -4.4)); ln(s, (0, -4.4), (-1.0, -5.2), (1.0, -6.0), (-1.0, -6.8), (0, -7.4)); ln(s, (0, -7.4), (0, -8.5))
ln(s, (-2.5, -8.5), (2.5, -8.5)); ln(s, (-1.6, -9.5), (1.6, -9.5)); ln(s, (-0.7, -10.5), (0.7, -10.5))
s = bl("U_TRAFO_DY")        # transformador 2 enrolamentos (IEC 06-09-02) - Δ / Y aterrado
s.add_circle((-3.2, 0), 4.6, dxfattribs={"layer": "0", "color": 0})
s.add_circle((3.2, 0), 4.6, dxfattribs={"layer": "0", "color": 0})
ln(s, (-9, 0), (-7.8, 0)); ln(s, (7.8, 0), (9, 0))
ln(s, (-5.0, -1.3), (-3.2, 1.8), (-1.4, -1.3), (-5.0, -1.3))   # Δ
ln(s, (3.2, -0.2), (3.2, -1.9)); ln(s, (3.2, -0.2), (1.7, 1.5)); ln(s, (3.2, -0.2), (4.7, 1.5))  # Y
s = bl("U_BUCHA")           # bucha de passagem (parede)
ln(s, (-0.8, -3), (-0.8, 3)); ln(s, (0.8, -3), (0.8, 3))
s = bl("U_CP")              # caixa de passagem
ln(s, (-2.5, -2.5), (2.5, -2.5), (2.5, 2.5), (-2.5, 2.5), (-2.5, -2.5))
s = bl("U_CONT")            # conector de continuação
s.add_circle((0, 0), 3, dxfattribs={"layer": "0", "color": 0})
s = bl("U_MEDIDOR")         # instrumento integrador / medidor (IEC 08-04-01)
ln(s, (-4, -3), (4, -3), (4, 3), (-4, 3), (-4, -3)); ln(s, (-4, 1.6), (4, 1.6))


SS = 1.7  # escala geral dos símbolos na folha


def ins(nome, x, y, lay="UNIF-DIAGRAMA", rot=0, esc=1.0):
    e = esc * SS
    return msp.add_blockref(nome, (x, y), dxfattribs={"layer": lay, "rotation": rot, "xscale": e, "yscale": e})


def L(*pts, lay="UNIF-DIAGRAMA"):
    msp.add_lwpolyline(pts, dxfattribs={"layer": lay})


def T(s, x, y, h=2.5, al=A.MIDDLE_CENTER, lay="UNIF-TEXTO", rot=0):
    t = msp.add_text(s, height=h, dxfattribs={"layer": lay, "style": folha.ESTILO, "width": 0.85, "rotation": rot})
    t.set_placement((x, y), align=al)
    return t


def TL(linhas, x, y, h=2.4, al=A.TOP_LEFT, lay="UNIF-TEXTO", esp=1.5):
    for i, s_ in enumerate(linhas):
        T(s_, x, y - i * h * esp, h, al, lay)


def caixa(x0, y0, x1, y1, lay="UNIF-CUBICULO"):
    L((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0), lay=lay)


def barra_titulo(x0, x1, y, s_, h=3.2):
    L((x0, y), (x1, y), (x1, y + 8), (x0, y + 8), (x0, y), lay="UNIF-TEXTO")
    T(s_, (x0 + x1) / 2, y + 4, h, A.MIDDLE_CENTER, "UNIF-TITULO")


# ================================================================ NÍVEL 1 - DERIVAÇÃO E RAMAL
Y1 = 440
barra_titulo(5, 175, 505, "DERIVAÇÃO (REDE CELESC)")
barra_titulo(175, 600, 505, "RAMAL DE ENTRADA SUBTERRÂNEO / APARENTE")
L((8, Y1), (586, Y1))
TL(["REDE CELESC MT 13,8 kV", "POSTE DE DERIVAÇÃO"], 8, Y1 - 8)
ins("U_CHFUS", 38, Y1, esc=1.3)
TL(["CHAVE FUSÍVEL (3x)", "200 A / 15 kV - ELO 40K (3x)", "VER ESTUDO DE PROTEÇÃO"], 22, Y1 + 26)
# poste de transição + para-raios
x = 85
L((x, Y1), (x, Y1 - 8)); ins("U_PR", x, Y1 - 8, esc=1.2)
TL(["POSTE DE TRANSIÇÃO", "AÉREO / SUBTERRÂNEO"], 72, Y1 + 26)
TL(["PR-01/02/03 PARA-RAIOS (3x)", "12 kV - 10 kA", "ATERRAMENTO #35 mm² Cu NU"], 90, Y1 - 12)
ins("U_MUFLA", 112, Y1, esc=1.2)
TL(["TERMINAÇÃO POLIMÉRICA (4x)", "#35 mm² - 15 kV - EXTERNA"], 120, Y1 + 26)
# ramal subterrâneo
TL(["RAMAL DE ENTRADA: 4x35 mm² 8,7/15 kV", "NEUTRO CONTÍNUO #25 mm² (1W) SEMIRRÍGIDO AZ",
    "ELETRODUTO PEAD CORRUGADO Ø4\" (2x)"], 175, Y1 - 12)
for xx in (160, 255):
    ins("U_CP", xx, Y1)
TL(["CAIXA DE PASSAGEM MT (9x)", "90 x 70 x 80 cm"], 146, Y1 + 14)
TL(["CAIXA DE PASSAGEM MT (2x)", "60 x 60 x 20 cm"], 241, Y1 + 14)
caixa(300, Y1 - 3, 360, Y1 + 3, "UNIF-TEXTO")
TL(["TRECHO APARENTE: ELETROCALHA 10 x 10 cm", "COM TAMPA E LACRE - ELETRODUTO Fe G.F. Ø4\""], 296, Y1 + 14)
ins("U_MUFLA", 395, Y1, rot=180, esc=1.2)
TL(["TERMINAÇÃO POLIMÉRICA (4x)", "#35 mm² - 15 kV - INTERNA"], 380, Y1 + 14)
x = 345
L((x, Y1 - 3), (x, Y1 - 10)); ins("U_PR", x, Y1 - 10, esc=1.2)
TL(["PR-01/02/03 PARA-RAIOS (3x)", "12 kV - 10 kA - #35 mm²"], 351, Y1 - 14)
ins("U_CONT", 589, Y1); T("A", 589, Y1, 2.6)
T("CONTINUA EM (A)", 589, Y1 - 7, 2.0)

# ================================================================ NÍVEL 2 - SUBESTAÇÃO
Y2 = 330
barra_titulo(5, 600, 395, "SUBESTAÇÃO DE MEDIÇÃO E TRANSFORMAÇÃO - CUBÍCULOS EM ALVENARIA")
for x0, x1, nome in [(5, 190, "CUBÍCULO DE ENTRADA E MEDIÇÃO"), (190, 400, "CUBÍCULO DE PROTEÇÃO"),
                     (400, 600, "CUBÍCULO DE TRANSFORMAÇÃO")]:
    barra_titulo(x0, x1, 387, nome, 2.6)
    caixa(x0 + 2, 205, x1 - 2, 385)
ins("U_CONT", 12, Y2); T("A", 12, Y2, 2.6)
L((15, Y2), (520, Y2))
# medição
for xx in (45,):
    ins("U_TC", xx, Y2)
TL(["TC-01/02/03 (3x) - MEDIÇÃO CELESC", "15 kV - 40x80/5 A"], 30, Y2 + 22)
L((90, Y2), (90, Y2 - 12)); ins("U_TP", 90, Y2 - 12)
TL(["TP-01/02/03 (3x) - MEDIÇÃO CELESC", "15 kV - 13,8 kV/√3 : 115 V - RTP 70"], 96, Y2 - 14)
ins("U_MEDIDOR", 60, 255)
TL(["MDR - MEDIÇÃO DE DEMANDA CELESC", "FIAÇÃO #2,5 mm² (SECUNDÁRIOS)"], 38, 246)
L((45, Y2 - 2.6), (45, 258), lay="UNIF-CONTROLE"); T("SINAL DE CORRENTE", 47, 285, 1.8, A.MIDDLE_LEFT)
L((90, Y2 - 21), (90, 255), (64, 255), lay="UNIF-CONTROLE"); T("SINAL DE TENSÃO", 92, 270, 1.8, A.MIDDLE_LEFT)
ins("U_BUCHA", 175, Y2)
TL(["BUCHA DE PASSAGEM", "400 A / 15 kV"], 160, Y2 + 22)
T("BARRAMENTO Ø3/8\" (3x)", 140, Y2 + 4, 1.9)
# proteção
ins("U_AT", 205, Y2, lay="UNIF-AT")
TL(["AT-1"], 199, Y2 - 18, 3.0, lay="UNIF-AT-TEXTO")
ins("U_SECC_TERRA", 232, Y2, esc=1.25)
TL(["CH-01 SECCIONADORA TRIPOLAR", "15 kV - 400 A - MICRO-CHAVE (CONTATO AUX.)",
    "COM LÂMINA DE ATERRAMENTO", "INTERTRAVAMENTO KIRK"], 214, Y2 + 30)
ins("U_TC", 268, Y2)
TL(["TC-04/05/06 (3x) - PROTEÇÃO", "250/5 A - 15 kV - 12,5 VA 10P20"], 256, Y2 - 8)
ins("U_DJ", 318, Y2, esc=1.25)
TL(["DJ-01 DISJUNTOR A VÁCUO - FIXO", "15 kV - 630 A - 16 kA (500 MVA)", "COMANDO MOTORIZADO",
    "INTERTRAVAMENTO KIRK (4NA+4NF)"], 300, Y2 + 30)
caixa(250, 232, 300, 262, "UNIF-TEXTO")
TL(["RELÉ DE PROTEÇÃO", "SECUNDÁRIO", "50/51 - 50N/51N"], 275, 258, 2.0, A.TOP_CENTER)
L((268, Y2 - 2.6), (268, 262), lay="UNIF-CONTROLE")
L((300, 247), (318, 247), (318, Y2 - 4), lay="UNIF-CONTROLE"); T("TRIP", 320, 252, 1.8, A.MIDDLE_LEFT)
L((365, Y2), (365, Y2 - 12)); ins("U_TP", 365, Y2 - 12)
TL(["TP-04 PROTEÇÃO", "13,8 kV / 115 V - 0,3P75"], 330, Y2 - 30)
caixa(342, 222, 395, 246, "UNIF-TEXTO")
TL(["NOBREAK 1000 VA", "ENT. 115 V / SAÍDA 115-220 Vca", "FONTE CAPACITIVA (2x)"], 368.5, 243, 1.9, A.TOP_CENTER)
L((365, Y2 - 21), (365, 246), lay="UNIF-CONTROLE"); L((342, 234), (300, 234), lay="UNIF-CONTROLE")
# transformação
ins("U_SECC_TERRA", 425, Y2, esc=1.25)
TL(["CH-02 SECCIONADORA TRIPOLAR", "15 kV - 400 A", "COM LÂMINA DE ATERRAMENTO",
    "INTERTRAVAMENTO KIRK"], 408, Y2 + 30)
ins("U_TRAFO_DY", 480, Y2, esc=1.3)
TL(["TR-01 TRANSFORMADOR A SECO 500 kVA", "13.800 V - 380/220 V - Dyn - IP-00"], 458, Y2 + 30)
msp.add_circle((480, Y2 - 18), 3.2, dxfattribs={"layer": "UNIF-DIAGRAMA"}); T("49", 480, Y2 - 18, 2.0)
L((480, Y2 - 6), (480, Y2 - 14.8), lay="UNIF-CONTROLE")
TL(["RELÉ DE TEMPERATURA (49)"], 486, Y2 - 16, 1.9)
L((492, Y2), (574, Y2))
T("BT 380/220 V", 500, Y2 + 3, 1.9, A.BOTTOM_LEFT)
ins("U_AT", 530, Y2, lay="UNIF-AT")
TL(["AT-2"], 523, Y2 - 18, 3.0, lay="UNIF-AT-TEXTO")
TL(["4x(1x185) mm² + N 185 mm² + PE 185 mm²", "EPR 90 °C - 0,6/1 kV", "CANALETA NO PISO 40 x 50 cm"], 498, Y2 - 30)
caixa(574, Y2 - 8, 596, Y2 + 8, "UNIF-TEXTO"); T("QG-SE", 585, Y2, 2.4)
# terra das lâminas

# ================================================================ NÍVEL 3 - EQUIPOTENCIALIZAÇÃO
Y3 = 150
barra_titulo(5, 600, 190, "EQUIPOTENCIALIZAÇÃO E ATERRAMENTO DA SUBESTAÇÃO")
caixa(15, Y3 - 6, 55, Y3 + 6, "UNIF-TEXTO"); T("BEP", 35, Y3, 3.2)
TL(["BARRAMENTO DE EQUIPOTENCIALIZAÇÃO", "PRINCIPAL - COBRE 25 x 5 mm (350 A)"], 15, Y3 + 20)
L((55, Y3), (560, Y3))
for i, (cabo, destino) in enumerate([("Cu NU #50 mm²", "TCs E TPs"), ("Cu NU #120 mm²", "X0 DO TRANSFORMADOR"),
                                     ("Cu NU #120 mm²", "MALHA DE ATERRAMENTO"), ("Cu ISOL. #25 mm²", "PARTES METÁLICAS"),
                                     ("Cu NU #70 mm²", "INTERLIGAÇÃO SPDA")]):
    xx = 110 + i * 105
    L((xx, Y3), (xx, Y3 - 12))
    caixa(xx - 30, Y3 - 22, xx + 30, Y3 - 12, "UNIF-TEXTO")
    T(destino, xx, Y3 - 17, 2.0)
    T(cabo, xx + 2, Y3 + 4, 2.0, A.BOTTOM_LEFT)
ins("U_TERRA", 307.5, Y3 - 22)
T("VER MEMORIAL DESCRITIVO DO PROJETO DE ORIGEM PARA O CÁLCULO DO CABO DA MALHA DE ATERRAMENTO.", 15, Y3 - 34, 2.0,
  A.MIDDLE_LEFT)

# ================================================================ QUADRO DOS PONTOS DE ATERRAMENTO TEMPORÁRIO
caixa(10, 38, 595, 100, "UNIF-AT-TEXTO")
T("PONTOS DE ATERRAMENTO TEMPORÁRIO PARA A MANUTENÇÃO PREVENTIVA (NR-10, item 10.5)", 302, 93, 3.0, A.MIDDLE_CENTER,
  "UNIF-AT-TEXTO")
TL(["AT-1 - TRIFÁSICO (3 FASES): BARRAMENTO DE ENTRADA DO CUBÍCULO DE PROTEÇÃO, A MONTANTE DA CH-01.",
    "        INSTALAR SOMENTE APÓS A ABERTURA DAS CHAVES FUSÍVEIS DO POSTE DE DERIVAÇÃO (CONCESSIONÁRIA) E A",
    "        CONSTATAÇÃO DE AUSÊNCIA DE TENSÃO.",
    "AT-2 - TRIFÁSICO + NEUTRO (4 PONTOS): SAÍDA DE BAIXA TENSÃO DO TRANSFORMADOR TR-01, PROTEGENDO CONTRA",
    "        RETORNO DE TENSÃO PELO LADO DE BT (GERADOR, NOBREAK OU INTERLIGAÇÕES).",
    "SEQUÊNCIA DE DESENERGIZAÇÃO (NR-10, 10.5.1): 1) SECCIONAMENTO; 2) IMPEDIMENTO DE REENERGIZAÇÃO (BLOQUEIO KIRK +",
    "        ETIQUETA); 3) CONSTATAÇÃO DA AUSÊNCIA DE TENSÃO COM DETECTOR ADEQUADO À CLASSE; 4) INSTALAÇÃO DO ATERRAMENTO",
    "        TEMPORÁRIO COM EQUIPOTENCIALIZAÇÃO DOS CONDUTORES; 5) PROTEÇÃO DOS ELEMENTOS ENERGIZADOS NA ZONA CONTROLADA;",
    "        6) SINALIZAÇÃO DE IMPEDIMENTO DE REENERGIZAÇÃO. A RETIRADA SEGUE A ORDEM INVERSA."],
   16, 86, 2.5, lay="UNIF-AT-TEXTO", esp=1.5)

# ---------------------------------------------------------------- folha
NORMAS = [
    "ABNT NBR 14039:2021 - INSTALAÇÕES ELÉTRICAS DE MÉDIA TENSÃO DE 1,0 kV A 36,2 kV",
    "IEC 60617 - SÍMBOLOS GRÁFICOS PARA DIAGRAMAS",
    "IEEE C37.2 - NUMERAÇÃO DE FUNÇÕES DE DISPOSITIVOS DE PROTEÇÃO (ANSI)",
    "NR-10 - SEGURANÇA EM INSTALAÇÕES E SERVIÇOS EM ELETRICIDADE",
    "PADRÃO DE FORNECIMENTO EM MÉDIA TENSÃO DA CELESC (VIGENTE)",
]
notas = [
    "DIAGRAMA REDESENHADO A PARTIR DO PROJETO DE ORIGEM (CONECTAR ENGENHARIA - RT ENG. RAFAEL FERREIRA SANTANA - "
    "CREA/SC 102.020-1), SEM ALTERAÇÃO DO CONTEÚDO TÉCNICO, PARA INDICAÇÃO DOS PONTOS DE ATERRAMENTO TEMPORÁRIO "
    "NA MANUTENÇÃO PREVENTIVA. DIAGRAMA SEM ESCALA.",
    "OS RAMAIS DE ENTRADA, ELETRODUTOS DE AÇO GALVANIZADO JUNTO AO POSTE, ARCO E TAMPA DA CAIXA DE PASSAGEM SÃO "
    "FORNECIDOS E INSTALADOS PELO PROPRIETÁRIO.",
    "O CONDUTOR DE ATERRAMENTO DEVE SER CONTÍNUO DO NEUTRO ATÉ A MALHA DE ATERRAMENTO DA SUBESTAÇÃO.",
    "BARRAMENTOS Ø3/8\" PINTADOS: FASE A - VERMELHO; FASE B - BRANCO; FASE C - MARROM.",
    "ELETRODUTO DE AÇO GALVANIZADO Ø4\" CONFORME ABNT NBR 5598.",
    "O SISTEMA DE PROTEÇÃO DEVE POSSUIR 2 FONTES CAPACITIVAS COM CIRCUITO DE TESTE (1 PARA O TRIP DO DISJUNTOR E 1 "
    "PARA O RELÉ), COM AUTONOMIA MÍNIMA DE 2 ABERTURAS.",
    "OS CONJUNTOS DE ATERRAMENTO TEMPORÁRIO DEVEM SER COMPATÍVEIS COM O NÍVEL DE CURTO-CIRCUITO DO PONTO DE "
    "INSTALAÇÃO E ENSAIADOS DENTRO DA VALIDADE.",
]
leg = lambda b, d, c="UNIF-DIAGRAMA", e=1.4: folha.ItemLegenda("bloco", d, b, c, e)
legenda = [
    leg("U_CHFUS", "CHAVE FUSÍVEL / SECCIONADOR-FUSÍVEL (IEC 07-21-07)"),
    leg("U_SECC", "SECCIONADORA (IEC 07-13-06)"),
    leg("U_SECC_TERRA", "SECCIONADORA COM LÂMINA DE ATERRAMENTO", e=1.1),
    leg("U_DJ", "DISJUNTOR (IEC 07-13-05)"),
    leg("U_TC", "TRANSFORMADOR DE CORRENTE - TC (IEC 06-13-01)"),
    leg("U_TP", "TRANSFORMADOR DE POTENCIAL - TP (IEC 06-09-01)", e=1.1),
    leg("U_TRAFO_DY", "TRANSFORMADOR DE POTÊNCIA Δ/Y (IEC 06-09-02)", e=1.0),
    leg("U_PR", "PARA-RAIOS (IEC 07-22-03)", e=0.9),
    leg("U_MUFLA", "TERMINAÇÃO DE CABO / MUFLA (IEC 03-04-03)"),
    leg("U_TERRA", "ATERRAMENTO (IEC 02-15-01)"),
    leg("U_AT", "PONTO DE ATERRAMENTO TEMPORÁRIO (AT-n)", "UNIF-AT", 1.0),
]
car = folha.Carimbo(codigo=CODIGO + "_R00",
                    titulo=["DIAGRAMA UNIFILAR - SE 13,8 kV 500 kVA", "PONTOS DE ATERRAMENTO TEMPORÁRIO",
                            "PARA MANUTENÇÃO PREVENTIVA"],
                    cliente=CLIENTE, escala="S/ ESC.", data=DATA, revisao="0", folha="A1 - 01/01",
                    revisoes=[("0", DATA, "EMISSÃO INICIAL - REDESENHO NO PADRÃO BLM")])
psp, vp = folha.prancha(doc, "A1", car, notas, legenda, None, (0, 0, 606, 544), 1000, faixa_inferior=30,
                        normas=NORMAS, titulo_legenda="LEGENDA - SIMBOLOGIA IEC 60617")
folha.texto(psp, "DIAGRAMA UNIFILAR - SUBESTAÇÃO 13,8 kV / 500 kVA - SEM ESCALA", (33, 22), 5.0, "FOLHA-TITULO")
out = AQUI / "saida"
out.mkdir(exist_ok=True)
nome = CODIGO + "_R00"
doc.set_modelspace_vport(height=544, center=(303, 272))
doc.saveas(out / f"{nome}.dxf")
folha.exporta_pdf(doc, psp.name, out / f"{nome}.pdf", "A1")
print("dwg:", folha.exporta_dwg(out / f"{nome}.dxf"))
