# ORYA · Atendimento automático no WhatsApp (Claude)

O bot faz o pré-atendimento da ORYA 24 horas por dia no WhatsApp oficial (Cloud API da Meta). Ele segue o roteiro de SDR da clínica: acolhe a lead, descobre a queixa, faz a triagem de saúde, passa o preço só quando faz sentido, agenda a avaliação em horário livre e entrega para a equipe um resumo de cada cliente.

## O que ele faz

- **Responde 24h** com tom humanizado: balões curtos, uma pergunta por vez, usa o nome e as palavras da cliente.
- **Categoriza cada contato** numa ficha: lead novo ou cliente de retorno, status, temperatura (quente/morna/fria), etapa, interesses, queixa, triagem, objeções, origem (anúncio).
- **Agenda a avaliação** consultando a agenda interna, sempre oferecendo duas opções reais. Também remarca e cancela.
- **Avisa a equipe** no WhatsApp e no painel quando agenda, quando precisa de uma pessoa ou quando falta preço na tabela.
- **Sai de cena sozinho** quando alguém da equipe responde pelo app WhatsApp Business (modo coexistência) e volta depois de 12h, ou quando vocês mandarem pelo painel.
- **Lembretes** D-1 e 2h antes da avaliação, e **um follow-up** para quem parou de responder (dentro da janela de 24h).
- **Entende fotos** e pede com naturalidade pra escrever quando recebe áudio.
- **Reconhece clientes antigas** (importe a lista no painel) e já fala de manutenção.
- **Compliance**: preço só no individual, sem promessa de resultado, sem escassez falsa, sem antes e depois, honesta se perguntarem se é robô (CFBM Res. 330/2020 e LGPD).
- Opcional: avisa o Meta (API de Conversões) quando uma lead que veio de anúncio **agenda**, para o algoritmo buscar quem agenda, não só quem clica.

## Estrutura

```
prompts/sdr_orya.md   ← comportamento do bot (edite aqui o tom e as regras)
prompts/precos.md     ← tabela de preços (PREENCHER antes de ligar)
prompts/agenda.json   ← (opcional) horários de atendimento; sem ele vale seg-sex 9h-20h e sáb 9h-14h
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
4. Teste automático (7 clientes simuladas: só quer preço, "vou falar com meu marido", gestante, cliente de retorno, "é robô?", intercorrência e agendamento rápido). Um juiz dá nota a cada conversa:
   ```bash
   python avaliar.py
   ```
   O resultado sai em `relatorio_avaliacao.md`.

## Passo 2 · Colocar no ar (Railway)

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
6. No app da Meta → WhatsApp → **Configuração → Webhook**:
   - URL de callback: `https://SEU-DOMINIO/webhook`
   - Token de verificação: o mesmo `WHATSAPP_VERIFY_TOKEN`
   - Assine os campos **messages** e **smb_message_echoes** (este último é o que faz o bot pausar quando a equipe responde pelo celular).
7. Mande uma mensagem de outro celular para o número da clínica e acompanhe no painel.

### Templates (para falar fora da janela de 24h)

Pelas regras do WhatsApp, depois de 24h sem mensagem da cliente só dá pra escrever com template aprovado. Crie no Gerenciador do WhatsApp (categoria **Utilidade**) e coloque o nome nas variáveis:

- `TEMPLATE_LEMBRETE`, exemplo de corpo: `Oi, {{1}}! Passando pra lembrar da sua avaliação na ORYA dia {{2}} às {{3}}. Rua Viri, 62, Jardim São Paulo. Posso confirmar sua presença?`
- `TEMPLATE_AVISO_EQUIPE`, exemplo: `Aviso do atendimento ORYA: {{1}}` (para a equipe receber avisos mesmo sem conversa aberta com o número).

Sem template, o lembrete só sai se a cliente falou nas últimas 24h; os demais ficam como aviso no painel.

## Ajustes do dia a dia

- **Preços**: edite `prompts/precos.md`. Onde estiver `[PREENCHER]`, o bot diz que vai confirmar e avisa a equipe.
- **Horários e bloqueios** (feriados, férias, agenda da Dra. Suelen diferente): crie `prompts/agenda.json`, por exemplo:
  ```json
  {
    "duracao_min": 30,
    "avaliacoes_simultaneas": 1,
    "expediente": {"0": [["09:00","12:00"],["14:00","20:00"]], "1": [["09:00","20:00"]], "2": [["09:00","20:00"]],
                   "3": [["09:00","20:00"]], "4": [["09:00","20:00"]], "5": [["09:00","14:00"]]},
    "profissionais": {"suelen": {"expediente": {"1": [["13:00","20:00"]], "3": [["13:00","20:00"]]}}},
    "bloqueios": ["2026-11-02", "2026-11-15", "2026-11-20 14:00"]
  }
  ```
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
