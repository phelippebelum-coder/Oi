# Bot ORYA · onde paramos

## Pronto
- Código completo nesta pasta (branch `orya-whatsapp-bot`): webhook da Meta, cérebro com o roteiro SDR da ORYA, ficha/categorização, agenda, passagem para a equipe, lembretes, follow-up, página de teste (`/teste`), painel (`/painel`) e teste automático de qualidade (`avaliar.py`).
- 17 testes técnicos passando. O formato da chamada ao Claude foi conferido.
- Ainda NÃO testado com o Claude de verdade (faltava a chave da API).

## Próximo passo: testar na página de teste
1. Criar a API key em console.anthropic.com (com créditos).
2. Subir no Railway: repositório **Oi**, branch `orya-whatsapp-bot`, Root Directory `orya-whatsapp-bot`; variáveis `ANTHROPIC_API_KEY` e `PAINEL_SENHA`; volume em `/data`; gerar domínio.
3. Abrir `https://SEU-DOMINIO/teste`, conversar como cliente e mandar as conversas pro Claude ajustar o tom.

## Atualizado (28/10)
- Só Dra. Danielly; avaliações seg-sáb 8h-20h.
- Preços: botox (terço superior R$ 1.100, face completa R$ 1.400), labial 1 ml R$ 1.100, limpeza R$ 150, drenagem R$ 229 ou 5 sessões R$ 1.037, avaliação R$ 200 abatida (falta não devolve). 10x sem juros ou 10% no Pix/dinheiro. Harmonização facial/glútea e bioestimulador: só na avaliação.
- Follow-up 1, 3, 7, 15, 30 dias + mensal com grupo VIP; resgate zera a cadência.
- Relatório por e-mail (avisos na hora + diário às 20h), pedido de ligação para +55 11 97612-2138.
- Cadastro: nome, sobrenome e e-mail (sem insistir); exportação CSV no painel.
- Tom closer + redireciona assuntos fora da estética.

## Informações que faltam (Phelippe)
- [ ] E-mail que recebe os relatórios + um Gmail com senha de app para enviar
- [ ] Pagamento da avaliação de R$ 200: Pix antecipado? na clínica? (`prompts/precos.md`)
- [ ] Domingo tem atendimento?
- [ ] Blefaro plasma: confirmar R$ 1.000 (10x) / R$ 900 no Pix (veio da skill antiga)
- [ ] Link do grupo VIP → variável `GRUPO_VIP_LINK`
- [ ] Como o bot se apresenta → variável `ATENDENTE` (hoje: "o atendimento da ORYA")

## Depois de aprovar o comportamento
- Ligar no WhatsApp: Meta Business verificado, app no Meta for Developers, número (11) 2959-3266 em coexistência, webhook com `messages` e `smb_message_echoes` (passo a passo no README).
- Criar os templates de lembrete e de aviso à equipe.
- Opcional: integração com o Google Agenda e evento de conversão "agendou" para os anúncios.
