"""Rotinas em segundo plano: lembretes de avaliação e follow-up de quem parou de responder."""

import asyncio
import logging
from datetime import datetime, timedelta

from . import agenda, config, db, equipe, google_agenda, processador, relatorio, whatsapp

log = logging.getLogger("orya.rotinas")

# O que cada etapa da cadência deve trazer (cadência A da ORYA: lead que não agendou).
NOTAS_ETAPA = {
    "1": ("Ela parou de responder desde ontem. Retome com carinho a queixa ou o motivo dela, com as palavras "
          "dela, e traga algo novo e útil. Termine com uma pergunta leve."),
    "3": ("Ela está há 3 dias sem responder. Tire uma dúvida comum de quem está na fase dela (dor, naturalidade, "
          "tempo de recuperação ou como funciona a avaliação), sem cobrança."),
    "7": "Ela está há 7 dias sem responder. Ofereça duas opções reais de horário (use ver_horarios) de forma leve.",
    "15": ("Ela está há 15 dias sem responder. Conte que tem novidades justamente na área que ela procurou (use a "
           "seção de promoções e novidades, se houver), diga que a gente gostaria muito de conversar e ofereça uma "
           "ligação rápida com o nosso executivo de vendas, do time de qualidade, se ela preferir."),
    "30": ("Ela está há 30 dias sem responder. Reativação: pergunte como ela está e se aquele incômodo ainda a "
           "acompanha, conte as novidades da área dela e convide para o grupo VIP ({link}). Lembre que a agenda "
           "é flexível."),
    "mensal": ("Mensagem mensal de relacionamento: conte as promoções e novidades do mês (seção de promoções e "
               "novidades; se estiver vazia, fale só em novidades e condições especiais, sem inventar), puxando "
               "pela área de interesse dela, e convide para o grupo VIP da ORYA no WhatsApp ({link}). "
               "Feche oferecendo um horário ou uma ligação com o nosso executivo de vendas."),
}
REGRA_FOLLOWUP = (" Envie UM follow-up curto (1 ou 2 balões), humano, como alguém que lembrou dela de verdade. "
                  "Nada de 'e aí?', nada de cobrança pelo sumiço. Se ela já tinha dito que não queria agora, só deixe "
                  "a porta aberta, sem pergunta de venda. "
                  "Tudo o que você escrever agora vai direto para o WhatsApp dela: escreva só a mensagem, falando COM "
                  "ela (você), nunca SOBRE ela. O resumo da ficha e esta orientação são anotações internas: use só "
                  "para saber o assunto. Não reconte a conversa nem diga o que ela fez ou pediu ('você entrou em "
                  "contato por...', 'você pediu o valor'); retome o assunto com leveza, como quem lembrou dela.")
MARCADOR_SILENCIO = "(a cliente não respondeu desde a sua última mensagem)"


def etapa_followup(n: int) -> tuple[str, timedelta]:
    """n = quantos follow-ups já foram enviados. Retorna (chave da etapa, dias de silêncio da etapa)."""
    dias = config.FOLLOWUP_DIAS
    if n < len(dias):
        return f"{dias[n]:g}", timedelta(days=dias[n])
    return "mensal", timedelta(days=dias[-1] + config.FOLLOWUP_MENSAL_DIAS * (n - len(dias) + 1))


def momento_followup(ultima_cliente: datetime, espera: timedelta) -> datetime:
    """Quando o follow-up sai: às FOLLOWUP_HORA do dia da etapa, contando da data da última mensagem dela.

    Contato às 4h ou às 17h de segunda → D+1 é terça às 10h. Domingo passa para segunda (sem FOLLOWUP_DOMINGO).
    """
    dia = ultima_cliente.astimezone(config.TZ).date() + timedelta(days=max(1, round(espera.days)))
    if dia.weekday() == 6 and not config.FOLLOWUP_DOMINGO:
        dia += timedelta(days=1)
    return datetime(dia.year, dia.month, dia.day, config.FOLLOWUP_HORA, tzinfo=config.TZ)


def horario_de_followup(agora_local: datetime) -> bool:
    """Follow-up só em horário comercial (8h às 18h) e, por padrão, fora do domingo."""
    if agora_local.weekday() == 6 and not config.FOLLOWUP_DOMINGO:
        return False
    return config.FOLLOWUP_HORARIO[0] <= agora_local.hour < config.FOLLOWUP_HORARIO[1]


def nota_etapa(chave: str) -> str:
    base = NOTAS_ETAPA.get(chave) or NOTAS_ETAPA["30"]
    return base.format(link=config.GRUPO_VIP_LINK or "(ainda não configurado, não cite link)") + REGRA_FOLLOWUP


async def laco():
    while True:
        try:
            await processador.retomar_pendentes()
            if config.LEMBRETES_ATIVOS:
                await lembretes()
            await pagamentos()
            if config.FOLLOWUP_ATIVO:
                await followups()
            await relatorio.relatorio_diario_se_for_hora()
        except Exception:
            log.exception("Erro nas rotinas")
        await asyncio.sleep(60)


