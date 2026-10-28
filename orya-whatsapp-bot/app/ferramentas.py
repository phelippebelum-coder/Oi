"""Ferramentas que o Claude usa: ficha, agenda e passagem para a equipe."""

from datetime import date, datetime, timedelta

from . import agenda, config, db, equipe, whatsapp

ETAPAS = ["abertura", "descoberta", "triagem", "cadastro", "preco", "agendamento", "confirmacao", "pos_agendamento"]

FERRAMENTAS = [
    {
        "name": "atualizar_ficha",
        "description": (
            "Registra na ficha da cliente o que você descobriu na conversa (categorização para a equipe). "
            "Envie só os campos novos ou alterados. Use sempre que aprender algo útil."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "nome": {"type": "string", "description": "Como ela gosta de ser chamada"},
                "nome_completo": {"type": "string"},
                "data_nascimento": {"type": "string", "description": "DD/MM/AAAA"},
                "bairro": {"type": "string"},
                "como_conheceu": {"type": "string", "description": "Instagram, anúncio, indicação de quem, Google..."},
                "melhor_periodo": {"type": "string", "enum": ["manha", "tarde", "noite"]},
                "queixa": {"type": "string", "description": "A queixa nas palavras dela"},
                "interesses": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Procedimentos de interesse, ex.: bioestimulador, preenchimento labial",
                },
                "ja_fez": {"type": "string", "description": "Procedimentos que já fez e como foi"},
                "motivacao_ou_data": {"type": "string", "description": "Evento, data especial, motivo pessoal"},
                "triagem": {"type": "string", "description": "Resumo das respostas de saúde"},
                "alertas_saude": {"type": "string", "description": "Gestante, lactante, anticoagulante, alergia etc."},
                "objecoes": {"type": "string"},
                "sensivel_a": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["preco", "dor", "naturalidade", "tempo", "seguranca"]},
                },
                "valor_informado": {"type": "string", "description": "Valores que você já passou para ela"},
                "temperatura": {"type": "string", "enum": ["quente", "morna", "fria"]},
                "etapa": {"type": "string", "enum": ETAPAS},
                "tipo": {"type": "string", "enum": ["lead", "cliente"], "description": "cliente = já fez procedimento na ORYA"},
                "opt_out": {"type": "boolean", "description": "true se ela pediu para não receber mensagens"},
                "observacoes": {"type": "string"},
            },
        },
    },
    {
        "name": "ver_horarios",
        "description": (
            "Consulta horários livres reais para a avaliação. Use antes de oferecer horários. "
            "Ofereça à cliente só duas opções da lista."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "profissional": {
                    "type": "string", "enum": ["danielly", "suelen"],
                    "description": "danielly = faciais; suelen = corporais",
                },
                "a_partir_de": {"type": "string", "description": "Data AAAA-MM-DD (opcional)"},
                "periodo": {"type": "string", "enum": ["manha", "tarde", "noite"]},
            },
            "required": ["profissional"],
        },
    },
    {
        "name": "agendar_avaliacao",
        "description": "Agenda a avaliação no horário que a cliente escolheu (precisa ter vindo de ver_horarios).",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "inicio": {"type": "string", "description": "Data e hora ISO exatamente como veio de ver_horarios"},
                "profissional": {"type": "string", "enum": ["danielly", "suelen"]},
                "procedimento_interesse": {"type": "string"},
                "resumo_para_equipe": {
                    "type": "string",
                    "description": (
                        "Resumo para a avaliação: nome/idade/bairro/origem · queixa nas palavras dela · interesse · "
                        "já fez · motivação/data · triagem · sensível a · valor já informado · temperatura"
                    ),
                },
            },
            "required": ["inicio", "profissional", "procedimento_interesse", "resumo_para_equipe"],
        },
    },
    {
        "name": "remarcar_ou_cancelar",
        "description": "Remarca ou cancela uma avaliação já agendada desta cliente.",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "acao": {"type": "string", "enum": ["remarcar", "cancelar"]},
                "agendamento_id": {"type": "integer"},
                "novo_inicio": {"type": "string", "description": "ISO de ver_horarios (só para remarcar)"},
                "motivo": {"type": "string"},
            },
            "required": ["acao", "agendamento_id"],
        },
    },
    {
        "name": "transferir_para_humano",
        "description": (
            "Passa a conversa para a equipe e PAUSA o atendimento automático desta cliente. "
            "Use nos casos descritos em 'Quando passar para uma pessoa'."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "motivo": {"type": "string"},
                "urgente": {"type": "boolean", "description": "true para intercorrência ou reclamação"},
                "resumo": {"type": "string", "description": "O que a equipe precisa saber para continuar"},
            },
            "required": ["motivo", "resumo"],
        },
    },
    {
        "name": "avisar_equipe",
        "description": (
            "Manda um aviso para a equipe SEM pausar o atendimento (ex.: preço que não está na tabela, "
            "pedido que precisa de confirmação)."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"motivo": {"type": "string"}},
            "required": ["motivo"],
        },
    },
]


