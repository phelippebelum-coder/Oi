# ORYA · Atendimento automático no WhatsApp (Claude)

O bot faz o pré-atendimento da ORYA 24 horas por dia no WhatsApp oficial (Cloud API da Meta). Ele segue o roteiro de SDR da clínica: acolhe a lead, descobre a queixa, faz a triagem de saúde, passa o preço só quando faz sentido, agenda a avaliação em horário livre e entrega para a equipe um resumo de cada cliente.

## O que ele faz

- **Responde 24h** com tom humanizado: balões curtos, uma pergunta por vez, usa o nome e as palavras da cliente.
- **Categoriza cada contato** numa ficha: lead novo ou cliente de retorno, status, temperatura (quente/morna/fria), etapa, interesses, queixa, triagem, objeções, origem (anúncio).
- **Agenda a avaliação** consultando a agenda interna, sempre oferecendo duas opções reais. Também remarca e cancela.
- **Avisa a equipe** no WhatsApp e no painel quando agenda, quando precisa de uma pessoa ou quando falta preço na tabela.
- **Sai de cena sozinho** quando alguém da equipe responde pelo app WhatsApp Business (modo coexistência) e volta depois de 12h, ou quando vocês mandarem pelo painel.
- **Lembretes** D-1 e 2h antes da avaliação.
- **Follow-up em cadência** para quem parou de responder: 1, 3, 7, 15 e 30 dias, sempre às 10h do dia da etapa (contato às 4h da manhã → follow-up às 10h do dia seguinte), só entre 8h e 18h e nunca no domingo, e depois uma mensagem por mês com convite para o grupo VIP. Se a lead responder, a cadência zera e o bot recomeça a conversa (resgate).
- **Relatórios por e-mail**: aviso na hora quando agenda, pede ligação ou passa para a equipe, e um relatório diário (20h) com todos os leads, categoria, e-mail e resumo da conversa.
- **Pedido de ligação**: quando a cliente quer que liguem ou precisa de atenção maior, o Phelippe recebe no WhatsApp e no e-mail o número pra ligar.
- **Cadastro para e-mail marketing**: pede nome, sobrenome e e-mail só no fim, na fase de agendamento (sem insistir). O painel exporta a lista em CSV.
- **Antes e depois**: vocês sobem uma foto por procedimento (botox, harmonização facial, labial, harmonização glútea) na aba "Antes e depois" do painel; o bot envia como referência quando a cliente demonstra interesse, com a legenda de autorização.
- **Pagamento antecipado da avaliação** (Pix ou link de cartão): o bot pergunta a preferência, envia a chave/link (se configurados) ou avisa a equipe para enviar. No painel, cada avaliação mostra "pagamento pendente" até vocês marcarem como pago.
- **Promoções do mês**: escreva em `prompts/promocoes.md`; o bot usa nos follow-ups, no resgate e na conversa.
- **Três unidades** (Jardim São Paulo, Tatuapé e Jardins): a cliente escolhe; a agenda da Dra. é única, então um horário ocupado numa unidade some das outras. No Tatuapé e nos Jardins o consultório depende da disponibilidade, então ficam "sob consulta" (o bot anota a preferência e avisa a equipe, que confirma local e horário).
- **Prazo do pagamento**: a avaliação precisa ser paga até 24 h antes (ou até 3 h antes, se marcada em cima da hora). O bot explica o prazo, lembra a cliente 2 h antes do prazo, avisa a equipe para marcar "pago" no painel e, vencido o prazo sem pagamento, avisa de novo para a equipe decidir (com `CANCELAR_SEM_PAGAMENTO=1`, cancela sozinho, também no Google Agenda).
- **Apresentação em PDF** (`materiais/apresentacao_orya.pdf`): a Dra., a jornada em 5 etapas, as metodologias, o Plano Olhar Leve Anual e as unidades. O bot envia quando a cliente quer entender como funciona. Para mudar o texto, edite `materiais/apresentacao.html` e rode `node materiais/gerar_pdf.js`, ou suba outro PDF no painel. A mesma apresentação existe em PowerPoint editável (`materiais/apresentacao_orya.pptx`, gerada por `materiais/gerar_pptx.js`); as logos oficiais ficam em `materiais/logo/`.
- **Entende fotos** e pede com naturalidade pra escrever quando recebe áudio.
- **Reconhece clientes antigas** (importe a lista no painel) e já fala de manutenção.
- **Compliance**: preço só no individual, sem promessa de resultado, sem escassez falsa, sem antes e depois, honesta se perguntarem se é robô (CFBM Res. 330/2020 e LGPD).
- Opcional: avisa o Meta (API de Conversões) quando uma lead que veio de anúncio **agenda**, para o algoritmo buscar quem agenda, não só quem clica.

