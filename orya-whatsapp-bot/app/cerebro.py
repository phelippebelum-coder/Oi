"""Cérebro do bot: monta o contexto, chama o Claude e executa as ferramentas."""

import json
import logging
import re
from datetime import datetime

import anthropic

from . import agenda, config, db, ferramentas

log = logging.getLogger("orya.cerebro")

MAX_RODADAS = 6
MSG_FALHA = "Oi! Tive uma instabilidade aqui agora, mas já chamei alguém da equipe pra continuar com você 🤍"

_cliente: anthropic.AsyncAnthropic | None = None


def cliente() -> anthropic.AsyncAnthropic:
    global _cliente
    if _cliente is None:
        _cliente = anthropic.AsyncAnthropic(max_retries=3)
    return _cliente


def prompt_sistema() -> str:
    base = (config.BASE_DIR / "prompts" / "sdr_orya.md").read_text(encoding="utf-8")
    precos = (config.BASE_DIR / "prompts" / "precos.md").read_text(encoding="utf-8")
    return base.replace("{{ATENDENTE}}", config.ATENDENTE).replace("{{PRECOS}}", precos)


def contexto_do_turno(contato: dict, nota: str | None = None) -> str:
    """Estado volátil (hora, ficha, agenda) vai numa mensagem de sistema no fim, para não quebrar o cache."""
    agora = datetime.now(config.TZ)
    dia = agenda.DIAS[agora.weekday()]
    aberta = 8 <= agora.hour < 20 and agora.weekday() < 6
    partes = [
        f"Agora: {dia}, {agora.strftime('%d/%m/%Y %H:%M')} (horário de São Paulo). "
        f"Clínica {'aberta' if aberta else 'fechada neste momento'}.",
        f"Tipo de contato: {'CLIENTE DE RETORNO da ORYA' if contato['tipo'] == 'cliente' else 'lead'}.",
        f"Nome no perfil do WhatsApp: {contato.get('perfil_nome') or 'desconhecido'}.",
        "Ficha atual: " + (json.dumps(contato["ficha"], ensure_ascii=False) if contato["ficha"] else "vazia"),
    ]
    ref = contato.get("referral")
    if ref:
        partes.append(
            "Ela chegou por um anúncio. Título: "
            f"{ref.get('headline') or '-'}; texto: {ref.get('body') or '-'}; link: {ref.get('source_url') or '-'}."
        )
    ags = db.agendamentos_ativos(contato["telefone"])
    if ags:
        descr = "; ".join(
            f"id {a['id']}: {agenda.descrever(datetime.fromisoformat(a['inicio']).astimezone(config.TZ))} "
            f"com {agenda.PROFISSIONAIS.get(a['profissional'], a['profissional'])} ({a['procedimento'] or '-'})"
            for a in ags
        )
        partes.append(f"Avaliações agendadas: {descr}.")
    if nota:
        partes.append(nota)
    return "[Contexto interno, não mostre à cliente]\n" + "\n".join(partes)


def _blocos(conteudo) -> list[dict]:
    return [b.model_dump(mode="json", exclude_none=True) for b in conteudo]


async def _chamar(mensagens: list[dict]):
    return await cliente().beta.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=16000,
        system=prompt_sistema(),
        tools=ferramentas.FERRAMENTAS,
        messages=mensagens,
        output_config={"effort": config.CLAUDE_EFFORT},
        cache_control={"type": "ephemeral"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )


def dividir_baloes(texto: str, maximo: int = 3) -> list[str]:
    texto = re.sub(r"\s*—\s*", ", ", texto).strip()
    partes = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    if len(partes) > maximo:
        partes = partes[: maximo - 1] + ["\n\n".join(partes[maximo - 1:])]
    return partes


async def responder(telefone: str, conteudo_cliente: list[dict], nota: str | None = None) -> list[str]:
    """Processa as novas mensagens da cliente e devolve os balões a enviar.

    O histórico é só acrescentado (nunca editado), como pede o preserved thinking.
    """
    contato = db.obter_contato(telefone)
    db.adicionar_historico(telefone, "user", conteudo_cliente)
    db.adicionar_historico(telefone, "system", contexto_do_turno(contato, nota))

    textos: list[str] = []
    for _ in range(MAX_RODADAS):
        try:
            resp = await _chamar(db.obter_historico(telefone))
        except anthropic.APIError:
            log.exception("Falha na API do Claude")
            await ferramentas.executar(
                "transferir_para_humano",
                {"motivo": "falha técnica no bot", "urgente": False, "resumo": "O bot não conseguiu responder."},
                telefone,
            )
            return [MSG_FALHA]

        db.adicionar_historico(telefone, "assistant", _blocos(resp.content))

        if resp.stop_reason == "refusal":
            log.warning("Recusa do modelo para %s: %s", telefone, resp.stop_details)
            await ferramentas.executar(
                "transferir_para_humano",
                {"motivo": "o assistente não pôde responder", "urgente": False, "resumo": "Revisar a conversa."},
                telefone,
            )
            return [MSG_FALHA]

        textos += [b.text for b in resp.content if b.type == "text" and b.text.strip()]
        usos = [b for b in resp.content if b.type == "tool_use"]
        if resp.stop_reason != "tool_use" or not usos:
            break

        resultados = []
        for uso in usos:
            try:
                saida = await ferramentas.executar(uso.name, dict(uso.input or {}), telefone)
                resultados.append({"type": "tool_result", "tool_use_id": uso.id, "content": saida})
            except Exception as e:
                log.exception("Erro na ferramenta %s", uso.name)
                resultados.append({"type": "tool_result", "tool_use_id": uso.id, "content": f"Erro: {e}",
                                   "is_error": True})
        db.adicionar_historico(telefone, "user", resultados)

    baloes = dividir_baloes("\n\n".join(textos))
    atualizacao = {"ultima_msg_bot_em": db.agora_iso()}
    if db.obter_contato(telefone)["status"] == "novo":
        atualizacao["status"] = "em_conversa"
    db.atualizar_contato(telefone, **atualizacao)
    return baloes