def _nome(contato: dict) -> str:
    f = contato["ficha"]
    nome = f.get("nome") or (f.get("nome_completo") or contato.get("perfil_nome") or "").split(" ")[0]
    return nome or "tudo bem"


def _dentro_da_janela(contato: dict) -> bool:
    ultima = contato.get("ultima_msg_cliente_em")
    return bool(ultima and db.agora() - datetime.fromisoformat(ultima) < timedelta(hours=23, minutes=50))


async def _enviar_lembrete(contato: dict, ag: dict, texto: str):
    tel = contato["telefone"]
    inicio = datetime.fromisoformat(ag["inicio"]).astimezone(config.TZ)
    hora = f"{inicio.hour}h" if inicio.minute == 0 else f"{inicio.hour}h{inicio.minute:02d}"
    if contato["canal"] == "whatsapp" and whatsapp.configurado():
        if _dentro_da_janela(contato):
            await whatsapp.enviar_texto(tel, texto)
        elif config.TEMPLATE_LEMBRETE:
            await whatsapp.enviar_template(tel, config.TEMPLATE_LEMBRETE,
                                           [_nome(contato), inicio.strftime("%d/%m"), hora])
        else:
            db.criar_aviso(tel, "lembrete_pendente",
                           f"Lembrete não enviado (fora da janela de 24h e sem template): {contato['telefone']}")
            return
    db.registrar_conversa(tel, "bot", texto)
    if db.obter_historico(tel):
        db.adicionar_historico(tel, "assistant", [{"type": "text", "text": texto}])


async def _mensagem_cliente(contato: dict, texto: str, template: str | None = None, parametros=None) -> bool:
    """Mensagem automática para a cliente: texto livre dentro da janela de 24h, senão template."""
    tel = contato["telefone"]
    if contato["canal"] == "whatsapp" and whatsapp.configurado():
        if _dentro_da_janela(contato):
            await whatsapp.enviar_texto(tel, texto)
        elif template:
            await whatsapp.enviar_template(tel, template, parametros or [])
        else:
            return False
    db.registrar_conversa(tel, "bot", texto)
    if db.obter_historico(tel):
        db.adicionar_historico(tel, "assistant", [{"type": "text", "text": texto}])
    return True


async def pagamentos():
    """Lembra do pagamento antecipado e cancela automaticamente o horário que passou do prazo."""
    agora = db.agora()
    for ag in db.agendamentos_ativos():
        if ag.get("pagamento") == "pago" or not ag.get("prazo_pagamento"):
            continue
        prazo = datetime.fromisoformat(ag["prazo_pagamento"])
        contato = db.obter_contato(ag["telefone"])
        if not contato:
            continue
        nome = _nome(contato)
        quando_prazo = prazo.astimezone(config.TZ).strftime("%d/%m às %H:%M")
        inicio = datetime.fromisoformat(ag["inicio"]).astimezone(config.TZ)
        rotulo = f"{nome} (+{ag['telefone']}), avaliação {agenda.descrever(inicio)}"

        if agora >= prazo:
            if not config.CANCELAR_SEM_PAGAMENTO:
                if (ag.get("lembrete_pagamento") or 0) < 2:
                    db.atualizar_agendamento(ag["id"], lembrete_pagamento=2)
                    await equipe.notificar(
                        ag["telefone"], "pagamento",
                        f"⏰ Prazo do pagamento venceu: {rotulo}. O horário continua reservado. Se recebeu, marque "
                        "como pago no painel; se não, cancele a avaliação no painel (aba Avaliações).")
                continue
            db.atualizar_agendamento(ag["id"], status="cancelado")
            db.atualizar_contato(ag["telefone"], status="qualificado")
            if ag.get("google_evento_id"):
                try:
                    await google_agenda.cancelar_evento(ag["google_evento_id"])
                except Exception:
                    log.warning("Falha ao apagar evento do Google", exc_info=True)
            await _mensagem_cliente(
                contato,
                f"Oi, {nome}! Como não identificamos o pagamento da avaliação dentro do prazo, o sistema liberou o "
                "seu horário. Mas fica tranquila: se quiser, a gente encontra um novo horário pra você agora mesmo 🤍",
            )
            await equipe.notificar(ag["telefone"], "cancelamento",
                                   f"⏰ Avaliação cancelada automaticamente por falta de pagamento\n{rotulo}")
            continue

        criado_ha = agora - datetime.fromisoformat(ag["criado_em"])
        if not ag.get("lembrete_pagamento") and prazo - agora <= timedelta(hours=2) and criado_ha > timedelta(hours=1):
            db.atualizar_agendamento(ag["id"], lembrete_pagamento=1)
            enviado = await _mensagem_cliente(
                contato,
                f"{nome}, passando pra lembrar: pra garantir o seu horário com a Dra. Danielly, o pagamento da "
                f"avaliação precisa ser feito até {quando_prazo}. Se já fez, é só me mandar o comprovante por aqui 🤍",
                config.TEMPLATE_PAGAMENTO, [nome, quando_prazo],
            )
            await equipe.notificar(
                ag["telefone"], "pagamento",
                f"💳 Pagamento pendente: {rotulo}. Prazo {quando_prazo}. Se já recebeu, marque como pago no painel, "
                + ("senão o horário será cancelado automaticamente." if config.CANCELAR_SEM_PAGAMENTO
                 else "senão você decide se cancela quando o prazo vencer.") + ("" if enviado else
                                                                       "\n(Lembrete à cliente não enviado: fora da janela de 24h e sem TEMPLATE_PAGAMENTO.)"),
            )


