"""Integração com o Google Agenda da ORYA (conta de serviço do Google Cloud).

- Horários ocupados na agenda (inclusive eventos criados à mão, férias, bloqueios) não são oferecidos.
- Cada avaliação agendada pelo bot vira um evento; remarcar e cancelar atualizam o evento.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta

import httpx

from . import config

log = logging.getLogger("orya.google")

BASE = "https://www.googleapis.com/calendar/v3"
ESCOPOS = ["https://www.googleapis.com/auth/calendar"]

_credenciais = None
_cache_ocupados: dict = {"em": 0.0, "intervalo": None, "dados": []}


def configurado() -> bool:
    return bool(config.GOOGLE_CALENDAR_ID and config.GOOGLE_SERVICE_ACCOUNT_JSON)


def _token() -> str:
    global _credenciais
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    if _credenciais is None:
        info = json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON)
        _credenciais = service_account.Credentials.from_service_account_info(info, scopes=ESCOPOS)
    if not _credenciais.valid:
        _credenciais.refresh(Request())
    return _credenciais.token


async def _requisicao(metodo: str, caminho: str, corpo: dict | None = None) -> dict:
    token = await asyncio.to_thread(_token)
    async with httpx.AsyncClient(timeout=20) as cli:
        r = await cli.request(metodo, BASE + caminho, headers={"Authorization": f"Bearer {token}"}, json=corpo)
    if r.status_code >= 400:
        log.error("Erro Google Agenda %s: %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json() if r.content else {}


def _calendario() -> str:
    from urllib.parse import quote
    return quote(config.GOOGLE_CALENDAR_ID, safe="")


async def ocupados(inicio: datetime, fim: datetime) -> list[tuple[datetime, datetime]]:
    """Intervalos ocupados no Google Agenda (cache de 60 s). Em caso de erro, não bloqueia nada."""
    if not configurado():
        return []
    chave = (inicio.date(), fim.date())
    if _cache_ocupados["intervalo"] == chave and time.time() - _cache_ocupados["em"] < 60:
        return _cache_ocupados["dados"]
    try:
        resp = await _requisicao("POST", "/freeBusy", {
            "timeMin": inicio.isoformat(), "timeMax": fim.isoformat(), "timeZone": str(config.TZ),
            "items": [{"id": config.GOOGLE_CALENDAR_ID}],
        })
    except Exception:
        log.warning("Não consegui ler o Google Agenda; seguindo só com a agenda interna", exc_info=True)
        return []
    dados = [
        (datetime.fromisoformat(b["start"].replace("Z", "+00:00")), datetime.fromisoformat(b["end"].replace("Z", "+00:00")))
        for b in resp.get("calendars", {}).get(config.GOOGLE_CALENDAR_ID, {}).get("busy", [])
    ]
    _cache_ocupados.update(em=time.time(), intervalo=chave, dados=dados)
    return dados


def limpar_cache():
    _cache_ocupados.update(em=0.0, intervalo=None, dados=[])


def _evento(titulo: str, descricao: str, inicio: datetime, duracao_min: int, local: str) -> dict:
    return {
        "summary": titulo,
        "description": descricao,
        "location": local,
        "start": {"dateTime": inicio.isoformat(), "timeZone": str(config.TZ)},
        "end": {"dateTime": (inicio + timedelta(minutes=duracao_min)).isoformat(), "timeZone": str(config.TZ)},
    }


async def criar_evento(titulo: str, descricao: str, inicio: datetime, duracao_min: int, local: str) -> str | None:
    if not configurado():
        return None
    resp = await _requisicao("POST", f"/calendars/{_calendario()}/events",
                             _evento(titulo, descricao, inicio, duracao_min, local))
    limpar_cache()
    return resp.get("id")


async def mover_evento(evento_id: str, inicio: datetime, duracao_min: int):
    if not (configurado() and evento_id):
        return
    await _requisicao("PATCH", f"/calendars/{_calendario()}/events/{evento_id}", {
        "start": {"dateTime": inicio.isoformat(), "timeZone": str(config.TZ)},
        "end": {"dateTime": (inicio + timedelta(minutes=duracao_min)).isoformat(), "timeZone": str(config.TZ)},
    })
    limpar_cache()


async def cancelar_evento(evento_id: str):
    if not (configurado() and evento_id):
        return
    await _requisicao("DELETE", f"/calendars/{_calendario()}/events/{evento_id}")
    limpar_cache()


async def status() -> dict:
    """Testa o acesso à agenda (usado no painel para conferir a integração)."""
    if not configurado():
        return {"ok": False, "motivo": "GOOGLE_CALENDAR_ID ou GOOGLE_SERVICE_ACCOUNT_JSON vazio no Render"}
    try:
        email = json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON).get("client_email")
        agora = datetime.now(config.TZ)
        resp = await _requisicao("POST", "/freeBusy", {
            "timeMin": agora.isoformat(), "timeMax": (agora + timedelta(days=7)).isoformat(),
            "timeZone": str(config.TZ), "items": [{"id": config.GOOGLE_CALENDAR_ID}],
        })
    except Exception as e:
        return {"ok": False, "motivo": f"erro ao acessar o Google: {e}"}
    agenda = resp.get("calendars", {}).get(config.GOOGLE_CALENDAR_ID, {})
    if agenda.get("errors"):
        return {"ok": False, "conta_de_servico": email, "motivo": (
            "a agenda não foi compartilhada com a conta de serviço (Fazer alterações nos eventos)"),
            "erros": agenda["errors"]}
    return {"ok": True, "agenda": config.GOOGLE_CALENDAR_ID, "conta_de_servico": email,
            "ocupados_proximos_7_dias": len(agenda.get("busy", []))}