def _rotulo_contato(c: dict) -> str:
    f = c["ficha"]
    nome = f.get("nome_completo") or f.get("nome") or c.get("perfil_nome") or "Sem nome"
    return f"{nome} ({c['telefone']})"


async def executar(nome: str, entrada: dict, telefone: str) -> str:
    contato = db.obter_contato(telefone)
    if nome == "atualizar_ficha":
        return _atualizar_ficha(contato, entrada)
    if nome == "ver_horarios":
        return _ver_horarios(entrada)
    if nome == "agendar_avaliacao":
        return await _agendar(contato, entrada)
    if nome == "remarcar_ou_cancelar":
        return await _remarcar(contato, entrada)
    if nome == "transferir_para_humano":
        return await _transferir(contato, entrada)
    if nome == "avisar_equipe":
        await equipe.notificar(telefone, "aviso", f"ORYA bot · {_rotulo_contato(contato)}\n{entrada.get('motivo', '')}")
        return "Equipe avisada. Continue o atendimento normalmente."
    return f"Ferramenta desconhecida: {nome}"


def _atualizar_ficha(contato: dict, entrada: dict) -> str:
    ficha = dict(contato["ficha"])
    for k, v in entrada.items():
        if v in (None, "", []):
            continue
        if isinstance(v, list):
            atuais = ficha.get(k) or []
            ficha[k] = list(dict.fromkeys([*atuais, *v]))
        else:
            ficha[k] = v
    campos = {"ficha": ficha}
    if "temperatura" in entrada:
        campos["temperatura"] = entrada["temperatura"]
    if "etapa" in entrada:
        campos["etapa"] = entrada["etapa"]
    if "tipo" in entrada:
        campos["tipo"] = entrada["tipo"]
    if ficha.get("interesses"):
        campos["interesses"] = ", ".join(ficha["interesses"])
    status = contato["status"]
    if entrada.get("opt_out"):
        status = "opt_out"
    elif status in ("novo", "em_conversa") and entrada.get("etapa") in ("triagem", "cadastro", "preco", "agendamento"):
        status = "qualificado"
    campos["status"] = status
    db.atualizar_contato(contato["telefone"], **campos)
    return "Ficha atualizada."


def _ver_horarios(entrada: dict) -> str:
    a_partir = None
    if entrada.get("a_partir_de"):
        try:
            a_partir = date.fromisoformat(entrada["a_partir_de"])
        except ValueError:
            pass
    prof = entrada.get("profissional", "danielly")
    livres = agenda.horarios_livres(prof, a_partir, entrada.get("periodo"))
    if not livres:
        return "Sem horários livres nesse filtro. Tente outro período ou outra data."
    linhas = [f"{s.isoformat()} | {agenda.descrever(s)}" for s in livres]
    return f"Horários livres com {agenda.PROFISSIONAIS[prof]} (ISO | como falar):\n" + "\n".join(linhas)


def _parse_inicio(texto: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(texto)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=config.TZ)
    return dt.astimezone(config.TZ)