async def lembretes():
    agora = datetime.now(config.TZ)
    for ag in db.agendamentos_ativos():
        inicio = datetime.fromisoformat(ag["inicio"]).astimezone(config.TZ)
        falta = inicio - agora
        contato = db.obter_contato(ag["telefone"])
        if not contato or contato["status"] == "opt_out":
            continue
        prof = agenda.PROFISSIONAIS.get(ag["profissional"], "a Dra.")
        nome = _nome(contato)
        hora = f"{inicio.hour}h" if inicio.minute == 0 else f"{inicio.hour}h{inicio.minute:02d}"
        recente = db.agora() - datetime.fromisoformat(ag["criado_em"]) < timedelta(hours=12)
        if (not ag["lembrete_d1"] and not recente and timedelta(hours=3) < falta <= timedelta(hours=24)
                and 8 <= agora.hour < 21):
            texto = (f"Oi, {nome}! Passando pra lembrar da sua avaliação {agenda.descrever(inicio).split(' às')[0]} "
                     f"às {hora} com a {prof}, na unidade {agenda.nome_unidade(ag.get('unidade'))}"
                     f"{(', ' + agenda.endereco_unidade(ag.get('unidade')).split(', São Paulo')[0]) if agenda.endereco_unidade(ag.get('unidade')) else ''} 🤍\n\n"
                     "Posso confirmar sua presença?")
            await _enviar_lembrete(contato, ag, texto)
            db.atualizar_agendamento(ag["id"], lembrete_d1=1)
        elif not ag["lembrete_2h"] and timedelta(0) < falta <= timedelta(hours=2):
            texto = (f"{nome}, daqui a pouquinho, às {hora}, a {prof} te espera! "
                     "Se puder, chega uns 10 minutinhos antes ✨")
            await _enviar_lembrete(contato, ag, texto)
            db.atualizar_agendamento(ag["id"], lembrete_2h=1, lembrete_d1=1)


async def followups(agora_local: datetime | None = None):
    agora_local = agora_local or datetime.now(config.TZ)
    if not horario_de_followup(agora_local):
        return
    for contato in db.listar_contatos():
        if contato["status"] in ("agendado", "humano", "opt_out", "fornecedor"):
            continue
        if processador.bot_pausado(contato) or db.agendamentos_ativos(contato["telefone"]):
            continue
        cli, bot = contato.get("ultima_msg_cliente_em"), contato.get("ultima_msg_bot_em")
        if not cli or not bot or bot < cli:
            continue
        chave, espera = etapa_followup(contato["followups_enviados"])
        if agora_local < momento_followup(datetime.fromisoformat(cli), espera):
            continue
        await enviar_followup(contato, chave)


async def enviar_followup(contato: dict, chave: str):
    tel = contato["telefone"]
    n = contato["followups_enviados"] + 1
    campos = {"followups_enviados": n}
    if n >= 3 and contato["temperatura"] != "fria":
        campos["temperatura"] = "fria"
    db.atualizar_contato(tel, **campos)
    log.info("Follow-up %s (etapa %s) para %s", n, chave, tel)

    # Dentro da janela de 24h (ou na página de teste) o Claude escreve a mensagem personalizada.
    if contato["canal"] == "teste" or _dentro_da_janela(contato):
        await processador.responder_e_enviar(
            tel, contato["canal"], [{"type": "text", "text": MARCADOR_SILENCIO}], nota_etapa(chave))
        return

    # Fora da janela, o WhatsApp só aceita template aprovado.
    template = config.FOLLOWUP_TEMPLATES.get(chave)
    if not template or not whatsapp.configurado():
        db.criar_aviso(tel, "followup_pendente",
                       f"Follow-up da etapa {chave} não enviado para +{tel}: falta o template '{chave}' em "
                       "FOLLOWUP_TEMPLATES.")
        return
    parametros = [_nome(contato)]
    if chave == "mensal" and config.GRUPO_VIP_LINK:
        parametros.append(config.GRUPO_VIP_LINK)
    try:
        await whatsapp.enviar_template(tel, template, parametros)
    except Exception:
        log.exception("Falha no template de follow-up")
        db.criar_aviso(tel, "followup_pendente", f"Erro ao enviar o template '{template}' para +{tel}.")
        return
    texto = f"(follow-up automático enviado: template {template}, etapa {chave})"
    db.registrar_conversa(tel, "bot", texto)
    if db.obter_historico(tel):
        db.adicionar_historico(tel, "assistant", [{"type": "text", "text": texto}])
    db.atualizar_contato(tel, ultima_msg_bot_em=db.agora_iso())
