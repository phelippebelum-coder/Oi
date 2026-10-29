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

# Sinais de anotação interna (resumo, ficha, falar da cliente em 3ª pessoa) que nunca podem chegar ao WhatsApp dela.
_FERRAMENTAS = ("atualizar_ficha|ver_horarios|agendar_avaliacao|remarcar_ou_cancelar|solicitar_ligacao|"
                "transferir_para_humano|avisar_equipe|enviar_antes_depois|enviar_apresentacao")
_VAZAMENTO = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in (
    r"\b(?:a|da|na|pela|pra|para a|com a|à)\s+(?:cliente|lead)\b",
    r"\bela\s+(?:pediu|perguntou|entrou em contato|não respondeu|parou de responder|sumiu)\b",
    r"^\W*(?:resumo|motivo|status|temperatura|etapa|interesse|queixa|origem|triagem|obje[cç][aã]o|"
    r"pr[oó]ximo passo|observa[cç][aã]o|nota)\W*:",
    r"follow-?up|contexto interno|notas? internas?|anota[cç](?:ão|ões) internas?|\bficha\b",
    rf"\b(?:{_FERRAMENTAS})\b",
)]
AVISO_VAZAMENTO = (
    "[Contexto interno, não mostre à cliente]\nSua última resposta NÃO foi enviada: ela tinha anotação interna "
    "(resumo, ficha ou comentário sobre a cliente em terceira pessoa). Escreva de novo só a mensagem para ela, "
    "falando com ela (você), sem recontar a conversa nem dizer o que ela fez ou pediu."
)

_cliente: anthropic.AsyncAnthropic | None = None


def cliente() -> anthropic.AsyncAnthropic:
    global _cliente
    if _cliente is None:
        _cliente = anthropic.AsyncAnthropic(max_retries=3)
    return _cliente


def _instrucoes_pagamento() -> str:
    linhas = []
    if config.PIX_CHAVE:
        linhas.append(f"- Pix: chave {config.PIX_CHAVE} (favorecido: {config.PIX_FAVORECIDO}). Mande a chave sozinha num "
                      "balão separado, pra ela copiar fácil, e peça o comprovante.")
    else:
        linhas.append("- Pix: a chave é enviada pela equipe. Diga que já vai chegar por aqui e use `avisar_equipe` "
                      "pedindo para enviar o Pix da avaliação.")
    if config.LINK_CARTAO:
        linhas.append(f"- Cartão de crédito: envie este link de pagamento: {config.LINK_CARTAO}")
    else:
        linhas.append("- Cartão de crédito: o link é gerado pela equipe. Diga que já vai chegar por aqui e use "
                      "`avisar_equipe` pedindo para enviar o link de cartão da avaliação.")
    linhas.append("- Ao agendar, informe em `agendar_avaliacao` a forma de pagamento escolhida.")
    return "\n".join(linhas)


def _descrever_unidades() -> str:
    linhas = []
    for chave, u in agenda.unidades().items():
        endereco = u.get("endereco") or ("atendimento em consultório na região; o local exato depende do consultório "
                                          "disponível e a equipe confirma o endereço com ela")
        sob_consulta = "" if agenda.agenda_aberta(chave) else " Horários nessa unidade: sob consulta."
        linhas.append(f"  - {u['nome']} ({chave}): {endereco}, {u.get('referencia', '')}.{sob_consulta}")
    return "\n".join(linhas)


def prompt_sistema() -> str:
    pasta = config.BASE_DIR / "prompts"
    base = (pasta / "sdr_orya.md").read_text(encoding="utf-8")
    promocoes = pasta / "promocoes.md"
    trocas = {
        "{{ATENDENTE}}": config.ATENDENTE,
        "{{PRECOS}}": (pasta / "precos.md").read_text(encoding="utf-8"),
        "{{PAGAMENTO}}": _instrucoes_pagamento(),
        "{{PROMOCOES}}": promocoes.read_text(encoding="utf-8") if promocoes.exists() else "(nenhuma no momento)",
        "{{UNIDADES}}": _descrever_unidades(),
        "{{GRUPO_VIP}}": (f"link: {config.GRUPO_VIP_LINK}" if config.GRUPO_VIP_LINK
                          else "o link ainda não foi configurado, então só comente que existe e que a equipe envia"),
    }
    for chave, valor in trocas.items():
        base = base.replace(chave, valor)
    return base


def contexto_do_turno(contato: dict, nota: str | None = None) -> str:
    """Estado volátil (hora, ficha, agenda) vai numa mensagem de sistema no fim, para não quebrar o cache."""
    agora = datetime.now(config.TZ)
    dia = agenda.DIAS[agora.weekday()]
    aberta = 8 <= agora.hour < 18 and agora.weekday() < 6
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
            f"na unidade {agenda.nome_unidade(a.get('unidade'))} ({a['procedimento'] or '-'})"
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


def parece_anotacao_interna(texto: str) -> bool:
    return any(p.search(texto) for p in _VAZAMENTO)


def dividir_baloes(texto: str, maximo: int = 3) -> list[str]:
    texto = re.sub(r"\s*—\s*", ", ", texto).strip()
    partes = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    if len(partes) > maximo:
        partes = partes[: maximo - 1] + ["\n\n".join(partes[maximo - 1:])]
    return partes


async def _gerar(telefone: str) -> list[str] | None:
    """Roda o Claude com as ferramentas até ele terminar. None = falhou (a equipe já foi chamada)."""
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
            return None

        db.adicionar_historico(telefone, "assistant", _blocos(resp.content))

        if resp.stop_reason == "refusal":
            log.warning("Recusa do modelo para %s: %s", telefone, resp.stop_details)
            await ferramentas.executar(
                "transferir_para_humano",
                {"motivo": "o assistente não pôde responder", "urgente": False, "resumo": "Revisar a conversa."},
                telefone,
            )
            return None

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
    return textos


async def responder(telefone: str, conteudo_cliente: list[dict], nota: str | None = None) -> list[str]:
    """Processa as novas mensagens da cliente e devolve os balões a enviar.

    O histórico é só acrescentado (nunca editado), como pede o preserved thinking.
    """
    contato = db.obter_contato(telefone)
    db.adicionar_historico(telefone, "user", conteudo_cliente)
    db.adicionar_historico(telefone, "system", contexto_do_turno(contato, nota))

    textos = await _gerar(telefone)
    if textos is None:
        return [MSG_FALHA]
    baloes = dividir_baloes("\n\n".join(textos))

    if bloqueados := [b for b in baloes if parece_anotacao_interna(b)]:
        # Anotação interna na resposta: nada sai, e o Claude reescreve uma vez só a mensagem para ela.
        log.warning("Resposta com anotação interna bloqueada para %s: %r", telefone, bloqueados)
        db.criar_aviso(telefone, "mensagem_bloqueada",
                       "A Aurora tentou mandar uma anotação interna para a cliente e foi bloqueada (não saiu): "
                       + " | ".join(bloqueados)[:900])
        db.adicionar_historico(telefone, "system", AVISO_VAZAMENTO)
        textos = await _gerar(telefone)
        if textos is None:
            return [MSG_FALHA]
        baloes = [b for b in dividir_baloes("\n\n".join(textos)) if not parece_anotacao_interna(b)]

    atualizacao = {"ultima_msg_bot_em": db.agora_iso()}
    if db.obter_contato(telefone)["status"] == "novo":
        atualizacao["status"] = "em_conversa"
    db.atualizar_contato(telefone, **atualizacao)
    return baloes
