# Bot ORYA · onde paramos

## Pronto
- Código completo nesta pasta (branch `orya-whatsapp-bot`): webhook da Meta, cérebro com o roteiro SDR da ORYA, ficha/categorização, agenda, passagem para a equipe, lembretes, follow-up, página de teste (`/teste`), painel (`/painel`) e teste automático de qualidade (`avaliar.py`).
- 23 testes técnicos passando. O formato da chamada ao Claude foi conferido.
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

## Informações que faltam (Phelippe)
- [ ] Endereços das unidades Tatuapé e Jardins + dias/horários da Dra. em cada uma
- [ ] Aprovar o PDF e os nomes das metodologias
- [ ] Plano anual: vale também para face completa (R$ 3.920 com 30%)? Tem desconto extra no Pix?
- [ ] Senha do e-mail Phelippe.belum@blmengenharia.com.br (vai só na variável SMTP_SENHA do Railway)
- [ ] Link de cartão: fixo (bot envia) ou a equipe gera para cada cliente?
- [ ] Avaliação sem pagamento: cancelar o horário depois de quantas horas?
- [ ] Fotos de antes e depois (botox, harmonização facial, labial, glútea): subir pelo painel
- [ ] Promoções do mês → `prompts/promocoes.md`
- [ ] Link do grupo VIP → variável `GRUPO_VIP_LINK`
- [ ] Blefaro plasma: confirmar R$ 1.000 (10x) / R$ 900 no Pix
- [ ] Chave da API do Claude + conta no Railway (para o primeiro teste real)

## Depois de aprovar o comportamento
- Ligar no WhatsApp: Meta Business verificado, app no Meta for Developers, número (11) 2959-3266 em coexistência, webhook com `messages` e `smb_message_echoes` (passo a passo no README).
- Criar os templates de lembrete e de aviso à equipe.
- Opcional: integração com o Google Agenda e evento de conversão "agendou" para os anúncios.
