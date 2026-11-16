"""Levantamento de campo - Fundação Bradesco, Unidade Escolar Jardim Conceição (Osasco/SP).

Fonte: imagem aérea (Google Maps) marcada por Phelippe em 16/11/2026:
    azul = captor Franklin   vermelho = descida   verde = minicaptor   amarelo = gaiola
+ relatório de corretiva BLM-SPDA-2026-004 (inspeção 14/11/2026).

Coordenadas em PIXELS da imagem levantamento_marcado.png (619 x 864, y para baixo).
Escala: vagas do estacionamento (período 15,5 px ~ 2,5 m) -> 0,16 m/px. PROVISÓRIA.
Norte: para cima (padrão Google Maps).
"""

PROJETO = {
    "codigo": "FBJDC-ELE-SPDA-AB-001",
    "revisao": "0",
    "data": "16/11/2026",
    "formato": "A1",
    "escala": 250,
    "m_por_px": 0.16,
    "alt_img": 864,
    "janela_px": (30, 22, 610, 855),
    "titulo": ["FUNDAÇÃO BRADESCO - JD. CONCEIÇÃO", "SPDA - AS BUILT",
               "CAPTAÇÃO E DESCIDAS - IMPLANTAÇÃO"],
    "cliente": ["FUNDAÇÃO BRADESCO", "UNID. ESCOLAR JD. CONCEIÇÃO", "R. DOZE DE OUTUBRO, 180",
                "CONCEIÇÃO - OSASCO/SP"],
    "rot_norte": 0,
}

# Edificações (contorno da cobertura, px).  linhas_internas = divisões de telhado (base)
EDIF = {
    "A": dict(nome="BLOCO A", poli=[(58, 334), (355, 334), (355, 388), (413, 388), (413, 605), (424, 605),
                                    (424, 740), (82, 740), (82, 553), (58, 553)],
              linhas_internas=[[(235, 334), (235, 553)], [(58, 553), (235, 553)],
                               [(82, 553), (82, 740)], [(355, 553), (355, 672)], [(82, 672), (355, 672)]],
              rotulo=(300, 470), obs="COBERTURA METÁLICA + TELHADO CERÂMICO"),
    "B": dict(nome="BLOCO B", poli=[(230, 264), (283, 230), (275, 212), (327, 191), (388, 330), (261, 335)],
              rotulo=(305, 285)),
    "C": dict(nome="BLOCO C", poli=[(287, 40), (562, 34), (574, 102), (527, 104), (521, 88), (382, 96),
                                    (381, 125), (352, 114), (287, 112)],
              gaiola=True, rotulo=(430, 62)),
    "D": dict(nome="BLOCO D", poli=[(404, 119), (535, 114), (565, 116), (576, 130), (568, 146), (540, 152),
                                    (540, 157), (405, 163)],
              gaiola=True, gaiola_internas=[[(535, 114), (538, 157)]], rotulo=(470, 140)),
    "E": dict(nome="BLOCO E", poli=[(390, 212), (467, 178), (560, 377), (482, 415)],
              gaiola=True, gaiola_internas=[[(424, 194), (521, 396)], [(437, 320), (513, 278)]],
              rotulo=(578, 300)),
}

# Quadra externa (sem edificação): contorno do piso e da quadra pintada (base)
QUADRA = dict(piso=[(60, 68), (196, 68), (196, 334), (60, 334)],
              quadra=[(82, 148), (181, 148), (181, 321), (82, 321)], rotulo=(131, 236))

TEXTOS_BASE = [((240, 790), "ESTACIONAMENTO"), ((131, 100), "QUADRA EXTERNA")]

# Marcações (px)
FRANKLIN = [  # (x, y, edificação ou None)
    (147, 377, "A"), (357, 551, "A"), (359, 624, "A"), (146, 682, "A"), (226, 680, "A"), (312, 682, "A"),
    (71, 207, "QUADRA"), (188, 213, "QUADRA"), (69, 288, "QUADRA"), (185, 294, "QUADRA"),
]
DESCIDAS = [  # (x, y, edificação) - projetadas na fachada
    (329, 202, "B"), (369, 292, "B"),
    (70, 335, "A"), (403, 387, "A"), (407, 600, "A"), (415, 740, "A"), (291, 747, "A"), (175, 746, "A"),
    (88, 739, "A"),
]
MINICAPTORES = [  # (x, y, edificação) - projetados na gaiola
    (291, 49, "C"), (291, 78, "C"), (288, 112, "C"), (561, 37, "C"), (567, 68, "C"), (574, 102, "C"),
    (369, 127, "C"),
    (408, 122, "D"), (401, 140, "D"), (404, 162, "D"), (537, 117, "D"), (536, 135, "D"), (540, 157, "D"),
    (468, 179, "E"), (420, 193, "E"), (392, 213, "E"), (508, 273, "E"), (462, 295, "E"), (435, 321, "E"),
    (554, 378, "E"), (508, 398, "E"), (483, 416, "E"),
]

# Ensaio de continuidade da corretiva (relatório BLM-SPDA-2026-004, 14/11/2026), mΩ
ENSAIO = [(1, 11.9), (2, 11.3), (3, 17.8), (4, 12.9), (5, 10.6), (6, 22.3), (7, 88.0), (8, 12.0), (9, None)]
LIMITE_MOHM = 200
