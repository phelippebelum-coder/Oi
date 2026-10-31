"""Agenda interna de avaliações (sempre com a Dra. Danielly, em três unidades)."""

from datetime import date, datetime, time, timedelta

from . import config, db

DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
PROFISSIONAIS = {"danielly": "Dra. Danielly"}
UNIDADE_PADRAO = "jardim_sao_paulo"


def _cfg():
    return config.carregar_agenda()


def unidades() -> dict[str, dict]:
    return _cfg()["unidades"]


def nome_unidade(chave: str | None) -> str:
    return unidades().get(chave or UNIDADE_PADRAO, {}).get("nome", chave or "")


def endereco_unidade(chave: str | None) -> str:
    u = unidades().get(chave or UNIDADE_PADRAO, {})
    return u.get("endereco") or ""


def _expediente(cfg: dict, unidade: str) -> dict:
    return cfg["unidades"].get(unidade, {}).get("expediente") or {}


def agenda_aberta(unidade: str) -> bool:
    """Unidade sem expediente cadastrado = horários sob consulta (a equipe confirma)."""
    return any(_expediente(_cfg(), unidade).values())


def _bloqueado(cfg: dict, inicio: datetime) -> bool:
    for b in cfg.get("bloqueios", []):
        if len(b) == 10 and inicio.strftime("%Y-%m-%d") == b:
            return True
        if inicio.strftime("%Y-%m-%d %H:%M") == b:
            return True
    return False


def _ocupacao() -> dict[str, int]:
    """A Dra. é uma só: um horário ocupado em qualquer unidade fica ocupado em todas."""
    ocup: dict[str, int] = {}
    for ag in db.agendamentos_ativos():
        ocup[ag["inicio"]] = ocup.get(ag["inicio"], 0) + 1
    return ocup


Intervalo = tuple[datetime, datetime]


def _conflita(slot: datetime, dur: timedelta, ocupados: list[Intervalo]) -> bool:
    return any(slot < fim and slot + dur > ini for ini, fim in ocupados)


def janela_busca() -> tuple[datetime, datetime]:
    agora = datetime.now(config.TZ)
    return agora, agora + timedelta(days=_cfg()["dias_a_frente"] + 1)


def prazo_pagamento(inicio: datetime, criado: datetime | None = None) -> datetime:
    """Até 24 h antes; se marcou em cima da hora (sem pelo menos 1 h para pagar), até 3 h antes."""
    criado = criado or datetime.now(config.TZ)
    prazo = inicio - timedelta(hours=config.PAGAMENTO_PRAZO_HORAS)
    if prazo < criado + timedelta(hours=1):
        prazo = inicio - timedelta(hours=config.PAGAMENTO_PRAZO_CURTO_HORAS)
    return prazo


def horarios_livres(unidade: str = UNIDADE_PADRAO, a_partir: date | None = None,
                    periodo: str | None = None, limite: int = 8,
                    ocupados: list[Intervalo] | None = None) -> list[datetime]:
    cfg = _cfg()
    agora = datetime.now(config.TZ)
    minimo = agora + timedelta(hours=cfg["antecedencia_min_horas"])
    inicio_busca = max(a_partir or agora.date(), agora.date())
    ocup = _ocupacao()
    dur = timedelta(minutes=cfg["duracao_min"])
    livres = []
    for d in range(cfg["dias_a_frente"]):
        dia = inicio_busca + timedelta(days=d)
        if _dia_de_evento(dia):
            continue
        for ini_s, fim_s in _expediente(cfg, unidade).get(str(dia.weekday()), []):
            slot = datetime.combine(dia, time.fromisoformat(ini_s), tzinfo=config.TZ)
            fim = datetime.combine(dia, time.fromisoformat(fim_s), tzinfo=config.TZ)
            while slot + dur <= fim:
                if (
                    slot >= minimo
                    and not _bloqueado(cfg, slot)
                    and ocup.get(slot.isoformat(), 0) < cfg["avaliacoes_simultaneas"]
                    and not _conflita(slot, dur, ocupados or [])
                    and _no_periodo(slot, periodo)
                ):
                    livres.append(slot)
                slot += dur
    return _espalhar(livres, limite)


def eventos() -> dict[str, dict]:
    return _cfg().get("eventos", {})


def _dia_de_evento(dia: date) -> bool:
    return any(e["data"] == dia.isoformat() for e in eventos().values())


