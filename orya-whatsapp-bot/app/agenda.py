"""Agenda interna de avaliações: horários livres, reserva e cancelamento."""

from datetime import date, datetime, time, timedelta

from . import config, db

DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
PROFISSIONAIS = {"danielly": "Dra. Danielly"}


def _cfg():
    return config.carregar_agenda()


def _expediente(cfg: dict, profissional: str) -> dict:
    por_prof = cfg.get("profissionais", {}).get(profissional, {})
    return por_prof.get("expediente", cfg["expediente"])


def _bloqueado(cfg: dict, inicio: datetime) -> bool:
    for b in cfg.get("bloqueios", []):
        if len(b) == 10 and inicio.strftime("%Y-%m-%d") == b:
            return True
        if inicio.strftime("%Y-%m-%d %H:%M") == b:
            return True
    return False


def _ocupacao(profissional: str) -> dict[str, int]:
    ocup: dict[str, int] = {}
    for ag in db.agendamentos_ativos():
        if ag["profissional"] == profissional:
            ocup[ag["inicio"]] = ocup.get(ag["inicio"], 0) + 1
    return ocup


def horarios_livres(profissional: str = "danielly", a_partir: date | None = None,
                    periodo: str | None = None, limite: int = 8) -> list[datetime]:
    cfg = _cfg()
    agora = datetime.now(config.TZ)
    minimo = agora + timedelta(hours=cfg["antecedencia_min_horas"])
    inicio_busca = max(a_partir or agora.date(), agora.date())
    ocup = _ocupacao(profissional)
    dur = timedelta(minutes=cfg["duracao_min"])
    livres = []
    for d in range(cfg["dias_a_frente"]):
        dia = inicio_busca + timedelta(days=d)
        for ini_s, fim_s in _expediente(cfg, profissional).get(str(dia.weekday()), []):
            slot = datetime.combine(dia, time.fromisoformat(ini_s), tzinfo=config.TZ)
            fim = datetime.combine(dia, time.fromisoformat(fim_s), tzinfo=config.TZ)
            while slot + dur <= fim:
                if (
                    slot >= minimo
                    and not _bloqueado(cfg, slot)
                    and ocup.get(slot.isoformat(), 0) < cfg["avaliacoes_simultaneas"]
                    and _no_periodo(slot, periodo)
                ):
                    livres.append(slot)
                slot += dur
    return _espalhar(livres, limite)


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


def validar_horario(inicio: datetime, profissional: str) -> str | None:
    """Retorna None se o horário estiver livre, senão o motivo."""
    cfg = _cfg()
    agora = datetime.now(config.TZ)
    if inicio < agora + timedelta(hours=cfg["antecedencia_min_horas"]):
        return "horário muito próximo ou no passado"
    if _bloqueado(cfg, inicio):
        return "dia/horário bloqueado na agenda"
    dur = timedelta(minutes=cfg["duracao_min"])
    dentro = False
    for ini_s, fim_s in _expediente(cfg, profissional).get(str(inicio.weekday()), []):
        ini = datetime.combine(inicio.date(), time.fromisoformat(ini_s), tzinfo=config.TZ)
        fim = datetime.combine(inicio.date(), time.fromisoformat(fim_s), tzinfo=config.TZ)
        if ini <= inicio and inicio + dur <= fim and (inicio - ini) % dur == timedelta(0):
            dentro = True
    if not dentro:
        return "fora do horário de atendimento"
    if _ocupacao(profissional).get(inicio.isoformat(), 0) >= cfg["avaliacoes_simultaneas"]:
        return "horário já ocupado"
    return None
