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
LEMBRETES_ATIVOS = _env("LEMBRETES_ATIVOS", "1") == "1"

# Follow-up de quem parou de responder: dias sem resposta para cada mensagem.
# Depois da última etapa, repete a cada FOLLOWUP_MENSAL_DIAS (mensagem mensal com convite pro grupo VIP).
FOLLOWUP_ATIVO = _env("FOLLOWUP_ATIVO", "1") == "1"
FOLLOWUP_DIAS = [float(x) for x in _lista("FOLLOWUP_DIAS") or ["1", "3", "7", "15", "30"]]
FOLLOWUP_MENSAL_DIAS = float(_env("FOLLOWUP_MENSAL_DIAS", "30"))
FOLLOWUP_HORARIO = (int(_env("FOLLOWUP_HORA_INICIO", "9")), int(_env("FOLLOWUP_HORA_FIM", "20")))
# Templates aprovados no Meta para cada etapa fora da janela de 24h (parâmetro {{1}} = primeiro nome).
# Formato: "3:nome_template_d3,7:nome_template_d7,15:...,30:...,mensal:nome_template_mensal"
FOLLOWUP_TEMPLATES = dict(x.split(":", 1) for x in _lista("FOLLOWUP_TEMPLATES") if ":" in x)
GRUPO_VIP_LINK = _env("GRUPO_VIP_LINK")

# Relatórios por e-mail (SMTP, ex.: Gmail com senha de app)
SMTP_HOST = _env("SMTP_HOST", "smtp.gmail.com")
SMTP_PORTA = int(_env("SMTP_PORTA", "587"))
SMTP_USUARIO = _env("SMTP_USUARIO")
SMTP_SENHA = _env("SMTP_SENHA")
RELATORIO_EMAIL = _lista("RELATORIO_EMAIL")  # destinatários
RELATORIO_HORA = int(_env("RELATORIO_HORA", "20"))  # relatório diário de leads, horário de SP

TZ = ZoneInfo(_env("TZ_CLINICA", "America/Sao_Paulo"))
DATA_DIR = Path(_env("DATA_DIR", str(BASE_DIR / "data")))
DB_PATH = DATA_DIR / "orya.db"

# Agenda da avaliação (sempre com a Dra. Danielly)
_EXPEDIENTE = [["08:00", "20:00"]]
AGENDA_PADRAO = {
    "duracao_min": 30,
    "antecedencia_min_horas": 2,
    "dias_a_frente": 14,
    # 0 = segunda ... 6 = domingo; lista de [início, fim] no horário da clínica
    "expediente": {str(d): _EXPEDIENTE for d in range(6)},
    "avaliacoes_simultaneas": 1,
    "bloqueios": [],  # ex.: ["2026-11-02", "2026-11-15 14:00"]
}


def carregar_agenda() -> dict:
    arquivo = BASE_DIR / "prompts" / "agenda.json"
    if arquivo.exists():
        return {**AGENDA_PADRAO, **json.loads(arquivo.read_text(encoding="utf-8"))}
    return AGENDA_PADRAO
