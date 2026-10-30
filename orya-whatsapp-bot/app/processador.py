"""Recebe as mensagens, espera a cliente terminar de mandar tudo, chama o cérebro e envia a resposta.

No WhatsApp a Aurora espera 1min30 sem mensagem nova (cada mensagem zera a contagem) e não responde de madrugada:
o que chega entre meia-noite e 6h30 é respondido às 6h30. As mensagens que aguardam resposta ficam no banco
(`pendente`), então nada se perde se o servidor reiniciar no meio da espera.
"""

import asyncio
import base64
import logging
from datetime import datetime, timedelta

from . import cerebro, config, db, ferramentas, midia, whatsapp

log = logging.getLogger("orya.processador")

_timers: dict[str, asyncio.Task] = {}
_travas: dict[str, asyncio.Lock] = {}
_ultimo_id: dict[str, str] = {}

IMAGENS_SUPORTADAS = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def bot_pausado(contato: dict) -> bool:
    if contato["status"] == "opt_out":
        return True
    ate = contato.get("bot_pausado_ate")
    return bool(ate and datetime.fromisoformat(ate) > db.agora())


def momento_de_responder(agora: datetime, canal: str) -> datetime:
    """1min30 depois da última mensagem dela; se isso cair na madrugada, às 6h30."""
    if canal != "whatsapp":
        return agora + timedelta(seconds=config.AGRUPAR_SEGUNDOS)
    alvo = agora + timedelta(seconds=config.ESPERA_CLIENTE_SEGUNDOS)
    local = alvo.astimezone(config.TZ)
    hora, minuto = config.RESPONDER_A_PARTIR_DE
    abre = local.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    return abre if local < abre else alvo


async def receber_mensagem(evento: dict, canal: str = "whatsapp"):
    """Chamado para cada mensagem da cliente (WhatsApp ou página de teste)."""
    if evento.get("id") and db.ja_processado(evento["id"]):
        return
    tel = db.resolver_telefone_br(evento["de"])
    contato = db.garantir_contato(tel, canal, evento.get("nome"))
    if evento.get("referral") and not contato.get("referral"):
        db.atualizar_contato(tel, referral=evento["referral"], origem="anuncio")
    nota = None
    if contato["followups_enviados"] and contato.get("ultima_msg_cliente_em"):
        # Lead resgatada: voltou a responder depois dos follow-ups. A cadência recomeça do zero.
        dias = (db.agora() - datetime.fromisoformat(contato["ultima_msg_cliente_em"])).days
        nota = (f"A cliente VOLTOU a responder depois de {dias} dia(s) sem retorno e "
                f"{contato['followups_enviados']} follow-up(s). Siga 'Leads que voltaram a responder'.")
        if contato["temperatura"] == "fria":
            db.atualizar_contato(tel, temperatura="morna")
    db.atualizar_contato(tel, ultima_msg_cliente_em=db.agora_iso(), followups_enviados=0)

    blocos = await _converter(evento, canal)
    texto_legivel = evento.get("texto") or f"[{evento.get('msg_tipo')}]"
    db.registrar_conversa(tel, "cliente", texto_legivel)

    contato = db.obter_contato(tel)
    if bot_pausado(contato):
        # Equipe está atendendo: guarda no histórico para o bot ter contexto quando voltar.
        db.adicionar_historico(tel, "user", blocos)
        return

    # Junta com o que ela já mandou e empurra a resposta para 1min30 depois desta mensagem.
    pend = contato.get("pendente") or {"blocos": []}
    pend["blocos"] = pend["blocos"] + blocos
    pend["canal"] = canal
    if nota:
        pend["nota"] = nota
    if canal == "whatsapp" and evento.get("id"):
        pend["ultimo_id"] = evento["id"]
    quando = momento_de_responder(db.agora(), canal)
    pend["responder_em"] = quando.isoformat()
    db.atualizar_contato(tel, pendente=pend)
    _agendar(tel, quando)


def _agendar(tel: str, quando: datetime):
    if t := _timers.get(tel):
        t.cancel()
    _timers[tel] = asyncio.create_task(_processar_depois(tel, quando))


async def _processar_depois(tel: str, quando: datetime):
    try:
        await asyncio.sleep(max(0.0, (quando - db.agora()).total_seconds()))
    except asyncio.CancelledError:
        return
    if _timers.get(tel) is asyncio.current_task():
        _timers.pop(tel)
    await processar_pendente(tel)


async def processar_pendente(tel: str):
    trava = _travas.setdefault(tel, asyncio.Lock())
    async with trava:
        contato = db.obter_contato(tel)
        pend = (contato or {}).get("pendente")
        if not pend or not pend.get("blocos"):
            return
        if datetime.fromisoformat(pend["responder_em"]) > db.agora():
            return  # ela mandou mensagem nova: a espera recomeçou
        db.atualizar_contato(tel, pendente=None)
        if bot_pausado(contato):
            db.adicionar_historico(tel, "user", pend["blocos"])
            return
        nota = pend.get("nota")
        if contato["status"] == "fornecedor":
            # Fornecedor já recebeu a resposta: silêncio (sem gastar o Claude), a não ser que peça um serviço.
            texto = "\n".join(b["text"] for b in pend["blocos"] if b.get("type") == "text")
            if not texto or not await cerebro.fornecedor_quer_servico(texto):
                db.adicionar_historico(tel, "user", pend["blocos"])
                return
            db.atualizar_contato(tel, status="em_conversa")
            nota = ("Este contato tinha sido marcado como fornecedor, mas agora perguntou sobre um serviço da "
                    "clínica. Atenda normalmente como lead.")
        canal = pend.get("canal", "whatsapp")
        if canal == "whatsapp" and whatsapp.configurado() and pend.get("ultimo_id"):
            # Só agora marca como lida e mostra "digitando...", como quem pegou o celular pra responder.
            _ultimo_id[tel] = pend["ultimo_id"]
            await whatsapp.marcar_lida_digitando(pend["ultimo_id"])
        await responder_e_enviar(tel, canal, pend["blocos"], nota)


