// Gera o documento de Gerenciamento de Risco (NBR 5419-2) do HGDP a partir de risco_resultados.json
// Uso: node gera_documento.js saida.docx
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, Header, Footer,
  AlignmentType, WidthType, ShadingType, BorderStyle, PageNumber, HeadingLevel, PageBreak,
  LevelFormat, TabStopType,
} = require("docx");

const R = JSON.parse(fs.readFileSync(path.join(__dirname, "risco_resultados.json"), "utf8"));
const LOGO = fs.readFileSync(path.join(__dirname, "../../../blm_cad/assets/logo_blm.png"));
const AZUL = "1C3F94", LARANJA = "E8590C", CINZA = "F2F4F8", VERDE = "2F9E44", VERM = "C92A2A";
const LARG = 9638; // A4 com margens de 2 cm (DXA)
const DOC = "BLM-GR-HGDP/11-2026";
const DATA = "19/11/2026";

// ---------- helpers
const SUP = { "-": "⁻", "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹" };
function sci(x, d = 2) {
  if (x === 0) return "0";
  const e = Math.floor(Math.log10(Math.abs(x)));
  const m = x / Math.pow(10, e);
  if (e >= -1 && e <= 3) return x.toLocaleString("pt-BR", { maximumSignificantDigits: 4 });
  return m.toFixed(d).replace(".", ",") + " × 10" + String(e).split("").map(c => SUP[c]).join("");
}
const num = (x, d = 1) => x.toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const t = (text, o = {}) => new TextRun({ text, font: "Arial", size: o.size || 20, bold: o.bold, italics: o.italics, color: o.color });
const P = (runs, o = {}) => new Paragraph({
  children: Array.isArray(runs) ? runs : [typeof runs === "string" ? t(runs, o) : runs],
  alignment: o.align || AlignmentType.JUSTIFIED, spacing: { before: o.before ?? 60, after: o.after ?? 100, line: 276 },
  numbering: o.bullet ? { reference: "marcadores", level: 0 } : undefined, keepNext: o.keepNext,
});
const H1 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: s })] });
const H2 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: s })] });
const borda = { style: BorderStyle.SINGLE, size: 4, color: "B0B7C3" };
const bordas = { top: borda, bottom: borda, left: borda, right: borda };
function tabela(cab, linhas, pesos, o = {}) {
  const tot = pesos.reduce((a, b) => a + b, 0);
  const w = pesos.map(p => Math.round(p / tot * LARG));
  w[w.length - 1] += LARG - w.reduce((a, b) => a + b, 0);
  const cel = (txt, i, header, fill, cor) => new TableCell({
    width: { size: w[i], type: WidthType.DXA }, borders: bordas,
    shading: { type: ShadingType.CLEAR, color: "auto", fill: header ? AZUL : (fill || "FFFFFF") },
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({
      alignment: (o.esq || [0]).includes(i) ? AlignmentType.LEFT : AlignmentType.CENTER,
      children: [new TextRun({ text: String(txt), font: "Arial", size: o.size || 17, bold: header || (o.negrito && o.negrito(i)), color: header ? "FFFFFF" : (cor || "000000") })],
    })],
  });
  const rows = [new TableRow({ tableHeader: true, children: cab.map((c, i) => cel(c, i, true)) })];
  linhas.forEach((l, k) => {
    const fill = k % 2 ? CINZA : "FFFFFF";
    rows.push(new TableRow({ children: l.map((c, i) => {
      if (c && typeof c === "object") return cel(c.v, i, false, c.fill || fill, c.cor);
      return cel(c, i, false, fill);
    }) }));
  });
  return new Table({ width: { size: LARG, type: WidthType.DXA }, columnWidths: w, rows });
}
const esp = () => new Paragraph({ children: [], spacing: { before: 0, after: 80 } });

// ---------- dados
const C = R.critica, S = C.sem, A = C.com;
const ln0s = S.linhas[0], ln1s = S.linhas[1], ln0a = A.linhas[0], ln1a = A.linhas[1];
const edif = R.edificacoes;
const piorCom = R.pior_com, piorSem = R.pior_sem;
const RFtxt = { incendio_baixo: "baixo (10⁻³)", incendio_normal: "normal (10⁻²)" };
const HZtxt = { evacuacao_dificil: "5", panico_baixo: "2", sem_perigo: "1" };

