// Gera apresentacao_orya.pptx (editável no PowerPoint).
// Dependências: npm install pptxgenjs react-icons react react-dom sharp
// Uso: node gerar_pptx.js
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const lu = require("react-icons/lu");
const fa = require("react-icons/fa6");
const { applyTheme } = require(process.env.APPLY_THEME || "./apply_theme.js");

const DIR = __dirname;
const arq = (...p) => path.join(DIR, ...p);

const HEX = {
  texto: "4A4034", creme: "FFFCF7", taupe: "6B5E4E", areia: "F6F1EA",
  ouro: "9A7440", dourado: "E6C996", marrom: "5A4E40", nude: "EADBC6", rose: "F1DCD2", suave: "6F6457",
};
const THEME = {
  name: "ORYA",
  headFontFace: "Georgia",
  bodyFontFace: "Calibri",
  colors: {
    dk1: HEX.texto, lt1: HEX.creme, dk2: HEX.taupe, lt2: HEX.areia,
    accent1: HEX.ouro, accent2: HEX.dourado, accent3: HEX.marrom, accent4: HEX.nude,
    accent5: HEX.rose, accent6: HEX.suave, hlink: HEX.ouro, folHlink: HEX.taupe,
  },
};

async function icone(Comp, cor, tam = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { size: tam, color: "#" + cor }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13,333" x 7,5"
  pres.title = "ORYA · Como funciona";
  pres.author = "ORYA Estética Avançada";
  pres.company = "ORYA Estética Avançada";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  const MONO_W = 0.55, MONO_H = 0.62; // monograma 1068x1200
  const sobreClaro = { x: 0.75, y: 0.55, w: 10.5, h: 0.4, fontSize: 13, bold: true, charSpacing: 5, color: C.accent1, margin: 0 };
  const sobreEscuro = { ...sobreClaro, color: C.accent2 };
  const tituloClaro = { x: 0.75, y: 0.95, w: 11.0, h: 1.1, fontSize: 36, bold: true, color: C.text1, align: "left", valign: "top", margin: 0 };
  const tituloEscuro = { ...tituloClaro, color: C.background1 };

  function layout(nome, fundo, escuro, comTitulo = true) {
    const objetos = [];
    if (comTitulo) {
      objetos.push({ image: { path: arq("logo", escuro ? "orya_monograma_clara.png" : "orya_monograma.png"), x: 12.05, y: 0.45, w: MONO_W, h: MONO_H } });
      objetos.push({ placeholder: { options: { name: "sobre", type: "body", ...(escuro ? sobreEscuro : sobreClaro) }, text: "" } });
      objetos.push({ placeholder: { options: { name: "title", type: "title", ...(escuro ? tituloEscuro : tituloClaro) }, text: "" } });
    }
    pres.defineSlideMaster({ title: nome, background: fundo, objects: objetos });
  }
  layout("ORYA CLARO", { color: C.background2 }, false);
  layout("ORYA BRANCO", { color: C.background1 }, false);
  layout("ORYA ESCURO", { color: C.text2 }, true);
  layout("ORYA MARROM", { color: C.accent3 }, true);
  layout("ORYA CAPA", { path: arq("fundos", "capa.png") }, true, false);
  layout("ORYA FECHAMENTO", { path: arq("fundos", "cta.png") }, true, false);
  layout("ORYA FRASE", { color: C.accent4 }, false, false);

  const titulo = (s, a, b, cor) => s.addText([
    { text: a },
    { text: b, options: { italic: true, color: cor } },
  ], { placeholder: "title" });

  // ---------- 1. Capa ----------
  pres.addSection({ title: "Abertura" });
  let s = pres.addSlide({ masterName: "ORYA CAPA", sectionTitle: "Abertura" });
  s.addImage({ path: arq("logo", "orya_monograma_clara.png"), x: 8.7, y: 0.9, w: 4.9, h: 5.5, transparency: 87, objectName: "Marca d'água" });
  s.addImage({ path: arq("logo", "orya_horizontal_clara.png"), x: 0.75, y: 0.8, w: 3.6, h: 1.03, altText: "ORYA by Dra Danielly Pinheiro" });
  s.addText([
    { text: "Realce a sua beleza.", options: { breakLine: true } },
    { text: "Sem perder a sua essência.", options: { italic: true, color: C.accent2 } },
  ], { x: 0.75, y: 2.2, w: 8.6, h: 2.5, fontFace: "Georgia", fontSize: 44, bold: true, color: C.background1, valign: "top", margin: 0, isTextBox: true, objectName: "Título da capa" });
  s.addText("Estética avançada com a Dra. Danielly Pinheiro: avaliação individual, plano feito para você e resultado natural.",
    { x: 0.75, y: 5.0, w: 7.4, h: 0.9, fontSize: 18, color: C.accent5, margin: 0, isTextBox: true });
  s.addText("DRA. DANIELLY PINHEIRO · CRBM-1 62832", { x: 0.75, y: 6.75, w: 6, h: 0.3, fontSize: 11, charSpacing: 4, color: C.accent4, margin: 0, isTextBox: true });
  s.addNotes("Abertura: a promessa da ORYA é realçar a beleza com naturalidade.");

  // ---------- 2. A dor ----------
  s = pres.addSlide({ masterName: "ORYA CLARO", sectionTitle: "Abertura" });
  s.addText("POR QUE VOCÊ ESTÁ AQUI", { placeholder: "sobre" });
  titulo(s, "Quando o espelho não mostra ", "como você se sente", C.accent1);
  const dores = [
    [lu.LuFrown, "Rosto cansado", "Linhas de expressão e olhar pesado que fazem você parecer mais cansada do que está."],
    [lu.LuScanFace, "Contorno e firmeza", "Perda de colágeno, flacidez e contorno menos definido com o passar dos anos."],
    [lu.LuHeart, "Medo de ficar artificial", "A vontade de cuidar de si com a segurança de continuar sendo você."],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.75 + i * 4.0, y = 2.85;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 3.75, h: 3.4, rectRadius: 0.12, fill: { color: C.background1 },
      shadow: { type: "outer", color: HEX.texto, opacity: 0.12, blur: 12, offset: 4, angle: 90 }, line: { color: C.background1 }, objectName: `Card ${i + 1}` });
    s.addShape(pres.shapes.OVAL, { x: x + 0.4, y: y + 0.4, w: 0.8, h: 0.8, fill: { color: C.accent4 }, line: { color: C.accent4 } });
    s.addImage({ data: await icone(dores[i][0], HEX.ouro), x: x + 0.58, y: y + 0.58, w: 0.44, h: 0.44 });
    s.addText(dores[i][1], { x: x + 0.4, y: y + 1.45, w: 3.0, h: 0.5, fontSize: 20, bold: true, color: C.text1, margin: 0, isTextBox: true });
    s.addText(dores[i][2], { x: x + 0.4, y: y + 2.0, w: 3.0, h: 1.2, fontSize: 15, color: C.accent6, margin: 0, valign: "top", isTextBox: true });
  }

  // ---------- 3. Dra. Danielly ----------
  pres.addSection({ title: "Quem somos" });
  s = pres.addSlide({ masterName: "ORYA ESCURO", sectionTitle: "Quem somos" });
  s.addText("QUEM CUIDA DE VOCÊ", { placeholder: "sobre" });
  titulo(s, "Dra. Danielly ", "Pinheiro", C.accent2);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.75, y: 2.25, w: 3.3, h: 0.5, rectRadius: 0.25, fill: { color: C.accent2 }, line: { color: C.accent2 } });
  s.addText("ESPECIALIZAÇÃO EM PARIS", { x: 0.75, y: 2.25, w: 3.3, h: 0.5, fontSize: 12, bold: true, charSpacing: 3, color: C.text1, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText("Do primeiro olhar ao retorno, é a própria Dra. quem avalia, planeja e faz o seu procedimento.",
    { x: 0.75, y: 3.05, w: 4.5, h: 1.3, fontSize: 18, color: C.accent5, margin: 0, valign: "top", isTextBox: true });
  const creds = [
    [lu.LuStar, "Anatomia aplicada à harmonização facial", "Especialização em Paris, na França."],
    [lu.LuGraduationCap, "Pós-graduação em biomedicina estética", "Formação no Brasil."],
    [lu.LuBadgeCheck, "Biomédica esteta", "CRBM-1 nº 62832. Sócia e responsável técnica da ORYA."],
    [lu.LuUser, "Do início ao fim", "Avaliação, plano, procedimento e acompanhamento com ela."],
  ];
  for (let i = 0; i < 4; i++) {
    const x = 5.85 + (i % 2) * 3.45, y = 2.25 + Math.floor(i / 2) * 2.35;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 3.25, h: 2.15, rectRadius: 0.1, fill: { color: C.accent3 }, line: { color: C.accent3 } });
    s.addImage({ data: await icone(creds[i][0], HEX.dourado), x: x + 0.3, y: y + 0.28, w: 0.45, h: 0.45 });
    s.addText(creds[i][1], { x: x + 0.3, y: y + 0.85, w: 2.7, h: 0.65, fontSize: 15, bold: true, color: C.background1, margin: 0, valign: "top", isTextBox: true });
    s.addText(creds[i][2], { x: x + 0.3, y: y + 1.5, w: 2.7, h: 0.55, fontSize: 12.5, color: C.accent5, margin: 0, valign: "top", isTextBox: true });
  }

  // ---------- 4. Jornada ----------
  pres.addSection({ title: "Como funciona" });
  s = pres.addSlide({ masterName: "ORYA CLARO", sectionTitle: "Como funciona" });
  s.addText("COMO FUNCIONA", { placeholder: "sobre" });
  titulo(s, "A sua jornada ", "em 5 etapas", C.accent1);
  const etapas = [
    ["Conversa inicial", "Pelo WhatsApp, entendemos o que te incomoda e o seu momento."],
    ["Avaliação com a Dra.", "Análise completa do rosto ou corpo. Valor 100% abatido se você fechar."],
    ["Plano personalizado", "Os caminhos possíveis para você, explicados com transparência."],
    ["Procedimento", "Com a própria Dra., produtos ANVISA abertos na sua frente."],
    ["Acompanhamento", "Retorno em 15 dias nos injetáveis e calendário de manutenção."],
  ];
  for (let i = 0; i < 5; i++) {
    const x = 0.75 + i * 2.39, y = 2.7, ultimo = i === 4;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.22, h: 3.6, rectRadius: 0.1, fill: { color: ultimo ? C.accent3 : C.background1 },
      line: { color: ultimo ? C.accent3 : C.background1 }, shadow: { type: "outer", color: HEX.texto, opacity: 0.1, blur: 10, offset: 3, angle: 90 } });
    s.addText(String(i + 1).padStart(2, "0"), { x: x + 0.25, y: y + 0.25, w: 1.6, h: 0.75, fontFace: "Georgia", fontSize: 40, bold: true, color: ultimo ? C.accent2 : C.accent1, margin: 0, isTextBox: true });
    s.addText(etapas[i][0], { x: x + 0.25, y: y + 1.1, w: 1.8, h: 0.7, fontSize: 16, bold: true, color: ultimo ? C.background1 : C.text1, margin: 0, valign: "top", isTextBox: true });
    s.addText(etapas[i][1], { x: x + 0.25, y: y + 1.85, w: 1.8, h: 1.6, fontSize: 13, color: ultimo ? C.accent5 : C.accent6, margin: 0, valign: "top", isTextBox: true });
  }

  // ---------- 5. Metodologias ----------
  s = pres.addSlide({ masterName: "ORYA BRANCO", sectionTitle: "Como funciona" });
  s.addText("METODOLOGIAS EXCLUSIVAS", { placeholder: "sobre" });
  titulo(s, "Um método ", "para cada objetivo", C.accent1);
  const metodos = [
    ["HARMONIZAÇÃO FACIAL", "Método Essência ORYA", "Equilíbrio e proporção em etapas, começando pelo essencial."],
    ["TOXINA BOTULÍNICA", "Protocolo Olhar Leve", "Suaviza linhas e cansaço sem tirar a naturalidade dos movimentos."],
    ["PREENCHIMENTO LABIAL", "Lábios Assinatura", "Contorno, volume e hidratação na medida do seu rosto."],
    ["BIOESTIMULADORES", "Protocolo Colágeno Vivo", "O seu próprio colágeno trabalhando por mais firmeza."],
    ["GLÚTEO E CORPO", "Contorno ORYA", "Proporção, firmeza e autoestima no contorno corporal."],
    ["PELE E BEM-ESTAR", "Pele Renovada & Leveza", "Limpeza de pele, peelings, microagulhamento e drenagem."],
  ];
  for (let i = 0; i < 6; i++) {
    const x = 0.75 + (i % 3) * 4.0, y = 2.45 + Math.floor(i / 3) * 2.15;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 3.75, h: 1.95, rectRadius: 0.1, fill: { color: C.background2 }, line: { color: C.background2 } });
    s.addText(metodos[i][0], { x: x + 0.3, y: y + 0.25, w: 3.2, h: 0.3, fontSize: 10.5, bold: true, charSpacing: 3, color: C.accent1, margin: 0, isTextBox: true });
    s.addText(metodos[i][1], { x: x + 0.3, y: y + 0.58, w: 3.2, h: 0.45, fontFace: "Georgia", fontSize: 16, bold: true, color: C.text1, margin: 0, isTextBox: true });
    s.addText(metodos[i][2], { x: x + 0.3, y: y + 1.12, w: 3.2, h: 0.72, fontSize: 13, color: C.accent6, margin: 0, valign: "top", isTextBox: true });
  }

  // ---------- 6. Frase ----------
  s = pres.addSlide({ masterName: "ORYA FRASE", sectionTitle: "Como funciona" });
  s.addImage({ path: arq("logo", "orya_monograma.png"), x: 8.9, y: 0.9, w: 4.9, h: 5.5, transparency: 90 });
  s.addText([
    { text: "Realçar quem você é.", options: { breakLine: true } },
    { text: "Nunca transformar você em outra pessoa.", options: { italic: true, color: C.accent1 } },
  ], { x: 0.75, y: 2.0, w: 10.5, h: 3.4, fontFace: "Georgia", fontSize: 54, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true });

  // ---------- 7. Plano anual ----------
  pres.addSection({ title: "Planos e diferenciais" });
  s = pres.addSlide({ masterName: "ORYA ESCURO", sectionTitle: "Planos e diferenciais" });
  s.addText("PLANO OLHAR LEVE ANUAL", { placeholder: "sobre" });
  titulo(s, "O seu botox do ano, ", "sempre em dia", C.accent2);
  s.addText("30%", { x: 0.75, y: 2.2, w: 4.6, h: 2.2, fontFace: "Georgia", fontSize: 140, bold: true, color: C.accent2, margin: 0, valign: "middle", isTextBox: true });
  s.addText("de economia em relação às aplicações avulsas (terço superior)", { x: 0.75, y: 4.5, w: 4.4, h: 0.9, fontSize: 18, color: C.background1, margin: 0, valign: "top", isTextBox: true });
  const itens = ["4 aplicações programadas em 12 meses", "Acompanhamento da Dra. Danielly em todas as sessões", "Retorno de 15 dias após cada aplicação", "Parcelamento em até 10x sem juros", "Valores e condições na nossa conversa"];
  const check = await icone(lu.LuCheck, HEX.dourado);
  for (let i = 0; i < itens.length; i++) {
    const y = 2.25 + i * 0.82;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.0, y, w: 6.6, h: 0.66, rectRadius: 0.08, fill: { color: C.accent3 }, line: { color: C.accent3 } });
    s.addImage({ data: check, x: 6.22, y: y + 0.17, w: 0.32, h: 0.32 });
    s.addText(itens[i], { x: 6.75, y, w: 5.7, h: 0.66, fontSize: 16, color: C.background1, valign: "middle", margin: 0, isTextBox: true });
  }

  // ---------- 8. Diferenciais ----------
  s = pres.addSlide({ masterName: "ORYA MARROM", sectionTitle: "Planos e diferenciais" });
  s.addText("POR QUE A ORYA", { placeholder: "sobre" });
  titulo(s, "O que você pode ", "esperar de nós", C.accent2);
  const difs = [
    [lu.LuShieldCheck, "Segurança", "Produtos ANVISA abertos na sua frente e triagem de saúde antes de tudo."],
    [lu.LuHeart, "Naturalidade", "Começamos pelo necessário e ajustamos no retorno, se precisar."],
    [lu.LuClock, "Agenda flexível", "Horários que encaixam na sua rotina, em três regiões de São Paulo."],
    [lu.LuWallet, "Avaliação que volta", "O valor da avaliação é 100% abatido no procedimento que você fechar."],
    [lu.LuCheck, "Retorno incluso", "Retorno em 15 dias nos injetáveis para acompanhar o seu resultado."],
    [lu.LuMessageCircle, "Acolhimento", "Do primeiro “oi” ao pós-procedimento, você é acompanhada de perto."],
  ];
  for (let i = 0; i < 6; i++) {
    const x = 0.75 + (i % 3) * 4.0, y = 2.35 + Math.floor(i / 3) * 2.05;
    s.addShape(pres.shapes.OVAL, { x, y, w: 0.72, h: 0.72, fill: { color: C.text2 }, line: { color: C.accent2, width: 1 } });
    s.addImage({ data: await icone(difs[i][0], HEX.dourado), x: x + 0.18, y: y + 0.18, w: 0.36, h: 0.36 });
    s.addText(difs[i][1], { x, y: y + 0.85, w: 3.6, h: 0.42, fontSize: 18, bold: true, color: C.background1, margin: 0, isTextBox: true });
    s.addText(difs[i][2], { x, y: y + 1.27, w: 3.5, h: 0.7, fontSize: 13.5, color: C.accent5, margin: 0, valign: "top", isTextBox: true });
  }
  s.addText("Os resultados variam de pessoa para pessoa e dependem da avaliação individual.", { x: 0.75, y: 6.75, w: 9, h: 0.3, fontSize: 11, italic: true, color: C.accent4, margin: 0, isTextBox: true });

  // ---------- 9. Unidades ----------
  s = pres.addSlide({ masterName: "ORYA CLARO", sectionTitle: "Planos e diferenciais" });
  s.addText("ONDE ATENDEMOS", { placeholder: "sobre" });
  titulo(s, "Perto de você, ", "em três regiões", C.accent1);
  const unidades = [
    ["ZONA NORTE", "Jardim São Paulo", "Rua Viri, 62. Pertinho de Santana e do Shopping Center Norte.", true],
    ["ZONA LESTE", "Tatuapé", "Atendimento em consultório na região, com data e local combinados com você.", false],
    ["REGIÃO DOS JARDINS", "Jardins", "Atendimento em consultório na região, com data e local combinados com você.", false],
  ];
  for (let i = 0; i < 3; i++) {
    const [regiao, nome, txt, principal] = unidades[i];
    const x = 0.75 + i * 4.0, y = 2.4;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 3.75, h: 2.5, rectRadius: 0.1, fill: { color: principal ? C.accent3 : C.background1 },
      line: { color: principal ? C.accent3 : C.background1 }, shadow: { type: "outer", color: HEX.texto, opacity: 0.1, blur: 10, offset: 3, angle: 90 } });
    s.addText(regiao, { x: x + 0.35, y: y + 0.3, w: 3.1, h: 0.3, fontSize: 10.5, bold: true, charSpacing: 3, color: principal ? C.accent2 : C.accent1, margin: 0, isTextBox: true });
    s.addText(nome, { x: x + 0.35, y: y + 0.65, w: 3.1, h: 0.6, fontFace: "Georgia", fontSize: 20, bold: true, color: principal ? C.background1 : C.text1, margin: 0, isTextBox: true });
    s.addText(txt, { x: x + 0.35, y: y + 1.35, w: 3.1, h: 1.0, fontSize: 14, color: principal ? C.accent5 : C.accent6, margin: 0, valign: "top", isTextBox: true });
  }
  const horarios = [["8h às 18h", "de segunda a sábado"], ["Sob consulta", "horários após as 18h e domingos"]];
  for (let i = 0; i < 2; i++) {
    const x = 0.75 + i * 6.0, y = 5.3;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 5.75, h: 0.95, rectRadius: 0.1, fill: { color: C.background1 }, line: { color: C.accent1, width: 1.5 } });
    s.addText([
      { text: horarios[i][0] + "   ", options: { fontFace: "Georgia", fontSize: 22, bold: true, color: C.text1 } },
      { text: horarios[i][1], options: { fontSize: 14, color: C.accent6 } },
    ], { x: x + 0.35, y, w: 5.2, h: 0.95, valign: "middle", margin: 0, isTextBox: true });
  }

  // ---------- 10. Fechamento ----------
  pres.addSection({ title: "Próximo passo" });
  s = pres.addSlide({ masterName: "ORYA FECHAMENTO", sectionTitle: "Próximo passo" });
  s.addImage({ path: arq("logo", "orya_monograma_clara.png"), x: 8.9, y: 0.95, w: 4.6, h: 5.17, transparency: 87 });
  s.addImage({ path: arq("logo", "orya_horizontal_clara.png"), x: 0.75, y: 0.8, w: 2.8, h: 0.8, altText: "ORYA by Dra Danielly Pinheiro" });
  s.addText("PRÓXIMO PASSO", { x: 0.75, y: 2.0, w: 6, h: 0.35, fontSize: 13, bold: true, charSpacing: 5, color: C.accent2, margin: 0, isTextBox: true });
  s.addText([{ text: "Vamos cuidar " }, { text: "de você?", options: { italic: true, color: C.accent2 } }],
    { x: 0.75, y: 2.4, w: 8.8, h: 1.1, fontFace: "Georgia", fontSize: 40, bold: true, color: C.background1, margin: 0, isTextBox: true });
  s.addText("Responda por aqui e a gente encontra o melhor dia, horário e unidade para a sua avaliação com a Dra. Danielly.",
    { x: 0.75, y: 3.7, w: 7.6, h: 0.9, fontSize: 18, color: C.accent5, margin: 0, valign: "top", isTextBox: true });
  s.addImage({ data: await icone(fa.FaWhatsapp, HEX.dourado), x: 0.75, y: 4.85, w: 0.38, h: 0.38 });
  s.addText("(11) 2959-3266", { x: 1.25, y: 4.8, w: 2.8, h: 0.48, fontSize: 18, bold: true, color: C.background1, valign: "middle", margin: 0, isTextBox: true });
  s.addImage({ data: await icone(fa.FaInstagram, HEX.dourado), x: 4.2, y: 4.85, w: 0.38, h: 0.38 });
  s.addText("@dra.daniellypinheiro · @oryaestetica", { x: 4.7, y: 4.8, w: 4.6, h: 0.48, fontSize: 18, bold: true, color: C.background1, valign: "middle", margin: 0, isTextBox: true });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.75, y: 5.65, w: 4.2, h: 0.72, rectRadius: 0.36, fill: { color: C.accent2 }, line: { color: C.accent2 } });
  s.addText("AGENDE A SUA AVALIAÇÃO", { x: 0.75, y: 5.65, w: 4.2, h: 0.72, fontSize: 14, bold: true, charSpacing: 3, color: C.text1, align: "center", valign: "middle", margin: 0, isTextBox: true });

  const saida = arq("apresentacao_orya.pptx");
  await pres.writeFile({ fileName: saida });
  await applyTheme(saida, THEME);
  console.log("ok", saida);
}

main().catch((e) => { console.error(e); process.exit(1); });