## Estrutura

```
prompts/sdr_orya.md   ← comportamento do bot (edite aqui o tom e as regras)
prompts/precos.md     ← tabela de preços e regras de pagamento
prompts/promocoes.md  ← promoções e novidades do mês (editar todo mês)
prompts/agenda.json   ← (opcional) horários de atendimento; sem ele vale seg-sáb 8h-18h (após 18h e domingo: sob consulta), sempre com a Dra. Danielly
app/                  ← servidor (webhook, cérebro, ferramentas, agenda, rotinas)
static/               ← página de teste e painel
avaliar.py            ← teste automático de qualidade com clientes simuladas
tests/                ← testes técnicos (sem custo de API)
```

## Passo 1 · Testar antes de ligar no WhatsApp (só precisa da chave do Claude)

1. Crie uma conta em https://console.anthropic.com, adicione créditos e gere uma **API key**.
2. Rodando no computador:
   ```bash
   cd orya-whatsapp-bot
   pip install -r requirements.txt
   export ANTHROPIC_API_KEY=sk-ant-...
   uvicorn app.main:app --port 8000
   ```
3. Abra http://localhost:8000/teste e converse como se fosse uma cliente. A ficha ao lado mostra a categorização em tempo real. O painel fica em http://localhost:8000/painel.
4. Teste automático (9 clientes simuladas: só quer preço, "vou falar com meu marido", gestante, cliente de retorno, "é robô?", intercorrência, harmonização com avaliação paga, assunto fora da estética e agendamento rápido). Um juiz dá nota a cada conversa:
   ```bash
   python avaliar.py
   ```
   O resultado sai em `relatorio_avaliacao.md`.

## Passo 2 · Colocar no ar (Railway ou Render)

No Render: New → Web Service → repositório Oi, Language Docker, Branch `orya-whatsapp-bot`, Root Directory `orya-whatsapp-bot`, plano Starter, as mesmas variáveis abaixo mais `DATA_DIR=/data`, disco de 1 GB em `/data` e Health Check Path `/`.

No Railway:

1. Em https://railway.com: **New Project → Deploy from GitHub repo** → escolha este repositório e, em *Settings → Root Directory*, coloque `orya-whatsapp-bot`.
2. Em **Variables**, cole as variáveis do `.env.example` (no mínimo `ANTHROPIC_API_KEY` e `PAINEL_SENHA`).
3. Adicione um **Volume** montado em `/data` (é onde ficam conversas, fichas e agenda).
4. Em *Settings → Networking*, gere um domínio. Teste em `https://SEU-DOMINIO/teste` (usuário qualquer, senha = `PAINEL_SENHA`).

## Passo 3 · Ligar no WhatsApp da ORYA (Meta)