// ---------- conteúdo
const corpo = [];
// Capa
corpo.push(
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 300 }, children: [new ImageRun({ type: "png", data: LOGO, transformation: { width: 320, height: 65 } })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 120 }, children: [new TextRun({ text: "GERENCIAMENTO DE RISCO", font: "Arial", size: 44, bold: true, color: AZUL })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [t("PROTEÇÃO CONTRA DESCARGAS ATMOSFÉRICAS — ABNT NBR 5419-2", { size: 24, bold: true, color: LARANJA })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 }, children: [t("Hospital Geriátrico e de Convalescentes Dom Pedro II", { size: 26 })] }),
);
corpo.push(tabela(["DADOS DO CLIENTE", ""], [
  ["Cliente", "HOSPITAL GERIÁTRICO E DE CONVALESCENTES DOM PEDRO II"],
  ["CNPJ", "62.779.145/0004-32"],
  ["Endereço", "Avenida Luís Stamatis, 103 — Vila Constança — São Paulo/SP — CEP 02260-000"],
  ["Objeto", "Gerenciamento de risco por descargas atmosféricas (risco R1 — perda de vida humana) e definição das medidas de proteção"],
], [28, 72], { esq: [0, 1], size: 18 }), esp());
corpo.push(tabela(["DADOS DA EXECUTORA", ""], [
  ["Razão social", "BLM Engenharia Ltda — CNPJ 42.180.014/0001-84"],
  ["Endereço", "Av. Zumkeller, 467 — Parque Mandaqui — São Paulo/SP — CEP 02420-000"],
  ["Responsável técnico", "Eng. Phelippe Belum Castro Dias — Engenheiro Eletricista — CREA 5070878575-SP"],
  ["ART", "[A PREENCHER]"],
], [28, 72], { esq: [0, 1], size: 18 }), esp());
corpo.push(tabela(["IDENTIFICAÇÃO DO DOCUMENTO", ""], [
  ["Documento", DOC + " — Rev. 00 (emissão inicial)"], ["Data", DATA],
  ["Documentos relacionados", "Laudo de SPDA (11/10/2024); As built HGDP-ELE-SPDA-AB-001_R00; Relatório de manutenção preventiva da subestação (02/2026)"],
], [28, 72], { esq: [0, 1], size: 18 }));
corpo.push(new Paragraph({ children: [new PageBreak()] }));

// 1 Objetivo
corpo.push(H1("1. OBJETIVO"),
  P("Este documento apresenta o gerenciamento de risco por descargas atmosféricas do Hospital Geriátrico e de Convalescentes Dom Pedro II, conforme a metodologia da ABNT NBR 5419-2. O objetivo é avaliar o risco de perda de vida humana (R1) em cada edificação do complexo, compará-lo com o risco tolerável RT = 10⁻⁵ por ano e definir o conjunto de medidas de proteção — classe do SPDA e sistema de DPS — que leva o risco a valores toleráveis."),
  P("Por se tratar de um hospital, além dos danos físicos e das tensões de toque e passo, foram consideradas as perdas decorrentes de falha dos sistemas internos (componentes RC, RM, RW e RZ), conforme exigido pela norma para estruturas em que essa falha coloca a vida humana em perigo."));

// 2 Normas
corpo.push(H1("2. REFERÊNCIAS NORMATIVAS"),
  tabela(["Referência", "Matéria"], [
    ["ABNT NBR 5419-1 a 5419-4:2026", "Proteção contra descargas atmosféricas — princípios gerais, gerenciamento de risco, danos físicos e sistemas internos"],
    ["ABNT NBR 5419-2:2015 (formulação de cálculo)", "Componentes de risco, probabilidades e perdas (anexos A, B e C) — ver item 4.1"],
    ["IT 14/2019 — CBPMESP", "Carga de incêndio nas edificações e áreas de risco (Anexo A)"],
    ["ABNT NBR 5410:2004 (versão corrigida 2008)", "Instalações elétricas de baixa tensão — categorias de suportabilidade a impulso"],
  ], [38, 62], { esq: [0, 1] }));

