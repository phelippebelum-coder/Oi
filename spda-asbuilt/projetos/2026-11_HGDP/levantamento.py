"""Levantamento de campo - Hospital Geriátrico e de Convalescentes Dom Pedro II (HGDP).

Fonte: planta de implantação Santa Casa (HGDP-Imp_1.500, 26/06/2002) marcada à mão
por Phelippe em campo + laudo BLM de 11/10/2024.

Coordenadas em pontos do PDF da implantação (orientação de exibição, y para baixo).
Legenda da marcação de campo:  X = descida   Δ = haste (captor Franklin)   O = minicaptor

Para corrigir algo: edite as listas abaixo e rode  python gerar.py
"""

PROJETO = {
    "codigo": "HGDP-ELE-SPDA-AB-001",
    "revisao": "0",
    "data": "13/11/2026",
    "formato": "A1",
    "escala": 500,
    "titulo": ["HOSP. GERIÁTRICO D. PEDRO II", "SPDA - AS BUILT", "CAPTAÇÃO E DESCIDAS - IMPLANTAÇÃO"],
    "cliente": ["SANTA CASA DE SÃO PAULO", "HOSPITAL GERIÁTRICO E DE", "CONVALESCENTES DOM PEDRO II",
                "AV. LUÍS STAMATIS, 103 - SÃO PAULO/SP"],
    # janela da base (pt) que aparece na folha
    "janela_pt": (318, 240, 1995, 1712),
    # trechos da base apagados (pt): rótulo antigo "Salão de festas/Velório" da atual Farmácia
    "excluir_pt": [(985, 435, 1085, 468)],
}

# Base em DWG (opção --base-dwg): camadas do modelo do desenho do cliente que entram na base.
# A camada "0" do modelo traz as coberturas/passarelas e divisas internas (a moldura e o carimbo da
# Santa Casa ficam no layout de papel, que não é lido). "aux" fica de fora (linhas de construção).
CAMADAS_DWG = ("Predios", "Textos", "Terreno", "Ruas", "Muro", "Vegetação", "Jardim", "0")
CAMADA_PREDIOS_DWG = "Predios"   # contornos usados no ajuste PDF -> DWG
PESOS_DWG = {"Predios": 25, "Muro": 18, "Terreno": 18}   # espessura (1/100 mm); demais = da camada

# Edificações com SPDA levantado.
#   paths  = índice do contorno no PDF da base (cobertura) -> vira a gaiola
#   mini   = qtde de minicaptores marcados em campo (distribuídos no perímetro)
#   gaiola = desenhar condutor perimetral (False = só pontos)
EDIF = {
    "FARM":   dict(nome="FARMÁCIA", paths=[99], mini=24),
    "RES":    dict(nome="RES. IRMÃS/T.O./S.N.D./SALAS DIV.", paths=[98], mini=37),
    "SESMT":  dict(nome="SESMT/RES. IRMÃS/VELÓRIO", paths=[116], mini=9),
    "U1920":  dict(nome="UNID. 19 E 20", paths=[55], mini=18),
    "U1617":  dict(nome="UNID. 16 E 17", paths=[106], mini=20),
    "U1314":  dict(nome="UNID. 13 E 14", paths=[54], mini=22),
    "U1112":  dict(nome="UNID. 11 E 12", paths=[57], mini=22),
    "U23":    dict(nome="UNID. 23", paths=[110], mini=9),
    "ADM":    dict(nome="ADMINISTRAÇÃO/UNID. 23", paths=[56], mini=20),
    "U1522":  dict(nome="UNID. 15, 18, 21 E 22", paths=[84], mini=0, gaiola=False,
                   aceita_descidas=False, situacao="PARCIAL - SÓ FRANKLIN"),  # "APENAS ISSO"
    "CAP":    dict(nome="CAPELA", paths=[1437, 1436, 1435], mini=18),
    "U0708":  dict(nome="UNID. 07 E 08", paths=[77], mini=24),
    "U0506":  dict(nome="UNID. 05 E 06", paths=[79], mini=30),
    "U0304":  dict(nome="UNID. 03 E 04", paths=[78], mini=26),
    "U0102":  dict(nome="UNID. 01 E 02", paths=[58], mini=32),
    "U09":    dict(nome="UNID. 09", paths=[31], mini=35),
    "CRE":    dict(nome="CRECHE", paths=[30], mini=15),
    "PORT2":  dict(nome="PORTARIA 2", paths=[1444], mini=0, gaiola=False,
                   pontos_mini=[(1800, 532)], situacao="PARCIAL"),
    "PORTE":  dict(nome="PORTARIA (ESQ.)", paths=[1426], mini=6),
    "PORTD":  dict(nome="PORTARIA (DIR.)", paths=[1428], mini=7),
}

