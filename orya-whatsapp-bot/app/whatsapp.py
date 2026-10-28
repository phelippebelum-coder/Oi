"""Cliente da WhatsApp Cloud API (Meta) e leitura dos webhooks."""

import hashlib
import hmac
import logging

import httpx

from . import config

log = logging.getLogger("orya.whatsapp")


def _url(caminho: str) -> str:
    return f"https://graph.facebook.com/{config.GRAPH_VERSION}/{caminho}"


def _headers() -> dict:
    return {"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"}


def configurado() -> bool:
    return bool(config.WHATSAPP_TOKEN and config.WHATSAPP_PHONE_NUMBER_ID)


def assinatura_valida(corpo: bytes, assinatura: str | None) -> bool:
    """Confere o X-Hub-Signature-256. Sem META_APP_SECRET configurado, aceita (só para testes)."""
    if not config.META_APP_SECRET:
        return True
    if not assinatura or not assinatura.startswith("sha256="):
        return False
    esperado = hmac.new(config.META_APP_SECRET.encode(), corpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, assinatura.removeprefix("sha256="))


async def _post(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=20) as cli:
        r = await cli.post(_url(f"{config.WHATSAPP_PHONE_NUMBER_ID}/messages"), headers=_headers(), json=payload)
    if r.status_code >= 400:
        log.error("Erro WhatsApp %s: %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


async def enviar_texto(para: str, texto: str) -> dict:
    return await _post({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": para,
        "type": "text",
        "text": {"body": texto, "preview_url": False},
    })


async def enviar_template(para: str, nome: str, parametros: list[str]) -> dict:
    componentes = []
    if parametros:
        componentes.append({"type": "body", "parameters": [{"type": "text", "text": p} for p in parametros]})
    return await _post({
        "messaging_product": "whatsapp",
        "to": para,
        "type": "template",
        "template": {"name": nome, "language": {"code": config.TEMPLATE_IDIOMA}, "components": componentes},
    })


async def marcar_lida_digitando(message_id: str):
    """Marca como lida e mostra "digitando..." para a cliente (some ao enviar a resposta ou após 25 s)."""
    try:
        await _post({
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
            "typing_indicator": {"type": "text"},
        })
    except Exception:  # não é crítico
        log.warning("Não consegui marcar como lida/digitando", exc_info=True)


async def baixar_midia(media_id: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=30) as cli:
        meta = await cli.get(_url(media_id), headers=_headers())
        meta.raise_for_status()
        info = meta.json()
        arq = await cli.get(info["url"], headers=_headers())
        arq.raise_for_status()
    return arq.content, info.get("mime_type", "application/octet-stream")


async def enviar_conversao(evento: str, ctwa_clid: str, valor: float | None = None):
    """Conversions API para mensagens: avisa o Meta que a lead do anúncio agendou."""
    if not (config.META_DATASET_ID and config.WABA_ID and ctwa_clid):
        return
    import time

    dado = {
        "event_name": evento,
        "event_time": int(time.time()),
        "action_source": "business_messaging",
        "messaging_channel": "whatsapp",
        "user_data": {"whatsapp_business_account_id": config.WABA_ID, "ctwa_clid": ctwa_clid},
    }
    if valor is not None:
        dado["custom_data"] = {"currency": "BRL", "value": valor}
    try:
        async with httpx.AsyncClient(timeout=20) as cli:
            r = await cli.post(_url(f"{config.META_DATASET_ID}/events"), headers=_headers(), json={"data": [dado]})
        if r.status_code >= 400:
            log.error("Erro Conversions API %s: %s", r.status_code, r.text)
    except Exception:
        log.warning("Falha ao enviar conversão", exc_info=True)


# ---------- leitura do webhook ----------

def extrair_eventos(payload: dict) -> list[dict]:
    """Transforma o webhook do Meta em eventos simples.

    tipo "mensagem": mensagem da cliente.
    tipo "eco": mensagem que a equipe enviou pelo app WhatsApp Business (coexistência).
    """
    eventos = []
    for entrada in payload.get("entry", []):
        for mudanca in entrada.get("changes", []):
            valor = mudanca.get("value", {})
            nomes = {c.get("wa_id"): c.get("profile", {}).get("name") for c in valor.get("contacts", [])}
            for m in valor.get("messages", []):
                eventos.append({
                    "tipo": "mensagem",
                    "id": m.get("id"),
                    "de": m.get("from"),
                    "nome": nomes.get(m.get("from")),
                    "timestamp": m.get("timestamp"),
                    "msg_tipo": m.get("type"),
                    "texto": _texto(m),
                    "midia": _midia(m),
                    "referral": m.get("referral"),
                })
            for m in valor.get("message_echoes", []):
                eventos.append({
                    "tipo": "eco",
                    "id": m.get("id"),
                    "para": m.get("to"),
                    "msg_tipo": m.get("type"),
                    "texto": _texto(m),
                })
    return eventos


def _texto(m: dict) -> str | None:
    t = m.get("type")
    if t == "text":
        return m.get("text", {}).get("body")
    if t in ("image", "video", "document"):
        return m.get(t, {}).get("caption")
    if t == "button":
        return m.get("button", {}).get("text")
    if t == "interactive":
        i = m.get("interactive", {})
        return (i.get("button_reply") or i.get("list_reply") or {}).get("title")
    if t == "reaction":
        return f"(reagiu com {m.get('reaction', {}).get('emoji', '')})"
    if t == "location":
        loc = m.get("location", {})
        return f"(enviou uma localização: {loc.get('name') or ''} {loc.get('address') or ''})".strip()
    return None


def _midia(m: dict) -> dict | None:
    t = m.get("type")
    if t in ("image", "sticker", "audio", "video", "document"):
        d = m.get(t, {})
        return {"tipo": t, "id": d.get("id"), "mime": d.get("mime_type")}
    return None
