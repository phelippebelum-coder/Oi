"""Rotinas em segundo plano: lembretes de avaliação e follow-up de quem parou de responder."""

import asyncio
import logging
from datetime import datetime, timedelta

from . import agenda, config, db, processador, whatsapp

log = logging.getLogger("orya.rotinas")

NOTA_FOLLOWUP = (
    "A cliente parou de responder há algumas horas. Envie UM follow-up curto (1 ou 2 balões), "
    "retomando com carinho a queixa ou o motivo dela e trazendo algo novo e útil (tirar uma dúvida comum, "
    "ou duas opções reais de horário via ver_horarios). Nada de cobrança, nada de 'e aí?'. "
    "Se ela já tinha dito que não queria agora, apenas deixe a porta aberta, sem pergunta de venda."
)


async def laco():
    while True:
        try:
            if config.LEMBRETES_ATIVOS:
                await lembretes()
            if config.FOLLOWUP_HORAS > 0:
                await followups()
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
                     f"às {hora} com a {prof}, aqui na Rua Viri, 62, Jardim São Paulo 🤍\n\n"
                     "Posso confirmar sua presença?")
            await _enviar_lembrete(contato, ag, texto)
            db.atualizar_agendamento(ag["id"], lembrete_d1=1)
        elif not ag["lembrete_2h"] and timedelta(0) < falta <= timedelta(hours=2):
            texto = (f"{nome}, daqui a pouquinho, às {hora}, a {prof} te espera! "
                     "Se puder, chega uns 10 minutinhos antes ✨")
            await _enviar_lembrete(contato, ag, texto)
            db.atualizar_agendamento(ag["id"], lembrete_2h=1, lembrete_d1=1)


async def followups():
    agora_local = datetime.now(config.TZ)
    if not (9 <= agora_local.hour < 21):
        return
    limite = timedelta(hours=config.FOLLOWUP_HORAS)
    for contato in db.listar_contatos():
        if contato["status"] not in ("em_conversa", "qualificado") or contato["followups_enviados"]:
            continue
        if processador.bot_pausado(contato) or db.agendamentos_ativos(contato["telefone"]):
            continue
        cli, bot = contato.get("ultima_msg_cliente_em"), contato.get("ultima_msg_bot_em")
        if not cli or not bot or bot < cli:
            continue
        silencio = db.agora() - datetime.fromisoformat(cli)
        if not (limite <= silencio < timedelta(hours=23, minutes=30)):
            continue
        db.atualizar_contato(contato["telefone"], followups_enviados=1)
        log.info("Follow-up para %s", contato["telefone"])
        await processador.responder_e_enviar(
            contato["telefone"], contato["canal"],
            [{"type": "text", "text": "(a cliente não respondeu desde a sua última mensagem)"}],
            NOTA_FOLLOWUP,
        )
