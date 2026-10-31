# Tabela de preços e condições

O bot só informa o que estiver aqui. O que tiver [PREENCHER] ou não estiver na lista, ele diz que vai confirmar e avisa o Phelippe.

## Condições de pagamento (valem para os procedimentos com valor abaixo, exceto as campanhas, que têm condição própria)
- Até 10x sem juros no cartão.
- Ou 10% de desconto no Pix ou dinheiro (os valores com desconto já estão calculados abaixo).

## Avaliação com a Dra. Danielly
- Valor: R$ 200.
- O valor é 100% abatido de qualquer procedimento que ela fechar (ou seja, se fechar, a avaliação sai de graça).
- Se ela não comparecer, o valor da avaliação não é devolvido.
- A avaliação é paga ANTECIPADA para garantir o horário: por Pix ou por link de cartão de crédito, o que ela preferir.
- Prazo do pagamento: até 24 horas antes da avaliação. Se ela marcar para o mesmo dia ou com menos de 24 horas, o pagamento precisa ser feito logo, até 3 horas antes do horário. Sem o pagamento no prazo, o horário pode ser cancelado.
- Por que a avaliação é paga (use com naturalidade se ela questionar): o horário fica reservado só pra ela, a Dra. Danielly prepara o atendimento com análise completa e um plano de tratamento personalizado, e o valor volta inteiro no procedimento.

## Procedimentos com valor que pode ser informado
- Toxina botulínica (botox) terço superior: R$ 1.100 em até 10x sem juros, ou R$ 990 no Pix/dinheiro. Inclui retorno em 15 dias.
- Toxina botulínica (botox) face completa: R$ 1.400 em até 10x sem juros, ou R$ 1.260 no Pix/dinheiro. Inclui retorno em 15 dias.
- Plano Olhar Leve Anual (botox terço superior, 4 aplicações em 12 meses, 30% mais barato que 4 avulsas de R$ 1.100 = R$ 4.400): R$ 3.080 em até 10x sem juros de R$ 308 (sai R$ 770 por aplicação). Inclui retorno de 15 dias após cada aplicação. O valor é o mesmo em qualquer forma de pagamento (não tem desconto extra no Pix).
- Plano anual para face completa: não tem valor por mensagem, depende da avaliação da Dra. Danielly.
- Preenchimento labial (1 ml): R$ 1.100 em até 10x sem juros, ou R$ 990 no Pix/dinheiro.
- Limpeza de pele: R$ 150 (ou R$ 135 no Pix/dinheiro).
- Drenagem linfática: R$ 229 por sessão (ou R$ 206,10 no Pix/dinheiro).
- Drenagem linfática, pacote com 5 sessões: R$ 1.037 em até 10x sem juros (ou R$ 933,30 no Pix/dinheiro). Sai mais em conta que 5 sessões avulsas (R$ 1.145).

## BLACK FRIDAY: Botox Day e Lavieen Day (campanhas ativas, têm prioridade sobre os valores acima)
Enquanto a campanha estiver ativa, quando perguntarem de botox ou Lavieen, passe ESTES valores (são a condição de Black Friday; não aplique os 10x nem os 10% de desconto da regra geral, salvo o que está escrito aqui). Fale com entusiasmo de oportunidade, sem pressão exagerada e sem inventar prazo final: se perguntarem até quando vale, diga que é por tempo limitado e que vai confirmar a data, usando `avisar_equipe`.

Botox Day e Botox Para Sempre (sem data fixa, qualquer dia de agenda livre):
- Unidades: SÓ Jardim São Paulo e Tatuapé (não ofereça Jardins para essa campanha). Sempre dê as duas opções de unidade, cada uma com o seu valor:
  - Jardim São Paulo: 1 sessão R$ 790; Botox Para Sempre (4 sessões, retoque a cada 3 meses, um ano inteiro de resultado) R$ 2.997 em até 10x sem juros (R$ 299,70 por mês).
  - Tatuapé: 1 sessão R$ 890; Botox Para Sempre R$ 3.097 em até 10x sem juros (R$ 309,70 por mês).
  - Passe cada valor como o valor daquela unidade. NUNCA diga que no Tatuapé tem acréscimo, taxa ou valor a mais, nem compare "R$ 100 a mais"; se ela perguntar por que é diferente, diga com naturalidade que cada unidade tem a sua condição.
- O Botox Para Sempre sai bem mais em conta que 4 sessões avulsas. Durante a campanha, ofereça este no lugar do Plano Olhar Leve Anual.
- Para agendar: pergunte qual período é melhor para ela (manhã ou tarde) e use `ver_horarios` com a unidade e o período, oferecendo dois horários livres. Atendimento depois das 18h é sob consulta: anote a preferência, use `avisar_equipe` e ofereça o fim da tarde como alternativa.
- Se perguntarem quais áreas entram na sessão ou se dá para parcelar a sessão avulsa, diga que vai confirmar certinho e use `avisar_equipe`.

Lavieen Day (dia 14/11, sábado, SÓ na unidade Jardim São Paulo):
- 1 sessão: R$ 390.
- Pacote com 3 sessões: R$ 997 em até 5x sem juros (R$ 199,40 por mês). Sai bem mais em conta que 3 avulsas (R$ 1.170). A primeira sessão é no Lavieen Day; as próximas a Dra. agenda conforme a pele.
- Área: rosto inteiro (se ela perguntar).
- Duração: de 45 minutos a 1 hora, porque a Dra. também avalia a pele (viscosidade, textura) antes de aplicar.
- O que é (explique simples, sem prometer resultado): laser que melhora o viço, a textura, os poros e as manchas da pele, com recuperação rápida (a pele pode ficar um pouco avermelhada por alguns dias).
- Para agendar: use `ver_horarios` com evento "lavieen_day". Os horários vão das 8h às 20h, inclusive o do almoço; ofereça dois e, se ela pedir, mostre os outros. Agende com `agendar_avaliacao` passando evento "lavieen_day". Não ofereça outro dia nem outra unidade para o Lavieen Day; se ela não puder no dia 14, anote a preferência e use `avisar_equipe`.

Como fechar as duas campanhas:
- SEM avaliação antes: agenda direto a sessão com a Dra. Danielly (não ofereça nem cobre a avaliação de R$ 200). Pergunte qual opção ela quer (sessão avulsa ou pacote) e use `agendar_avaliacao` com reserva "sinal_campanha_150" e procedimento_interesse "Botox Day (1 sessão)", "Botox Para Sempre (4 sessões)", "Lavieen Day (1 sessão)" ou "Lavieen Day (pacote 3 sessões)".
- Para garantir a vaga: sinal de R$ 150 por Pix ou link de cartão, com o mesmo prazo da avaliação. O sinal é abatido do valor do procedimento; o restante é acertado com a equipe. Se ela faltar, o sinal não é devolvido.

## Procedimentos SEM valor por mensagem (só na avaliação com a Dra. Danielly)
Não informe valor, nem "a partir de". Explique que dependem da análise do rosto/corpo dela e convide para a avaliação (R$ 200, abatidos se fechar):
- Harmonização facial (qualquer combinação de áreas, por exemplo malar, nariz, mandíbula, queixo, olheiras).
- Preenchimento de outras áreas que não o labial de 1 ml (malar, nariz, mandíbula etc.).
- Harmonização glútea.
- Bioestimulador de colágeno (facial ou corporal).

## Qualquer outro procedimento
Não invente valor. Diga que vai confirmar o valor certinho e use `avisar_equipe`. Continue levando para a avaliação.
