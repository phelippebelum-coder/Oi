# As built de SPDA — BLM Engenharia

Este gerador monta a prancha de as built de SPDA (DXF + PDF) no padrão BLM. Ele parte de dois insumos:

- a planta do cliente em **PDF vetorial**;
- o **levantamento de campo**: a folha marcada à mão, fotografada.

## Estrutura

```
blm_cad/                 padrão da empresa (vale para todos os projetos)
  folha.py               normas, notas-padrão, camadas, cores, símbolos, carimbo, legenda
  base_pdf.py            importa a planta PDF do cliente como base vetorial
  vetoriza_logo.py       converte o logo PNG em vetor (hachura) para o carimbo
  assets/                logo
projetos/<data>_<cliente>/
  levantamento.py        dados do levantamento (descidas, Franklin, minicaptores, sem SPDA)
  gerar.py               gera a prancha
  saida/                 DXF + PDF gerados (fora do git)
```

## Como gerar

```
pip install ezdxf pymupdf opencv-python-headless numpy
cd projetos/2026-11_HGDP
python gerar.py --base /caminho/HGDP-Imp_1.500.pdf
```

## Ferramentas

- `python -m blm_cad.marcacoes print.png` lê os pontos coloridos de um print marcado e gera `conferencia.png` e `marcacoes.json`.
  Cores: azul = Franklin, vermelho = descida, verde = minicaptor, amarelo = gaiola.
- `blm_cad/verifica.py` faz uma conferência interna do espaçamento entre descidas por classe (NBR 5419-3). O resultado não vai para a prancha.
- `python -m blm_cad.extrai_detalhes prancha.dxf` monta a biblioteca de detalhes típicos (`assets/detalhes_tipicos.dxf`).
  Para colocar detalhes numa prancha, passe `detalhes=(7, 2)` em `folha.prancha`.
- A skill `.claude/skills/blm-asbuilt-spda` descreve o fluxo completo para sessões futuras.

## Manutenção do padrão

- **Norma nova / notas-padrão / dados da empresa:** editar `NORMAS` e `EMPRESA` em `blm_cad/folha.py`.
- **Logo novo:** salvar o PNG em `blm_cad/assets/` e rodar `python -m blm_cad.vetoriza_logo assets/novo_logo.png`.
- **Símbolos e cores:** editar `_cria_blocos` e `COR` em `blm_cad/folha.py`.

Depois de qualquer mudança, rode `gerar.py` de novo. Todos os projetos pegam o padrão atualizado.

## Convenção da marcação de campo

| Marca | Significado |
|---|---|
| X | descida |
| Δ | haste / captor Franklin |
| O | minicaptor |
| em branco | não levantado (não aparece no desenho) |

O que não for verificado em campo fica registrado nas notas da prancha. Não é desenhado como se existisse.

## DWG

Com o ODA File Converter instalado (gratuito), o `gerar.py` também grava o DWG no formato AutoCAD 2018, ao lado do DXF e do PDF.
Sem ele, abra o DXF no AutoCAD e use **Salvar como → DWG**.

Para instalar no Linux:
`apt-get install ./ODAFileConverter_*.deb xvfb libopengl0`
O instalador fica em opendesign.com/guestfiles.