// 3 Caracterização
corpo.push(H1("3. CARACTERIZAÇÃO DA INSTALAÇÃO"),
  P("O complexo hospitalar ocupa um terreno urbano na zona norte de São Paulo e é formado por pavilhões de alvenaria, em sua maioria com dois pavimentos e cobertura em telhado cerâmico, interligados por coberturas de passagem. A ocupação predominante é de internação de pacientes idosos e convalescentes, com mobilidade reduzida e presença contínua (24 h)."),
  P("Características relevantes para a análise:", { keepNext: true }),
  P("Alimentação de energia: entrada aérea em média tensão (13,8 kV, Enel) até a cabine primária em alvenaria, com transformadores e para-raios de distribuição na entrada; a partir da cabine, toda a distribuição de baixa tensão às edificações é subterrânea.", { bullet: true }),
  P("Linhas de telecomunicação/dados: consideradas subterrâneas até cada edificação [A CONFIRMAR].", { bullet: true }),
  P("Combate a incêndio: extintores portáteis, com operação exclusivamente manual; não há detecção nem extinção automáticas.", { bullet: true }),
  P("Carga de incêndio: hospitais em geral (H-1/H-3) = 300 MJ/m² e asilos (H-2) = 350 MJ/m², conforme o Anexo A da IT 14/2019 — inferior a 400 MJ/m², portanto risco de incêndio baixo para as edificações hospitalares.", { bullet: true }),
  P("Entorno: área urbana, com as edificações do complexo cercadas por outras de altura semelhante.", { bullet: true }),
  P("As dimensões em planta foram obtidas do arquivo DWG de implantação fornecido pelo cliente (retângulo envolvente de cada edificação, o que é conservador para plantas em L). As alturas foram estimadas a partir do levantamento fotográfico do laudo de 2024 [A CONFIRMAR]."),
  tabela(["Edificação", "Uso", "L (m)", "W (m)", "H (m)"], edif.map(d => [d.nome, d.uso, num(d.L), num(d.W), num(d.H, 0)]), [34, 34, 10, 10, 10], { esq: [0, 1], size: 16 }));

// 4 Premissas
corpo.push(H1("4. PREMISSAS E PARÂMETROS DE CÁLCULO"),
  H2("4.1 Edição da norma e densidade de descargas"),
  P("A ABNT NBR 5419:2026 (partes 1 a 4) é a edição vigente. A formulação dos componentes de risco utilizada neste documento é a da Parte 2 na forma consolidada na edição de 2015 (equivalente à IEC 62305-2:2010). A edição de 2026 acrescenta a avaliação da frequência de dano aos sistemas internos (F), que deve ser verificada em complemento a este documento com o texto e a tabela oficiais."),
  P(`Densidade de descargas atmosféricas para a terra adotada: NG = ${num(R.NG, 0)} descargas/km²/ano, valor do novo mapeamento para o município de São Paulo, que substitui o valor de ${num(R.NG_2015, 0)} da edição de 2015 [A CONFIRMAR na tabela publicada]. A adoção do valor atualizado é a favor da segurança.`),
  H2("4.2 Parâmetros adotados"),
  tabela(["Parâmetro", "Valor", "Justificativa"], [
    ["Risco tolerável RT (R1)", "10⁻⁵ /ano", "NBR 5419-2"],
    ["Fator de localização CD", "0,5", "Estrutura cercada por objetos de mesma altura ou menores"],
    ["Linha de energia (por edificação)", "BT subterrânea — CI = 0,5; CT = 1; CE = 0,1", "Distribuição subterrânea a partir da cabine; área urbana"],
    ["Linha de telecomunicação", "Subterrânea — CI = 0,5; CT = 1; CE = 0,1", "[A CONFIRMAR]"],
    ["Comprimento das linhas LL", "1.000 m", "Valor normativo quando o comprimento real não é conhecido (conservador)"],
    ["Estrutura adjacente (linha BT)", "Cabine primária 10 × 6 × 4 m", "Estrutura na outra extremidade da linha"],
    ["Linhas não blindadas", "CLD = CLI = PLD = 1", "Cabos sem blindagem"],
    ["Tipo de piso / solo (rt)", "10⁻² (agrícola/concreto)", "Valor mais desfavorável entre áreas internas e externas"],
    ["Providências contra incêndio (rp)", "0,5", "Extintores / operação manual"],
    ["Risco de incêndio (rf)", "10⁻³ hospitalar; 10⁻² demais", "IT 14/2019: hospitais 300 MJ/m² (< 400 MJ/m²)"],
    ["Perigo especial (hz)", "5 hospitalar e creche; 2 demais", "Dificuldade de evacuação (pacientes com mobilidade reduzida)"],
    ["Perda por dano físico LF", "10⁻¹ (hospital) / 5 × 10⁻² (capela)", "NBR 5419-2, Anexo C"],
    ["Perda por falha de sistemas internos LO", "10⁻³ (demais partes de hospital)", "Hospital sem UTI/centro cirúrgico [A CONFIRMAR]"],
    ["Perda por tensão de toque e passo LT", "10⁻²", "NBR 5419-2, Anexo C"],
    ["Permanência (nz/nt · tz/8760)", "1", "Zona única, presença contínua (24 h)"],
    ["Suportabilidade dos equipamentos UW", "1,5 kV", "Equipamentos de utilização (NBR 5410, categoria II)"],
  ], [32, 30, 38], { esq: [0, 1, 2], size: 16 }));