async def _agendar(contato: dict, entrada: dict) -> str:
    tel = contato["telefone"]
    existentes = db.agendamentos_ativos(tel)
    if existentes:
        e = existentes[0]
        return (
            f"Ela já tem avaliação agendada (id {e['id']}) em {agenda.descrever(_parse_inicio(e['inicio']))}. "
            "Use remarcar_ou_cancelar se ela quiser mudar."
        )
    inicio = _parse_inicio(entrada.get("inicio"))
    prof = entrada.get("profissional", "danielly")
    if not inicio:
        return "Data inválida. Use o ISO exatamente como veio de ver_horarios."
    motivo = agenda.validar_horario(inicio, prof)
    if motivo:
        return f"Não foi possível agendar: {motivo}. Consulte ver_horarios de novo e ofereça outras opções."
    ag_id = db.criar_agendamento(tel, inicio.isoformat(), prof, entrada.get("procedimento_interesse"),
                                 entrada.get("resumo_para_equipe"))
    db.atualizar_contato(tel, status="agendado", temperatura="quente", etapa="confirmacao")
    quando = agenda.descrever(inicio)
    await equipe.notificar(
        tel, "agendamento",
        f"✅ Nova avaliação agendada pelo bot\n{_rotulo_contato(contato)}\n"
        f"{quando} com {agenda.PROFISSIONAIS[prof]}\nInteresse: {entrada.get('procedimento_interesse')}\n\n"
        f"{entrada.get('resumo_para_equipe', '')}",
    )
    clid = (contato.get("referral") or {}).get("ctwa_clid")
    if clid:
        await whatsapp.enviar_conversao("Schedule", clid)
    return (
        f"Agendado (id {ag_id}): {quando} ({inicio.strftime('%d/%m/%Y %H:%M')}) com {agenda.PROFISSIONAIS[prof]}. "
        "Agora confirme com ela: data, hora, endereço (Rua Viri, 62, Jardim São Paulo), nome da Dra. e orientações "
        "(sem maquiagem se for facial, trazer o nome dos medicamentos, chegar 10 min antes). Se faltar algum dado do "
        "cadastro, peça de forma leve."
    )


async def _remarcar(contato: dict, entrada: dict) -> str:
    tel = contato["telefone"]
    ags = {a["id"]: a for a in db.agendamentos_ativos(tel)}
    ag = ags.get(entrada.get("agendamento_id"))
    if not ag:
        return f"Agendamento não encontrado para esta cliente. Ativos: {list(ags) or 'nenhum'}."
    if entrada["acao"] == "cancelar":
        db.atualizar_agendamento(ag["id"], status="cancelado")
        db.atualizar_contato(tel, status="qualificado")
        await equipe.notificar(tel, "cancelamento",
                               f"❌ Avaliação cancelada pela cliente\n{_rotulo_contato(contato)}\n"
                               f"Era: {agenda.descrever(_parse_inicio(ag['inicio']))}\nMotivo: {entrada.get('motivo', '-')}")
        return "Cancelado. Acolha, pergunte se ela quer deixar um novo horário reservado."
    novo = _parse_inicio(entrada.get("novo_inicio"))
    if not novo:
        return "Para remarcar, informe novo_inicio no formato ISO de ver_horarios."
    motivo = agenda.validar_horario(novo, ag["profissional"])
    if motivo:
        return f"Não foi possível remarcar: {motivo}. Consulte ver_horarios de novo."
    db.atualizar_agendamento(ag["id"], inicio=novo.isoformat(), lembrete_d1=0, lembrete_2h=0)
    await equipe.notificar(tel, "remarcacao",
                           f"🔁 Avaliação remarcada\n{_rotulo_contato(contato)}\n"
                           f"De: {agenda.descrever(_parse_inicio(ag['inicio']))}\nPara: {agenda.descrever(novo)}")
    return f"Remarcado para {agenda.descrever(novo)}. Confirme com ela."


async def _transferir(contato: dict, entrada: dict) -> str:
    tel = contato["telefone"]
    ate = db.agora() + timedelta(hours=max(config.PAUSA_HUMANO_HORAS, 24))
    db.atualizar_contato(tel, status="humano", bot_pausado_ate=ate.isoformat())
    selo = "🚨 URGENTE" if entrada.get("urgente") else "🙋 Atendimento humano"
    await equipe.notificar(
        tel, "humano",
        f"{selo}\n{_rotulo_contato(contato)}\nMotivo: {entrada.get('motivo')}\n\n{entrada.get('resumo', '')}\n\n"
        "O bot ficou pausado nesta conversa. Responda pelo WhatsApp Business.",
    )
    return (
        "Transferido e bot pausado. Escreva só uma mensagem curta e acolhedora avisando que alguém da equipe "
        "continua com ela por aqui (fora das 9h às 20h, diga que retornam a partir das 9h). Não continue a venda."
    )