async def retomar_pendentes():
    """Rede de segurança (roda a cada minuto): responde o que ficou pendente sem timer, como após um reinício."""
    agora = db.agora()
    for c in db.listar_contatos():
        pend = c.get("pendente")
        tel = c["telefone"]
        if not pend or tel in _timers or (tel in _travas and _travas[tel].locked()):
            continue
        quando = datetime.fromisoformat(pend["responder_em"])
        if quando <= agora:
            asyncio.create_task(processar_pendente(tel))
        else:
            _agendar(tel, quando)


async def responder_e_enviar(tel: str, canal: str, blocos: list[dict], nota: str | None = None):
    baloes = await cerebro.responder(tel, blocos, nota)
    real = canal == "whatsapp" and whatsapp.configurado()
    for i, balao in enumerate(baloes):
        if real:
            if i > 0:
                await asyncio.sleep(min(1.5 + len(balao) / 60, 4))  # ritmo de quem está digitando
                if mid := _ultimo_id.get(tel):
                    await whatsapp.marcar_lida_digitando(mid)
            try:
                await whatsapp.enviar_texto(tel, balao)
            except Exception:
                log.exception("Falha ao enviar para %s", tel)
                db.criar_aviso(tel, "erro_envio", f"Não consegui enviar a resposta para {tel}.")
                return
        db.registrar_conversa(tel, "bot", balao)
    for proc in ferramentas.anexos_pendentes.pop(tel, []):
        if real:
            try:
                await asyncio.sleep(1.5)
                await midia.enviar(tel, proc)
            except Exception:
                log.exception("Falha ao enviar foto %s para %s", proc, tel)
                continue
        db.registrar_conversa(tel, "bot", "[pdf:apresentacao]" if proc == "apresentacao" else f"[foto:{proc}]")


async def receber_eco(evento: dict):
    """A equipe respondeu pelo app WhatsApp Business: o bot sai de cena nessa conversa."""
    if evento.get("id") and db.ja_processado(evento["id"]):
        return
    tel = db.resolver_telefone_br(evento["para"])
    contato = db.garantir_contato(tel)
    texto = evento.get("texto") or f"[{evento.get('msg_tipo')}]"
    db.registrar_conversa(tel, "equipe", texto)
    if t := _timers.pop(tel, None):
        t.cancel()
    if pend := contato.get("pendente"):
        # A equipe respondeu antes da Aurora: as mensagens dela ficam só como contexto.
        db.atualizar_contato(tel, pendente=None)
        db.adicionar_historico(tel, "user", pend["blocos"])
    if db.obter_historico(tel):
        db.adicionar_historico(tel, "assistant", [{"type": "text", "text": f"(mensagem da equipe) {texto}"}])
    ate = db.agora() + timedelta(hours=config.PAUSA_HUMANO_HORAS)
    atual = contato.get("bot_pausado_ate")
    if not atual or datetime.fromisoformat(atual) < ate:
        db.atualizar_contato(tel, bot_pausado_ate=ate.isoformat())


NAO_PEDIR_REENVIO = (
    "Não comente isso e NUNCA peça para ela reenviar, repetir, escrever ou mandar de novo. Se é o primeiro contato, "
    "mande só a boas-vindas com uma pergunta aberta e espere. Se a conversa já estava andando, siga pelo contexto "
    "com o próximo passo natural")


async def _converter(evento: dict, canal: str) -> list[dict]:
    """Converte a mensagem em blocos para o Claude (texto e imagem)."""
    blocos = []
    midia = evento.get("midia")
    if midia:
        tipo = midia["tipo"]
        if tipo == "image" and canal == "whatsapp" and whatsapp.configurado():
            try:
                dados, mime = await whatsapp.baixar_midia(midia["id"])
                mime = mime.split(";")[0]
                if mime in IMAGENS_SUPORTADAS and len(dados) < 4_500_000:
                    blocos.append({"type": "image", "source": {
                        "type": "base64", "media_type": mime, "data": base64.standard_b64encode(dados).decode()}})
                    blocos.append({"type": "text", "text": "(a cliente enviou esta foto)"})
            except Exception:
                log.warning("Não consegui baixar a imagem", exc_info=True)
        if not blocos:
            nomes = {"audio": "um áudio", "video": "um vídeo", "document": "um arquivo",
                     "sticker": "uma figurinha", "image": "uma foto"}
            blocos.append({"type": "text", "text": (
                f"(a cliente enviou {nomes.get(tipo, 'uma mídia')} que não abre por aqui. " + NAO_PEDIR_REENVIO + ")")})
    if evento.get("texto"):
        blocos.append({"type": "text", "text": evento["texto"]})
    if not blocos:
        blocos.append({"type": "text", "text": (
            f"(chegou uma mensagem sem texto legível, tipo {evento.get('msg_tipo')}. " + NAO_PEDIR_REENVIO + ")")})
    return blocos
