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
# Modelo barato que só confere se um fornecedor passou a querer um serviço da clínica.
CLAUDE_MODELO_TRIAGEM = _env("CLAUDE_MODELO_TRIAGEM", "claude-haiku-5-5")

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
ATENDENTE = _env("ATENDENTE", "Aurora, do atendimento da ORYA")

# Pagamento da avaliação (opcionais: sem eles, a equipe envia o Pix/link quando o bot avisar)
PIX_CHAVE = _env("PIX_CHAVE")
PIX_FAVORECIDO = _env("PIX_FAVORECIDO", "ORYA Estética Avançada")
LINK_CARTAO = _env("LINK_CARTAO")

# Prazo do pagamento antecipado: até 24 h antes; marcando em cima da hora, até 3 h antes.
# Sem pagamento no prazo: com CANCELAR_SEM_PAGAMENTO=1 cancela sozinho; com 0 (padrão) só avisa a equipe.
PAGAMENTO_PRAZO_HORAS = float(_env("PAGAMENTO_PRAZO_HORAS", "24"))
PAGAMENTO_PRAZO_CURTO_HORAS = float(_env("PAGAMENTO_PRAZO_CURTO_HORAS", "3"))
CANCELAR_SEM_PAGAMENTO = _env("CANCELAR_SEM_PAGAMENTO", "0") == "1"
TEMPLATE_PAGAMENTO = _env("TEMPLATE_PAGAMENTO")  # {{1}} nome, {{2}} prazo (dd/mm às hh:mm)

# Google Agenda (conta de serviço com acesso de edição à agenda da ORYA)
GOOGLE_CALENDAR_ID = _env("GOOGLE_CALENDAR_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = _env("GOOGLE_SERVICE_ACCOUNT_JSON")

# Fotos de antes e depois
LEGENDA_ANTES_DEPOIS = _env(
    "LEGENDA_ANTES_DEPOIS",
    "Resultado de paciente da Dra. Danielly Pinheiro (CRBM-1 62832), imagem autorizada pela paciente. "
    "Resultados variam de pessoa para pessoa.",
)

# Painel e página de teste
PAINEL_SENHA = _env("PAINEL_SENHA")

# Comportamento
AGRUPAR_SEGUNDOS = float(_env("AGRUPAR_SEGUNDOS", "7"))  # página de teste: espera a cliente terminar de digitar
# WhatsApp: espera 1min30 sem mensagem nova antes de responder (cada mensagem dela zera a contagem).
ESPERA_CLIENTE_SEGUNDOS = float(_env("ESPERA_CLIENTE_SEGUNDOS", "90"))
# Da meia-noite até este horário a Aurora não responde; o que chegar de madrugada é respondido a partir dele.
RESPONDER_A_PARTIR_DE = tuple(int(x) for x in _env("RESPONDER_A_PARTIR_DE", "06:30").split(":"))
PAUSA_HUMANO_HORAS = float(_env("PAUSA_HUMANO_HORAS", "12"))  # bot fica quieto após a equipe responder
LEMBRETES_ATIVOS = _env("LEMBRETES_ATIVOS", "1") == "1"

# Follow-up de quem parou de responder: dias sem resposta para cada mensagem.
# Depois da última etapa, repete a cada FOLLOWUP_MENSAL_DIAS (mensagem mensal com convite pro grupo VIP).
# O follow-up do dia N sai às FOLLOWUP_HORA do N-ésimo dia depois da última mensagem dela (contato às 4h → 10h
# do dia seguinte), sempre em horário comercial (8h às 18h) e, sem FOLLOWUP_DOMINGO=1, nunca no domingo.
FOLLOWUP_ATIVO = _env("FOLLOWUP_ATIVO", "1") == "1"
FOLLOWUP_DIAS = [float(x) for x in _lista("FOLLOWUP_DIAS") or ["1", "3", "7", "15", "30"]]
FOLLOWUP_MENSAL_DIAS = float(_env("FOLLOWUP_MENSAL_DIAS", "30"))
FOLLOWUP_HORA = int(_env("FOLLOWUP_HORA", "10"))
FOLLOWUP_HORARIO = (max(8, int(_env("FOLLOWUP_HORA_INICIO", "8"))), min(18, int(_env("FOLLOWUP_HORA_FIM", "18"))))
FOLLOWUP_DOMINGO = _env("FOLLOWUP_DOMINGO", "0") == "1"
# Templates aprovados no Meta para cada etapa fora da janela de 24h (parâmetro {{1}} = primeiro nome).
# Formato: "3:nome_template_d3,7:nome_template_d7,15:...,30:...,mensal:nome_template_mensal"
FOLLOWUP_TEMPLATES = dict(x.split(":", 1) for x in _lista("FOLLOWUP_TEMPLATES") if ":" in x)
GRUPO_VIP_LINK = _env("GRUPO_VIP_LINK")

# Relatórios por e-mail (SMTP; porta 465 usa SSL direto, 587 usa STARTTLS)
SMTP_HOST = _env("SMTP_HOST", "smtp.gmail.com")
SMTP_PORTA = int(_env("SMTP_PORTA", "587"))
SMTP_USUARIO = _env("SMTP_USUARIO")
SMTP_SENHA = _env("SMTP_SENHA")
RELATORIO_EMAIL = _lista("RELATORIO_EMAIL")  # destinatários
RELATORIO_HORA = int(_env("RELATORIO_HORA", "20"))  # relatório diário de leads, horário de SP

TZ = ZoneInfo(_env("TZ_CLINICA", "America/Sao_Paulo"))
DATA_DIR = Path(_env("DATA_DIR", str(BASE_DIR / "data")))
DB_PATH = DATA_DIR / "orya.db"

# Agenda da avaliação (sempre com a Dra. Danielly). Cada unidade tem o seu expediente;
# unidade sem expediente = horários sob consulta (o bot avisa a equipe para confirmar).
_SEG_A_SAB = {str(d): [["08:00", "18:00"]] for d in range(6)}  # 0 = segunda ... 6 = domingo; após 18h: sob consulta
AGENDA_PADRAO = {
    "duracao_min": 30,
    "antecedencia_min_horas": 4,  # dá tempo de pagar até 3 h antes
    "dias_a_frente": 14,
    "avaliacoes_simultaneas": 1,
    "bloqueios": [],  # ex.: ["2026-11-02", "2026-11-15 14:00"]
    # Dias de campanha: só o evento é oferecido nesse dia (a Dra. fica dedicada a ele em todas as unidades).
    "eventos": {
        "lavieen_day": {"nome": "Lavieen Day", "data": "2026-11-14", "unidade": "jardim_sao_paulo",
                        "inicio": "08:00", "fim": "20:00", "duracao_min": 60},
    },
    "unidades": {
        "jardim_sao_paulo": {
            "nome": "Jardim São Paulo",
            "endereco": "Rua Viri, 62, Jardim São Paulo, São Paulo/SP (CEP 02046-030)",
            "referencia": "pertinho de Santana e do Shopping Center Norte",
            "expediente": _SEG_A_SAB,
        },
        "tatuape": {"nome": "Tatuapé", "endereco": "", "referencia": "Zona Leste", "expediente": _SEG_A_SAB},
        "jardins": {"nome": "Jardins", "endereco": "", "referencia": "região dos Jardins", "expediente": {}},
    },
}


def carregar_agenda() -> dict:
    arquivo = BASE_DIR / "prompts" / "agenda.json"
    if arquivo.exists():
        return {**AGENDA_PADRAO, **json.loads(arquivo.read_text(encoding="utf-8"))}
    return AGENDA_PADRAO