# Edificações marcadas em campo como SEM SPDA
SEM_SPDA = {
    "AMB":  dict(nome="AMBULATÓRIO/CONS. DENTÁRIO", paths=[24]),
    "CARP": dict(nome="CARPINTARIA", paths=[1442]),
    "SAL2": dict(nome="SALÃO DE FESTAS/VELÓRIO", paths=[100]),
}
# coberturas (passarelas) sem SPDA: só texto, posição (pt)
COBERTURAS_SEM_SPDA = [(990, 1004), (990, 1168)]

# Descidas (X) - posição marcada (pt). São projetadas na fachada mais próxima.
DESCIDAS = [
    (877, 375), (1268, 481), (866, 530), (1040, 535), (1175, 532),          # Farmácia
    (835, 555), (1003, 555),                                               # Res. Irmãs
    (838, 748), (990, 748), (822, 830), (860, 836), (984, 818),            # Unid 19/20
    (832, 874), (990, 873), (838, 968), (992, 968),                        # Unid 16/17
    (842, 1040), (990, 1043), (838, 1135), (992, 1135),                    # Unid 13/14
    (818, 1290), (843, 1294), (832, 1335), (950, 1335),                    # Unid 23 / bloco central
    (812, 1432), (904, 1428), (958, 1438),                                 # Administração
    (1272, 726), (1432, 732), (1246, 832), (1270, 830), (1435, 830),       # Unid 07/08
    (1268, 866), (1270, 962), (1428, 960),                                 # Unid 05/06
    (1268, 1040), (1428, 1042), (1444, 1042), (1270, 1140), (1434, 1138),  # Unid 03/04
    (1268, 1194), (1286, 1194), (1466, 1172), (1278, 1302), (1440, 1296),  # Unid 01/02
    (1574, 676), (1770, 682), (1552, 764), (1764, 764),                    # Unid 09
    (1084, 865), (1095, 943), (1170, 951),                                 # Capela
    (1597, 1176), (1744, 1174), (1546, 1230), (1795, 1158), (1724, 1330),  # Creche
    (1736, 480),                                                           # Portaria 2
]

# Hastes / captores Franklin (Δ) - posição marcada (pt)
FRANKLIN = [
    (845, 370), (962, 535), (1115, 535), (1196, 545), (1260, 540),         # Farmácia
    (892, 550), (1025, 555), (1318, 552),                                  # Res. Irmãs
    (862, 752), (978, 754), (870, 815), (965, 815),                        # Unid 19/20
    (868, 880), (975, 878), (866, 958), (970, 958),                        # Unid 16/17
    (869, 1046), (979, 1046), (866, 1127), (979, 1127),                    # Unid 13/14
    (866, 1275), (978, 1272),                                              # Unid 11/12
    (1300, 735), (1405, 738), (1302, 816), (1408, 825),                    # Unid 07/08
    (1302, 868), (1435, 868), (1278, 912), (1440, 912), (1301, 940), (1406, 950),  # Unid 05/06
    (1293, 1047), (1406, 1047), (1298, 1120), (1410, 1120),                # Unid 03/04
    (1302, 1196), (1436, 1192), (1308, 1282), (1407, 1280), (1466, 1320),  # Unid 01/02
    (1554, 672), (1754, 668), (1576, 770), (1780, 774),                    # Unid 09
    (1089, 885), (1173, 885),                                              # Capela
    (790, 1350),                                                           # Unid 23
    (866, 1380), (970, 1380), (760, 1430),                                 # Administração
    (1538, 1258), (1541, 1306), (1844, 1260),                              # Creche
    (661, 1118),                                                           # Unid 15/18/21/22
    (1020, 1547),                                                          # Portaria esq.
]

# Textos adicionais no desenho (pt, texto, altura em m)
TEXTOS = [
    ((1041, 452), "FARMÁCIA", 1.6),
]