// 5 Memória de cálculo
const crit = C.nome;
corpo.push(H1("5. MEMÓRIA DE CÁLCULO — EDIFICAÇÃO CRÍTICA"),
  P(`A memória de cálculo completa é apresentada para a edificação de maior risco com as medidas adotadas: ${crit} (L = ${num(C.L)} m, W = ${num(C.W)} m, H = ${num(C.H, 0)} m). As demais edificações seguem o mesmo procedimento; os resultados constam no item 6.`),
  H2("5.1 Áreas de exposição e número de eventos perigosos"),
  tabela(["Grandeza", "Expressão", "Valor"], [
    ["AD", "L·W + 2·(3H)·(L+W) + π·(3H)²", sci(S.AD) + " m²"],
    ["AM", "2·500·(L+W) + π·500²", sci(S.AM) + " m²"],
    ["ND", "NG·AD·CD·10⁻⁶", sci(S.ND) + " /ano"],
    ["NM", "NG·AM·10⁻⁶", sci(S.NM) + " /ano"],
    ["AL / AI (cada linha)", "40·LL / 4000·LL", sci(ln0s.AL) + " / " + sci(ln0s.AI) + " m²"],
    ["NL (cada linha)", "NG·AL·CI·CE·CT·10⁻⁶", sci(ln0s.NL) + " /ano"],
    ["NI (cada linha)", "NG·AI·CI·CE·CT·10⁻⁶", sci(ln0s.NI) + " /ano"],
    ["NDJ (cabine, linha BT)", "NG·ADJ·CDJ·CT·10⁻⁶", sci(ln0s.NDJ) + " /ano"],
  ], [24, 46, 30], { esq: [0, 1] }),
  esp(),
  H2("5.2 Perdas"),
  tabela(["Perda", "Expressão", "Valor"], [
    ["LA = LU", "rt · LT", sci(S.LA)],
    ["LB = LV", "rp · rf · hz · LF", sci(S.LB)],
    ["LC = LM = LW = LZ", "LO", sci(S.LO)],
  ], [24, 46, 30], { esq: [0, 1] }),
  esp(),
  H2("5.3 Probabilidades — sem proteção e com as medidas adotadas"),
  tabela(["Probabilidade", "Sem proteção", "Com medidas", "Observação"], [
    ["PB (SPDA)", "1", sci(A.PB), "SPDA classe II"],
    ["PA = PTA·PB", "1", sci(A.PA), "Sem medidas adicionais de toque/passo"],
    ["PC = 1 − Π(1 − PSPD·CLD)", "1", sci(A.PC), "DPS coordenados, PSPD = 0,001"],
    ["PMS = (KS1·KS2·KS3·KS4)²", sci(S.PMS), sci(A.PMS), "KS3 = 0,2 (evitar grandes laços); KS4 = 1/UW"],
    ["PM = PSPD·PMS", sci(S.PM), sci(A.PM), ""],
    ["PU = PV = PW (por linha)", "1", sci(ln0a.PV), "DPS na entrada, PEB = 0,001"],
    ["PZ (energia / telecom)", sci(ln0s.PZ) + " / " + sci(ln1s.PZ), sci(ln0a.PZ) + " / " + sci(ln1a.PZ), "PSPD · PLI · CLI"],
  ], [30, 18, 18, 34], { esq: [0, 3], size: 16 }),
  esp(),
  H2("5.4 Componentes de risco"),
  tabela(["Componente", "Expressão", "Sem proteção", "Com medidas"], [
    ["RA", "ND·PA·LA", sci(S.RA), sci(A.RA)],
    ["RB", "ND·PB·LB", sci(S.RB), sci(A.RB)],
    ["RC", "ND·PC·LC", sci(S.RC), sci(A.RC)],
    ["RM", "NM·PM·LM", sci(S.RM), sci(A.RM)],
    ["RU", "Σ(NL+NDJ)·PU·LU", sci(S.RU), sci(A.RU)],
    ["RV", "Σ(NL+NDJ)·PV·LV", sci(S.RV), sci(A.RV)],
    ["RW", "Σ(NL+NDJ)·PW·LW", sci(S.RW), sci(A.RW)],
    ["RZ", "Σ NI·PZ·LZ", sci(S.RZ), sci(A.RZ)],
    [{ v: "R1" }, { v: "Soma" }, { v: sci(S.R1), cor: VERM }, { v: sci(A.R1), cor: VERDE }],
  ], [16, 34, 25, 25], { esq: [0, 1], negrito: () => false }),
  P(`Sem proteção, R1 = ${sci(S.R1)} > RT = 10⁻⁵ (não tolerável). Com as medidas adotadas, R1 = ${sci(A.R1)} ≤ RT (tolerável).`, { before: 120 }));