def horarios_evento(chave: str, ocupados: list[Intervalo] | None = None) -> list[datetime]:
    """Todos os horários livres do dia do evento (inclusive o do almoço)."""
    ev = eventos().get(chave)
    if not ev:
        return []
    cfg = _cfg()
    dia = date.fromisoformat(ev["data"])
    dur = timedelta(minutes=ev["duracao_min"])
    slot = datetime.combine(dia, time.fromisoformat(ev["inicio"]), tzinfo=config.TZ)
    fim = datetime.combine(dia, time.fromisoformat(ev["fim"]), tzinfo=config.TZ)
    minimo = datetime.now(config.TZ) + timedelta(hours=cfg["antecedencia_min_horas"])
    ocup = _ocupacao()
    livres = []
    while slot + dur <= fim:
        if slot >= minimo and ocup.get(slot.isoformat(), 0) < 1 and not _conflita(slot, dur, ocupados or []):
            livres.append(slot)
        slot += dur
    return livres


def validar_evento(chave: str, inicio: datetime, ocupados: list[Intervalo] | None = None) -> str | None:
    ev = eventos().get(chave)
    if not ev:
        return "evento desconhecido"
    if inicio not in horarios_evento(chave, ocupados):
        return f"horário fora do {ev['nome']} ou já ocupado"
    return None


def _no_periodo(slot: datetime, periodo: str | None) -> bool:
    if not periodo:
        return True
    h = slot.hour
    return {"manha": h < 12, "tarde": 12 <= h < 18, "noite": h >= 18}.get(periodo, True)


def _espalhar(livres: list[datetime], limite: int) -> list[datetime]:
    """Evita devolver 8 horários seguidos do mesmo dia: no máximo 3 por dia."""
    por_dia: dict[date, int] = {}
    escolhidos = []
    for s in livres:
        if por_dia.get(s.date(), 0) >= 3:
            continue
        # prefere horários redondos para a lista ficar natural
        if s.minute != 0 and any(x.date() == s.date() for x in livres if x.minute == 0):
            continue
        por_dia[s.date()] = por_dia.get(s.date(), 0) + 1
        escolhidos.append(s)
        if len(escolhidos) >= limite:
            break
    return escolhidos


def descrever(slot: datetime) -> str:
    hoje = datetime.now(config.TZ).date()
    if slot.date() == hoje:
        rotulo = "hoje"
    elif slot.date() == hoje + timedelta(days=1):
        rotulo = "amanhã"
    else:
        rotulo = DIAS[slot.weekday()]
    hora = f"{slot.hour}h" if slot.minute == 0 else f"{slot.hour}h{slot.minute:02d}"
    return f"{rotulo} ({slot.strftime('%d/%m')}) às {hora}"


def validar_horario(inicio: datetime, unidade: str = UNIDADE_PADRAO,
                    ocupados: list[Intervalo] | None = None) -> str | None:
    """Retorna None se o horário estiver livre, senão o motivo."""
    cfg = _cfg()
    if unidade not in cfg["unidades"]:
        return "unidade desconhecida"
    if not agenda_aberta(unidade):
        return "a agenda dessa unidade é sob consulta (a equipe confirma o horário)"
    agora = datetime.now(config.TZ)
    if inicio < agora + timedelta(hours=cfg["antecedencia_min_horas"]):
        return "horário muito próximo ou no passado"
    if _bloqueado(cfg, inicio):
        return "dia/horário bloqueado na agenda"
    if _dia_de_evento(inicio.date()):
        return "dia reservado para campanha (agende pelo evento)"
    dur = timedelta(minutes=cfg["duracao_min"])
    dentro = False
    for ini_s, fim_s in _expediente(cfg, unidade).get(str(inicio.weekday()), []):
        ini = datetime.combine(inicio.date(), time.fromisoformat(ini_s), tzinfo=config.TZ)
        fim = datetime.combine(inicio.date(), time.fromisoformat(fim_s), tzinfo=config.TZ)
        if ini <= inicio and inicio + dur <= fim and (inicio - ini) % dur == timedelta(0):
            dentro = True
    if not dentro:
        return "fora do horário de atendimento dessa unidade"
    if _ocupacao().get(inicio.isoformat(), 0) >= cfg["avaliacoes_simultaneas"]:
        return "horário já ocupado"
    if _conflita(inicio, dur, ocupados or []):
        return "horário ocupado no Google Agenda"
    return None
