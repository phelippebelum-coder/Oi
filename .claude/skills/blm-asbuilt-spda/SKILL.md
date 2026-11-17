---
name: blm-asbuilt-spda
description: Gera o as built de SPDA no padrão BLM Engenharia (DWG + DXF + PDF, folha A0/A1 com carimbo, legenda, notas, quadros e detalhes típicos) a partir de planta do cliente (PDF/DWG) ou print do Google Maps com marcações de campo. Usar quando o Phelippe pedir as built, projeto de SPDA em AutoCAD, "passar o levantamento para o CAD" ou mandar print/folha marcada com descidas, captores e gaiolas.
---

# As built de SPDA - padrão BLM

O código fica em `spda-asbuilt/` (leia o README de lá). Padrão da empresa em `spda-asbuilt/blm_cad/folha.py`
(normas, notas-padrão, carimbo, símbolos). Cada obra é uma pasta `spda-asbuilt/projetos/AAAA-MM_CLIENTE/`
com `levantamento.py` (dados) e `gerar.py` (copiar do projeto mais parecido).

## Entradas e de onde tirar
1. **Base**: planta do cliente (DWG/PDF vetorial -> `blm_cad/base_pdf.py`) ou, sem planta, contornos traçados
   sobre o print aéreo (ver projeto FB_JD_CONCEICAO). DWG do cliente: converter para DXF com
   `xvfb-run -a ODAFileConverter <dir_in> <dir_out> ACAD2018 DXF 0 1 "*.dwg"`.
2. **Marcações de campo**:
   - folha impressa: X = descida, Δ = captor Franklin (haste), O = minicaptor (projeto HGDP: registro foto->planta);
   - print colorido: azul = Franklin, vermelho = descida, verde = minicaptor, amarelo = gaiola ->
     `python -m blm_cad.marcacoes print.png` e CONFERIR `conferencia.png` (falsos positivos: lonas/telhados azuis;
     pontos vermelhos fracos podem não ser detectados).
3. **Dados do cliente**: procurar no Google Drive (pasta do cliente/relatório/laudo): razão social, CNPJ,
   endereço, contrato, laudo de referência, ensaios. Relatórios BLM citam a norma vigente - seguir a mesma.
4. **Escala sem planta**: vagas de estacionamento (~2,5 m de largura x 4,5-5 m), quadra, ou medida informada.
   Declarar "escala aproximada" na prancha enquanto não houver medida real.

## Regras de conteúdo (as built honesto)
- Só desenhar como existente o que foi visto ou consta em laudo; o resto vai para NOTAS ("não levantado",
  "posição indicativa"). Ex.: descidas estruturais não visíveis = símbolo próprio + "posição indicativa".
- Descidas projetadas na fachada mais próxima; minicaptores sobre a gaiola; captores alinhados às linhas
  da cobertura quando o Phelippe pedir "centralizar".
- Quantidades conferem com o relatório/laudo (ex.: nº de conexões de ensaio = nº de descidas).
- Rodar a verificação interna `blm_cad/verifica.py` (espaçamento de descidas por classe) e AVISAR o
  Phelippe dos resultados - é insumo para laudo/proposta de adequação, não vai na prancha.

## Saída e entrega
- `python gerar.py` -> `saida/` com DXF, PDF e DWG (DWG precisa do ODA File Converter; o setup do
  ambiente instala). Conferir o PDF renderizando em PNG antes de entregar.
- Entregar: prévia PNG (celular) + DWG + PDF; subir DWG e PDF na pasta do cliente no Drive
  (mesma pasta do relatório) com nome "AS BUILT SPDA - CLIENTE - UNIDADE - <codigo>_Rxx".
- Não versionar arquivos do cliente no git (saida/ e levantamento_marcado.* estão no .gitignore).
- Pendências para o Phelippe sempre em lista curta no fim (nomes de blocos, pontos a confirmar).
