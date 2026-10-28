# Bot ORYA · onde paramos

## Pronto
- Código completo nesta pasta (branch `orya-whatsapp-bot`): webhook da Meta, cérebro com o roteiro SDR da ORYA, ficha/categorização, agenda, passagem para a equipe, lembretes, follow-up, página de teste (`/teste`), painel (`/painel`) e teste automático de qualidade (`avaliar.py`).
- 29 testes técnicos passando. O formato da chamada ao Claude foi conferido.
- No ar no Render (aurora-orya, plano Starter, disco em /data) e testado com o Claude de verdade na página /teste em 28/10: aprovado.

## Próximo passo: testar na página de teste
1. Criar a API key em console.anthropic.com (com créditos).
2. Hospedagem: Render (Railway estava com cadastros bloqueados). Web Service Docker, branch `orya-whatsapp-bot`, Root Directory `orya-whatsapp-bot`, Starter, disco 1 GB em `/data`, health check `/`.
3. Abrir `https://SEU-DOMINIO/teste`, conversar como cliente e mandar as conversas pro Claude ajustar o tom.

## Atualizado (28/10)
- Só Dra. Danielly; avaliações seg-sáb 8h-20h.
- Preços: botox (terço superior R$ 1.100, face completa R$ 1.400), labial 1 ml R$ 1.100, limpeza R$ 150, drenagem R$ 229 ou 5 sessões R$ 1.037, avaliação R$ 200 abatida (falta não devolve). 10x sem juros ou 10% no Pix/dinheiro. Harmonização facial/glútea e bioestimulador: só na avaliação.
- Follow-up 1, 3, 7, 15, 30 dias + mensal com grupo VIP; resgate zera a cadência.
- Relatório por e-mail (avisos na hora + diário às 20h), pedido de ligação para +55 11 97612-2138.
- Cadastro: nome, sobrenome e e-mail (sem insistir); exportação CSV no painel.
- Tom closer + redireciona assuntos fora da estética.

## Atualizado (28/10, parte 2)
- Avaliação paga antecipada por Pix ou link de cartão; controle "pagamento pendente/pago" no painel.
- Domingo sob consulta (bot avisa a equipe e oferece sábado); agenda flexível.
- Dra. Danielly: especialização em harmonização facial em Paris + pós em biomedicina estética.
- Regiões: Jardim São Paulo (perto de Santana e Shopping Center Norte), Tatuapé, Jardins.
- Rapport: espelha emoji, risada e estilo; nome, sobrenome e e-mail só no fim.
- Antes e depois por procedimento (upload no painel, com confirmação do termo de imagem).
- Resgate e follow-ups com novidades da área de interesse, grupo VIP e ligação com o executivo de vendas.
- Áudio de lead com potencial → pedido de ligação para o Phelippe.
- Promoções do mês em `prompts/promocoes.md`.

## Atualizado (28/10, parte 3)
- Três unidades (Jardim São Paulo, Tatuapé, Jardins), agenda única da Dra.; Tatuapé e Jardins "sob consulta" até termos endereço e dias.
- PDF de apresentação (`materiais/apresentacao_orya.pdf`) com jornada em 5 etapas e metodologias nomeadas; bot envia.
- Plano Olhar Leve Anual: botox terço superior 4x/ano, R$ 3.080 (30% off) em 10x de R$ 308.
- Pix: CNPJ 67.898.906/0001-46. Relatórios para Phelippe.belum@blmengenharia.com.br.

## Atualizado (28/10, parte 4)
- PDF aprovado; Tatuapé e Jardins sem endereço (consultório conforme disponibilidade, equipe confirma).
- Pagamento até 24 h antes (ou 3 h antes se em cima da hora); lembrete + cancelamento automático.
- Google Agenda (oryaesteticavancada@gmail.com) via conta de serviço: lê ocupados e cria eventos.
- E-mail sai pelo Gmail da ORYA (senha de app); relatórios para ORYA + BLM.
- Grupo VIP configurado. Face completa anual e blefaro: sem valor por mensagem. Link de cartão: equipe envia.

## Atualizado (28/10, parte 5)
- Apresentação refeita no estilo da institucional da BLM (16:9, 10 slides, mais impactante).
- Dra. Danielly: especialização em anatomia aplicada à harmonização facial (Paris).
- Agenda da Dra.: 8h às 18h, seg a sáb; após 18h e domingo, sob consulta.

## Atualizado (28/10, parte 6)
- Apresentação com logo oficial e marrom mais claro; versão PowerPoint editável (`materiais/apresentacao_orya.pptx`).
- Bot se chama Aurora. Avisos no WhatsApp para Phelippe (+55 11 97612-2138) e Dra. (+55 11 99358-0088). Relatórios para os dois e-mails.
- Pagamento vencido: só avisa a equipe (não cancela sozinho). Plano anual: R$ 3.080 em qualquer forma.
- Planilha para preencher os preços: `materiais/tabela_precos_orya.xlsx`.

## NO AR no WhatsApp oficial (28/10)
- App "Aurora ORYA" publicado na Meta, webhook `https://aurora-orya.onrender.com/webhook` (messages + echoes).
- Número oficial +55 11 2959-3266: phone id 1291567380699182, WABA 1204872868495909 (aurora-bot com acesso total).
- A Aurora assina o app na WABA sozinha ao iniciar; conferir em `/api/whatsapp/status`.

## Próximos passos
- [ ] Forma de pagamento na Meta (WhatsApp Manager) para enviar modelos.
- [ ] Criar e aprovar os modelos: follow-ups (d1, d3, d7, d15, d30, mensal VIP), lembrete, pagamento e aviso à equipe; preencher `FOLLOWUP_TEMPLATES` e `TEMPLATE_*` no Render.
- [ ] Senha de app do Gmail (SMTP_*) para os e-mails e relatório diário.
- [ ] Conta de serviço do Google Agenda.

## Informações que faltam (Phelippe)
- [ ] TROCAR a senha da conta Google da ORYA (foi enviada no chat)
- [ ] Conta de serviço do Google Agenda + senha de app do Gmail (README, Passo 4)
- [ ] Preencher `materiais/tabela_precos_orya.xlsx` e devolver
- [ ] ID do conjunto de dados (Pixel) da ORYA no Gerenciador de Eventos do Meta (conversão "agendou")
- [ ] Fotos de antes e depois, fotos da Dra./clínica, promoções do mês, lista de clientes antigas (opcionais)
- [ ] Confirmar: sábado 8h-18h e avaliação de 30 min (padrões atuais)