// 6 Resultados
corpo.push(H1("6. RESULTADOS POR EDIFICAÇÃO"),
  P(`Risco R1 de cada edificação, sem proteção e com as medidas do item 7 (NG = ${num(R.NG, 0)}). A coluna NG = ${num(R.NG_2015, 0)} mostra, para referência, o resultado com o valor da edição de 2015.`),
  tabela(["Edificação", "R1 sem proteção", `R1 com medidas (NG ${num(R.NG, 0)})`, `R1 com medidas (NG ${num(R.NG_2015, 0)})`, "Situação"],
    edif.map(d => [d.nome, sci(d.R1_sem), sci(d.R1_com), sci(d.R1_com_ng11),
      { v: d.atende ? "TOLERÁVEL" : "NÃO TOLERÁVEL", cor: d.atende ? VERDE : VERM }]),
    [34, 16, 18, 18, 14], { esq: [0], size: 15 }),
  P(`Cabine primária (entrada aérea em 13,8 kV, ocupação eventual): R1 = ${sci(R.cabine.sem)} sem proteção e ${sci(R.cabine.com)} com as medidas — tolerável. Os para-raios de distribuição existentes na entrada de MT devem ser mantidos e ensaiados periodicamente.`, { before: 120 }),
  P(`Maior risco sem proteção: ${piorSem.nome} (R1 = ${sci(piorSem.R1_sem)}). Maior risco com as medidas: ${piorCom.nome} (R1 = ${sci(piorCom.R1_com)}). Todas as edificações atendem ao risco tolerável com as medidas adotadas.`));

// 7 Medidas
corpo.push(H1("7. MEDIDAS DE PROTEÇÃO REQUERIDAS"),
  P("O atendimento ao risco tolerável em todas as edificações exige o conjunto de medidas abaixo, adotado de forma uniforme no complexo:", { keepNext: true }),
  P("SPDA classe II (NBR 5419-3) em todas as edificações: subsistemas de captação, descidas e aterramento dimensionados para o nível de proteção II — inclusive malha de captação e espaçamento entre condutores de descida correspondentes à classe II, conforme as tabelas da NBR 5419-3 vigente.", { bullet: true }),
  P("Sistema de DPS coordenados (NBR 5419-4) com características de proteção superiores às exigidas para o nível I (PSPD = PEB = 0,001): DPS na origem de cada linha de energia que entra nas edificações (quadros gerais de BT) e nos pontos de entrada das linhas de telecomunicação/dados, coordenados com DPS nos quadros de distribuição e junto aos equipamentos sensíveis.", { bullet: true }),
  P("Cuidados de roteamento da fiação interna para evitar grandes laços de indução (KS3 = 0,2): condutores de energia e de sinal de um mesmo equipamento lançados juntos, pelo mesmo caminho.", { bullet: true }),
  P("Equipotencialização para descargas atmosféricas em todas as edificações (NBR 5419-3 e 5419-4): barramento de equipotencialização principal interligando SPDA, aterramento, massas metálicas, tubulações e blindagens; equipotencialização das massas metálicas da cobertura apontadas no laudo.", { bullet: true }),
  P("Manutenção dos para-raios de distribuição na entrada aérea de 13,8 kV da cabine primária.", { bullet: true }),
  P("Como alternativa, a instalação de detecção e alarme automáticos de incêndio reduz o fator rp de 0,5 para 0,2, o que diminui a parcela de risco por incêndio (RB e RV). Essa medida não dispensa o sistema de DPS, que é determinado principalmente pelos componentes RM e RZ."));

