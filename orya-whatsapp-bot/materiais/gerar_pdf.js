// Gera apresentacao_orya.pdf a partir de apresentacao.html (node gerar_pdf.js)
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + path.join(__dirname, 'apresentacao.html'), { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready);
  await p.pdf({ path: path.join(__dirname, 'apresentacao_orya.pdf'), width: '1920px', height: '1080px', printBackground: true });
  await b.close();
})();
