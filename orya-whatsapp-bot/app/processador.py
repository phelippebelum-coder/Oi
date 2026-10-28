"""Recebe as mensagens, espera a cliente terminar de digitar, chama o cérebro e envia a resposta."""

import asyncio
import base64
import logging
from datetime import datetime, timedelta

from . import cerebro, config, db, whatsapp

log = logging.getLogger("orya.processador")

_pendentes: dict[str, list[dict]] = {}
_timers: dict[str, asyncio.Task] = {}
_travas: dict[str, asyncio.Lock] = {}
_ultimo_id: dict[str, str] = {}
_notas: dict[str, str] = {}

IMAGENS_SUPORTADAS = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def bot_pausado(contato: dict) -> bool:
    if contato["status"] == "opt_out":
        return True
    ate = contato.get("bot_pausado_ate")
    return bool(ate and datetime.fromisoformat(ate) > db.agora())


async def receber_mensagem(evento: dict, canal: str = "whatsapp"):
    """Chamado para cada mensagem da cliente (WhatsApp ou página de teste)."""
    if evento.get("id") and db.ja_processado(evento["id"]):
        return
    tel = db.resolver_telefone_br(evento["de"])
    contato = db.garantir_contato(tel, canal, evento.get("nome"))
    if evento.get("referral") and not contato.get("referral"):
        db.atualizar_contato(tel, referral=evento["referral"], origem="anuncio")
    if contato["followups_enviados"] and contato.get("ultima_msg_cliente_em"):
        # Lead resgatada: voltou a responder depois dos follow-ups. A cadência recomeça do zero.
        dias = (db.agora() - datetime.fromisoformat(contato["ultima_msg_cliente_em"])).days
        _notas[tel] = (f"A cliente VOLTOU a responder depois de {dias} dia(s) sem retorno e "
                       f"{contato['followups_enviados']} follow-up(s). Siga 'Leads que voltaram a responder'.")
        if contato["temperatura"] == "fria":
            db.atualizar_contato(tel, temperatura="morna")
    db.atualizar_contato(tel, ultima_msg_cliente_em=db.agora_iso(), followups_enviados=0)

    blocos = await _converter(evento, canal)
    texto_legivel = evento.get("texto") or f"[{evento.get('msg_tipo')}]"
    db.registrar_conversa(tel, "cliente", texto_legivel)

    if bot_pausado(db.obter_contato(tel)):
        # Equipe está atendendo: guarda no histórico para o bot ter contexto quando voltar.
        db.adicionar_historico(tel, "user", blocos)
        return

    if canal == "whatsapp" and evento.get("id"):
        _ultimo_id[tel] = evento["id"]
        asyncio.create_task(whatsapp.marcar_lida_digitando(evento["id"]))

    _pendentes.setdefault(tel, []).extend(blocos)
    if t := _timers.get(tel):
        t.cancel()
    _timers[tel] = asyncio.create_task(_processar_depois(tel, canal))


async def _processar_depois(tel: str, canal: str):
    try:
        await asyncio.sleep(config.AGRUPAR_SEGUNDOS)
    except asyncio.CancelledError:
        return
    trava = _travas.setdefault(tel, asyncio.Lock())
    async with trava:
        blocos = _pendentes.pop(tel, [])
        _timers.pop(tel, None)
        if not blocos:
            return
        await responder_e_enviar(tel, canal, blocos, _notas.pop(tel, None))


async def responder_e_enviar(tel: str, canal: str, blocos: list[dict], nota: str | None = None):
    baloes = await cerebro.responder(tel, blocos, nota)
    for i, balao in enumerate(baloes):
        if canal == "whatsapp" and whatsapp.configurado():
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


async def receber_eco(evento: dict):
    """A equipe respondeu pelo app WhatsApp Business: o bot sai de cena nessa conversa."""
    if evento.get("id") and db.ja_processado(evento["id"]):
        return
    tel = db.resolver_telefone_br(evento["para"])
    contato = db.garantir_contato(tel)
    texto = evento.get("texto") or f"[{evento.get('msg_tipo')}]"
    db.registrar_conversa(tel, "equipe", texto)
    if db.obter_historico(tel):
        db.adicionar_historico(tel, "assistant", [{"type": "text", "text": f"(mensagem da equipe) {texto}"}])
    ate = db.agora() + timedelta(hours=config.PAUSA_HUMANO_HORAS)
    atual = contato.get("bot_pausado_ate")
    if not atual or datetime.fromisoformat(atual) < ate:
        db.atualizar_contato(tel, bot_pausado_ate=ate.isoformat())
    if t := _timers.pop(tel, None):
        t.cancel()
    _pendentes.pop(tel, None)


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
            blocos.append({"type": "text",
                           "text": f"(a cliente enviou {nomes.get(tipo, 'uma mídia')} que você não consegue abrir)"})
    if evento.get("texto"):
        blocos.append({"type": "text", "text": evento["texto"]})
    if not blocos:
        blocos.append({"type": "text", "text": f"(mensagem do tipo {evento.get('msg_tipo')} sem texto)"})
    return blocos
