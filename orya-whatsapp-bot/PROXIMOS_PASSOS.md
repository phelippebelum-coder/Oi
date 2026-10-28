# Bot ORYA · onde paramos

## Pronto
- Código completo nesta pasta (branch `orya-whatsapp-bot`): webhook da Meta, cérebro com o roteiro SDR da ORYA, ficha/categorização, agenda, passagem para a equipe, lembretes, follow-up, página de teste (`/teste`), painel (`/painel`) e teste automático de qualidade (`avaliar.py`).
- 11 testes técnicos passando. O formato da chamada ao Claude foi conferido.
- Ainda NÃO testado com o Claude de verdade (faltava a chave da API).

## Próximo passo: testar na página de teste
1. Criar a API key em console.anthropic.com (com créditos).
2. Subir no Railway: repositório **Oi**, branch `orya-whatsapp-bot`, Root Directory `orya-whatsapp-bot`; variáveis `ANTHROPIC_API_KEY` e `PAINEL_SENHA`; volume em `/data`; gerar domínio.
3. Abrir `https://SEU-DOMINIO/teste`, conversar como cliente e mandar as conversas pro Claude ajustar o tom.

## Informações que faltam (Phelippe)
- [ ] Tabela de preços → `prompts/precos.md` (só o blefaro plasma está preenchido)
- [ ] A avaliação é gratuita? Abate do procedimento?
- [ ] Horários reais das avaliações (Dra. Danielly e Dra. Suelen) → `prompts/agenda.json`
- [ ] Números da equipe que recebem avisos → variável `EQUIPE_WHATSAPP`
- [ ] Como o bot se apresenta → variável `ATENDENTE` (hoje: "o atendimento da ORYA")

## Depois de aprovar o comportamento
- Ligar no WhatsApp: Meta Business verificado, app no Meta for Developers, número (11) 2959-3266 em coexistência, webhook com `messages` e `smb_message_echoes` (passo a passo no README).
- Criar os templates de lembrete e de aviso à equipe.
- Opcional: integração com o Google Agenda e evento de conversão "agendou" para os anúncios.