1. **Meta Business Manager** da ORYA verificado (business.facebook.com → Configurações → Central de segurança).
2. Em https://developers.facebook.com: **Criar app → tipo Empresa → adicionar o produto WhatsApp**.
3. **Conectar o número (11) 2959-3266 em modo coexistência**: no fluxo de cadastro do WhatsApp (Embedded Signup / "conectar número existente do WhatsApp Business app"), escolha manter o app. Assim a equipe continua vendo e respondendo pelo celular, e o bot atende pela API. O app do WhatsApp Business precisa estar atualizado e o número ativo no app.
4. Gere um **token permanente** (usuário do sistema no Business Manager com permissão `whatsapp_business_messaging` e `whatsapp_business_management`). Copie também o **Phone Number ID**, o **WABA ID** e o **App Secret** (Configurações do app → Básico).
5. Preencha no Railway: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WABA_ID`, `META_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN` (invente uma senha) e `EQUIPE_WHATSAPP` (números que recebem os avisos).
   Para os relatórios por e-mail: `SMTP_USUARIO` (um Gmail), `SMTP_SENHA` (senha de app do Google) e `RELATORIO_EMAIL` (quem recebe).
6. No app da Meta → WhatsApp → **Configuração → Webhook**:
   - URL de callback: `https://SEU-DOMINIO/webhook`
   - Token de verificação: o mesmo `WHATSAPP_VERIFY_TOKEN`
   - Assine os campos **messages** e **smb_message_echoes** (este último é o que faz o bot pausar quando a equipe responde pelo celular).
7. Mande uma mensagem de outro celular para o número da clínica e acompanhe no painel.

### Templates (para falar fora da janela de 24h)

Pelas regras do WhatsApp, depois de 24h sem mensagem da cliente só dá pra escrever com template aprovado. Dentro das 24h o próprio Claude escreve a mensagem personalizada; depois disso entra o template.

**Follow-up** (categoria **Marketing**, cobrado por mensagem; `{{1}}` = primeiro nome). Coloque os nomes em `FOLLOWUP_TEMPLATES`. Sugestões de texto:

- `orya_followup_d1`: `Oi, {{1}}! Fiquei pensando na nossa conversa de ontem. Ficou alguma dúvida que eu possa te ajudar? 🤍`
- `orya_followup_d3`: `{{1}}, uma dúvida bem comum de quem está pensando em fazer um procedimento é se vai ficar natural. Aqui a Dra. Danielly trabalha sempre com a linha natural, começando pelo necessário. Quer que eu te explique como funciona a avaliação?`
- `orya_followup_d7`: `Oi, {{1}}! Abriram alguns horários de avaliação com a Dra. Danielly essa semana. Quer que eu veja um que encaixe na sua rotina?`
- `orya_followup_d15`: `{{1}}, passando só pra dizer que a ORYA tá aqui quando você quiser cuidar de você. É só me chamar por aqui 🤍`
- `orya_followup_d30`: `Oi, {{1}}! Tudo bem por aí? Aquele incômodo que você me contou ainda te acompanha? Se quiser, vejo um horário com a Dra. Danielly pra você.`
- `orya_mensal_vip` (`{{2}}` = link do grupo): `Oi, {{1}}! Este mês tem novidades e condições especiais aqui na ORYA. Elas saem primeiro no nosso grupo VIP: {{2}}. Se preferir, me chama aqui que te conto tudo, ou nosso executivo te liga rapidinho 🤍`

O texto do template é fixo depois de aprovado pela Meta. Para mudar a promoção do mês no template, crie um novo template (ou use um texto genérico como acima e deixe o detalhe para quando ela responder, porque aí o bot usa `prompts/promocoes.md`).

Se faltar o template de alguma etapa, o bot não envia e deixa um aviso no painel.

**Avisos e lembretes** (categoria **Utilidade**):

- `TEMPLATE_LEMBRETE`, exemplo de corpo: `Oi, {{1}}! Passando pra lembrar da sua avaliação na ORYA dia {{2}} às {{3}}. Rua Viri, 62, Jardim São Paulo. Posso confirmar sua presença?`
- `TEMPLATE_AVISO_EQUIPE`, exemplo: `Aviso do atendimento ORYA: {{1}}` (para a equipe receber avisos mesmo sem conversa aberta com o número).

Sem template, o lembrete só sai se a cliente falou nas últimas 24h; os demais ficam como aviso no painel.