// 8 SPDA existente
corpo.push(H1("8. SITUAÇÃO DO SPDA EXISTENTE"),
  P("O levantamento de campo consolidado no as built HGDP-ELE-SPDA-AB-001_R00 indica captação por captores Franklin e gaiola de Faraday com descidas aparentes em barra chata de alumínio. A quantidade de condutores de descida levantada em cada edificação é inferior à exigida para a classe II definida neste gerenciamento de risco. Também não há registro de sistema de DPS coordenados nas edificações. Recomenda-se, portanto:"),
  P("Elaborar projeto de adequação do SPDA à classe II, com complementação de descidas, revisão da malha de captação e do subsistema de aterramento.", { bullet: true }),
  P("Elaborar projeto e instalar o sistema de DPS coordenados descrito no item 7.", { bullet: true }),
  P("Instalar SPDA nas edificações indicadas como sem SPDA no as built (Ambulatório, Carpintaria, Salão de festas/Velório e coberturas).", { bullet: true }),
  P("Após a adequação, emitir novo laudo de inspeção com ensaios de continuidade e de resistência de aterramento.", { bullet: true }));

// 9 Conclusão
corpo.push(H1("9. CONCLUSÃO"),
  P(`Sem medidas de proteção, o risco de perda de vida humana atinge R1 = ${sci(piorSem.R1_sem)} por ano, muito acima do risco tolerável de 10⁻⁵ — a proteção contra descargas atmosféricas é obrigatória para o complexo.`),
  P(`Com SPDA classe II, sistema de DPS coordenados (PSPD = PEB = 0,001), cuidados de roteamento da fiação e equipotencialização, o risco de todas as edificações fica igual ou inferior a ${sci(piorCom.R1_com)} por ano. O gerenciamento de risco está, portanto, ATENDIDO, condicionado à implantação e à manutenção das medidas do item 7 e à adequação do SPDA existente descrita no item 8.`),
  P("Os itens marcados como [A CONFIRMAR] são premissas a validar em campo; a alteração de qualquer uma delas exige revisão deste documento. Recomenda-se complementar a análise com a verificação da frequência de dano aos sistemas internos (F) prevista na ABNT NBR 5419-2:2026."),
  new Paragraph({ spacing: { before: 700 }, alignment: AlignmentType.CENTER, children: [t("São Paulo, " + DATA)] }),
  new Paragraph({ spacing: { before: 700 }, alignment: AlignmentType.CENTER, children: [t("_____________________________________________")] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [t("Eng. Phelippe Belum Castro Dias", { bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [t("Engenheiro Eletricista — CREA 5070878575-SP")] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [t("Responsável Técnico — BLM Engenharia Ltda — ART nº [A PREENCHER]")] }));

// ---------- documento
const doc = new Document({
  creator: "BLM Engenharia", title: "Gerenciamento de Risco — HGDP",
  styles: {
    default: { document: { run: { font: "Arial", size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Arial", size: 26, bold: true, color: AZUL },
        paragraph: { spacing: { before: 300, after: 120 }, keepNext: true, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: LARANJA, space: 2 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Arial", size: 21, bold: true, color: AZUL },
        paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "marcadores", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, bottom: 1134, left: 1134, right: 1134 } } },
    headers: { default: new Header({ children: [new Paragraph({
      tabStops: [{ type: TabStopType.RIGHT, position: LARG }],
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: AZUL, space: 4 } },
      children: [new ImageRun({ type: "png", data: LOGO, transformation: { width: 130, height: 26 } }),
        new TextRun({ text: "\tGERENCIAMENTO DE RISCO — NBR 5419-2", font: "Arial", size: 16, color: AZUL, bold: true })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({
      tabStops: [{ type: TabStopType.RIGHT, position: LARG }],
      children: [new TextRun({ text: DOC + " · Rev. 00 · blmengenharia.com.br", font: "Arial", size: 15, color: "666666" }),
        new TextRun({ children: ["\tPágina ", PageNumber.CURRENT, " de ", PageNumber.TOTAL_PAGES], font: "Arial", size: 15, color: "666666" })] })] }) },
    children: corpo,
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(process.argv[2] || "gerenciamento_risco.docx", b); console.log("ok"); });
