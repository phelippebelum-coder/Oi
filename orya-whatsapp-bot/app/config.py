"""Configuração lida das variáveis de ambiente (ver .env.example)."""

import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(nome: str, padrao: str = "") -> str:
    return os.environ.get(nome, padrao).strip()


def _lista(nome: str) -> list[str]:
    return [x.strip() for x in _env(nome).split(",") if x.strip()]


# Claude
CLAUDE_MODEL = _env("CLAUDE_MODEL", "claude-opus-5-5")
CLAUDE_EFFORT = _env("CLAUDE_EFFORT", "medium")  # low | medium | high

# WhatsApp Cloud API (Meta)
WHATSAPP_TOKEN = _env("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = _env("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = _env("WHATSAPP_VERIFY_TOKEN", "orya-verifica")
META_APP_SECRET = _env("META_APP_SECRET")
GRAPH_VERSION = _env("GRAPH_VERSION", "v23.0")
WABA_ID = _env("WABA_ID")

# Conversões (opcional): dataset do Meta para enviar "agendou avaliação"
META_DATASET_ID = _env("META_DATASET_ID")

# Templates aprovados no Meta (opcionais). Parâmetros do corpo: {{1}} nome, {{2}} data, {{3}} hora
TEMPLATE_LEMBRETE = _env("TEMPLATE_LEMBRETE")
TEMPLATE_AVISO_EQUIPE = _env("TEMPLATE_AVISO_EQUIPE")  # {{1}} texto do aviso
TEMPLATE_IDIOMA = _env("TEMPLATE_IDIOMA", "pt_BR")

# Equipe
EQUIPE_WHATSAPP = _lista("EQUIPE_WHATSAPP")  # ex.: 5511999999999,5511988888888
ATENDENTE = _env("ATENDENTE", "o atendimento da ORYA")

# Painel e página de teste
PAINEL_SENHA = _env("PAINEL_SENHA")

# Comportamento
AGRUPAR_SEGUNDOS = float(_env("AGRUPAR_SEGUNDOS", "7"))  # espera a cliente terminar de digitar
PAUSA_HUMANO_HORAS = float(_env("PAUSA_HUMANO_HORAS", "12"))  # bot fica quieto após a equipe responder
FOLLOWUP_HORAS = float(_env("FOLLOWUP_HORAS", "20"))  # 0 desliga; precisa ser < 24 (janela do WhatsApp)
LEMBRETES_ATIVOS = _env("LEMBRETES_ATIVOS", "1") == "1"

TZ = ZoneInfo(_env("TZ_CLINICA", "America/Sao_Paulo"))
DATA_DIR = Path(_env("DATA_DIR", str(BASE_DIR / "data")))
DB_PATH = DATA_DIR / "orya.db"

# Agenda da avaliação
AGENDA_PADRAO = {
    "duracao_min": 30,
    "antecedencia_min_horas": 2,
    "dias_a_frente": 14,
    # 0 = segunda ... 6 = domingo; lista de [início, fim] no horário da clínica
    "expediente": {
        "0": [["09:00", "20:00"]],
        "1": [["09:00", "20:00"]],
        "2": [["09:00", "20:00"]],
        "3": [["09:00", "20:00"]],
        "4": [["09:00", "20:00"]],
        "5": [["09:00", "14:00"]],
    },
    "avaliacoes_simultaneas": 1,
    "bloqueios": [],  # ex.: ["2026-11-02", "2026-11-15 14:00"]
}


def carregar_agenda() -> dict:
    arquivo = BASE_DIR / "prompts" / "agenda.json"
    if arquivo.exists():
        return {**AGENDA_PADRAO, **json.loads(arquivo.read_text(encoding="utf-8"))}
    return AGENDA_PADRAO
