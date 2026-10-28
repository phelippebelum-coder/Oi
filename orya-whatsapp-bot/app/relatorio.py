"""E-mails para o dono: avisos importantes na hora e relatório diário de todos os leads."""

import asyncio
import html
import logging
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from . import config, db

log = logging.getLogger("orya.relatorio")

ROTULO_TIPO = {
    "agendamento": "Nova avaliação agendada",
    "ligacao": "Cliente pediu ligação",
    "humano": "Conversa passada para a equipe",
    "cancelamento": "Avaliação cancelada",
    "remarcacao": "Avaliação remarcada",
}


def configurado() -> bool:
    return bool(config.SMTP_USUARIO and config.SMTP_SENHA and config.RELATORIO_EMAIL)


def _enviar(assunto: str, texto: str, corpo_html: str | None = None):
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = config.SMTP_USUARIO
    msg["To"] = ", ".join(config.RELATORIO_EMAIL)
    msg.set_content(texto)
    if corpo_html:
        msg.add_alternative(corpo_html, subtype="html")
    if config.SMTP_PORTA == 465:
        conexao = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORTA, timeout=30)
    else:
        conexao = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORTA, timeout=30)
    with conexao as s:
        if config.SMTP_PORTA != 465:
            s.starttls()
        s.login(config.SMTP_USUARIO, config.SMTP_SENHA)
        s.send_message(msg)


async def enviar(assunto: str, texto: str, corpo_html: str | None = None) -> bool:
    if not configurado():
        return False
    try:
        await asyncio.to_thread(_enviar, assunto, texto, corpo_html)
        return True
    except Exception:
        log.exception("Falha ao enviar e-mail")
        return False


async def aviso_imediato(tipo: str, texto: str):
    if tipo in ROTULO_TIPO:
        await enviar(f"ORYA · {ROTULO_TIPO[tipo]}", texto)


def _nome(c: dict) -> str:
    f = c["ficha"]
    return f.get("nome_completo") or f.get("nome") or c.get("perfil_nome") or "Sem nome"


def montar_relatorio(desde: datetime) -> tuple[str, str, int]:
    contatos = [c for c in db.listar_contatos()
                if c["canal"] != "teste" and datetime.fromisoformat(c["atualizado_em"]) >= desde]
    ordem = {"humano": 0, "agendado": 1, "qualificado": 2, "em_conversa": 3, "novo": 4}
    contatos.sort(key=lambda c: (ordem.get(c["status"], 5), {"quente": 0, "morna": 1}.get(c["temperatura"], 2)))

    contagem = lambda f: sum(1 for c in contatos if f(c))
    resumo = (f"Contatos com atividade: {len(contatos)} · agendadas: {contagem(lambda c: c['status'] == 'agendado')} · "
              f"quentes: {contagem(lambda c: c['temperatura'] == 'quente')} · "
              f"com a equipe: {contagem(lambda c: c['status'] == 'humano')}")
    linhas_txt, linhas_html = [resumo, ""], [f"<p><b>{html.escape(resumo)}</b></p>"]
    avisos_ligacao = [a for a in db.listar_avisos(500)
                      if a["tipo"] == "ligacao" and datetime.fromisoformat(a["criado_em"]) >= desde]
    if avisos_ligacao:
        linhas_txt.append("LIGAÇÕES PEDIDAS:")
        linhas_html.append("<h3>📞 Ligações pedidas</h3>")
        for a in avisos_ligacao:
            linhas_txt.append(a["texto"] + "\n")
            linhas_html.append(f"<p style='white-space:pre-wrap'>{html.escape(a['texto'])}</p>")
    linhas_html.append("<h3>Leads</h3>")
    for c in contatos:
        f = c["ficha"]
        ags = db.agendamentos_ativos(c["telefone"])
        ag = ""
        if ags:
            ag = "Avaliação: " + datetime.fromisoformat(ags[0]["inicio"]).astimezone(config.TZ).strftime("%d/%m %H:%M")
        campos = [
            ("Status", f"{c['status']} · {c['temperatura'] or '-'} · {'cliente' if c['tipo'] == 'cliente' else 'lead'}"),
            ("WhatsApp", f"+{c['telefone']}"),
            ("E-mail", f.get("email") or "-"),
            ("Interesse", c.get("interesses") or "-"),
            ("Queixa", f.get("queixa") or "-"),
            ("Resumo", f.get("resumo_conversa") or "-"),
            ("Agenda", ag or "-"),
            ("Follow-ups enviados", str(c["followups_enviados"])),
        ]
        linhas_txt.append(f"• {_nome(c)}\n" + "\n".join(f"  {k}: {v}" for k, v in campos))
        linhas_html.append(
            f"<div style='border-bottom:1px solid #eee;padding:8px 0'><b>{html.escape(_nome(c))}</b><br>"
            + "<br>".join(f"<span style='color:#8a7f76'>{k}:</span> {html.escape(v)}" for k, v in campos) + "</div>")
    return "\n".join(linhas_txt), "<div style='font-family:sans-serif;font-size:14px'>" + "".join(linhas_html) + "</div>", len(contatos)


async def relatorio_diario_se_for_hora():
    if not configurado():
        return
    agora = datetime.now(config.TZ)
    hoje = agora.strftime("%Y-%m-%d")
    if agora.hour < config.RELATORIO_HORA or db.obter_meta("relatorio_dia") == hoje:
        return
    db.definir_meta("relatorio_dia", hoje)
    texto, corpo_html, n = montar_relatorio(db.agora() - timedelta(hours=24))
    await enviar(f"ORYA · Relatório de leads {agora.strftime('%d/%m')} ({n} contatos)", texto, corpo_html)