## Passo 4 · Google Agenda e e-mail da ORYA

**Google Agenda** (o bot lê os horários ocupados e cria um evento para cada avaliação; férias, bloqueios e compromissos que vocês colocarem na agenda deixam de ser oferecidos):

1. Entre em https://console.cloud.google.com com a conta da ORYA e crie um projeto (ex.: "orya-bot").
2. Em *APIs e serviços → Biblioteca*, ative a **Google Calendar API**.
3. Em *APIs e serviços → Credenciais → Criar credenciais → Conta de serviço*, crie a conta (ex.: "orya-agenda"). Depois, na conta criada, aba *Chaves → Adicionar chave → JSON*. Um arquivo `.json` será baixado.
4. Abra o Google Agenda da ORYA → *Configurações da agenda* → *Compartilhar com pessoas específicas* → adicione o e-mail da conta de serviço (termina em `@...iam.gserviceaccount.com`) com a permissão **Fazer alterações nos eventos**.
5. No Railway, cole o conteúdo inteiro do `.json` em `GOOGLE_SERVICE_ACCOUNT_JSON` e deixe `GOOGLE_CALENDAR_ID=oryaesteticavancada@gmail.com`.

Nunca coloque a senha da conta Google no bot: ele não precisa dela.

**E-mail (relatórios)**: ative a verificação em duas etapas na conta da ORYA e crie uma **senha de app** em https://myaccount.google.com/apppasswords. Cole essa senha de 16 letras em `SMTP_SENHA` no Railway.

## Ajustes do dia a dia

- **Preços**: edite `prompts/precos.md`. Onde estiver `[PREENCHER]`, o bot diz que vai confirmar e avisa a equipe.
- **Unidades, horários e bloqueios**: crie `prompts/agenda.json` (substitui o padrão). Exemplo com a Dra. no Tatuapé às terças e nos Jardins às quintas à tarde:
  ```json
  {
    "duracao_min": 30,
    "antecedencia_min_horas": 2,
    "dias_a_frente": 14,
    "avaliacoes_simultaneas": 1,
    "bloqueios": ["2026-11-02", "2026-11-15", "2026-11-20 14:00"],
    "unidades": {
      "jardim_sao_paulo": {"nome": "Jardim São Paulo", "endereco": "Rua Viri, 62, Jardim São Paulo, São Paulo/SP (CEP 02046-030)",
                           "referencia": "pertinho de Santana e do Shopping Center Norte",
                           "expediente": {"0": [["08:00","18:00"]], "2": [["08:00","18:00"]], "3": [["08:00","12:00"]],
                                          "4": [["08:00","18:00"]], "5": [["08:00","18:00"]]}},
      "tatuape": {"nome": "Tatuapé", "endereco": "ENDEREÇO", "referencia": "Zona Leste",
                  "expediente": {"1": [["08:00","18:00"]]}},
      "jardins": {"nome": "Jardins", "endereco": "ENDEREÇO", "referencia": "região dos Jardins",
                  "expediente": {"3": [["13:00","18:00"]]}}
    }
  }
  ```
  (0 = segunda ... 5 = sábado, 6 = domingo. Domingo é sob consulta, então fica fora.)
  Importante: a agenda do bot é a fonte da verdade dos horários de avaliação. Se a recepção marcar avaliações por fora, bloqueie o horário aqui ou peça a integração com o Google Agenda (próxima etapa).
- **Tom e regras**: edite `prompts/sdr_orya.md`.
- **Assumir uma conversa**: responda pelo celular (o bot pausa sozinho por 12h) ou use "Pausar bot" no painel. "Devolver para o bot" reativa.

## Custos aproximados

- Claude (Opus 5.5, esforço médio): poucos centavos de dólar por conversa completa.
- Meta: responder a cliente dentro da janela de atendimento é gratuito; templates são cobrados por mensagem.
- Railway: cerca de US$ 5 a 20 por mês.

## Testes técnicos

```bash
pip install pytest
python -m pytest -q
```
