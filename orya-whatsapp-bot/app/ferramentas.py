"""Ferramentas que o Claude usa: ficha, agenda e passagem para a equipe."""

from datetime import date, datetime, timedelta

from . import agenda, config, db, equipe, google_agenda, midia, whatsapp

# Fotos que o bot pediu para enviar nesta resposta (o processador envia depois dos balões de texto).
anexos_pendentes: dict[str, list[str]] = {}

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
                "nome_completo": {"type": "string", "description": "Nome e sobrenome"},
                "email": {"type": "string"},
                "aceita_email_marketing": {"type": "boolean", "description": "Passou o e-mail sabendo das novidades"},
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
                "resumo_conversa": {
                    "type": "string",
                    "description": "2 ou 3 frases sobre onde a conversa está (vai para o relatório do dono)",
                },
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
                "unidade": {"type": "string", "enum": ["jardim_sao_paulo", "tatuape", "jardins"], "description": "Unidade escolhida pela cliente"},
                "a_partir_de": {"type": "string", "description": "Data AAAA-MM-DD (opcional)"},
                "periodo": {"type": "string", "enum": ["manha", "tarde", "noite"]},
            },
            "required": ["unidade"],
        },
    },
    {
        "name": "agendar_avaliacao",
        "description": (
            "Agenda a avaliação com a Dra. Danielly no horário que a cliente escolheu (precisa ter vindo de "
            "ver_horarios). Antes, ela precisa saber o valor da avaliação e a regra de falta."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "inicio": {"type": "string", "description": "Data e hora ISO exatamente como veio de ver_horarios"},
                "unidade": {"type": "string", "enum": ["jardim_sao_paulo", "tatuape", "jardins"], "description": "Unidade escolhida pela cliente"},
                "procedimento_interesse": {"type": "string"},
                "forma_pagamento": {"type": "string", "enum": ["pix", "cartao", "a_definir"]},
                "resumo_para_equipe": {
                    "type": "string",
                    "description": (
                        "Resumo para a avaliação: nome/idade/bairro/origem · queixa nas palavras dela · interesse · "
                        "já fez · motivação/data · triagem · sensível a · valor já informado · temperatura"
                    ),
                },
            },
            "required": ["inicio", "unidade", "procedimento_interesse", "resumo_para_equipe"],
        },
    },
    {
        "name": "enviar_antes_depois",
        "description": (
            "Envia para a cliente uma foto real de antes e depois do procedimento de interesse, como referência. "
            "A foto chega logo depois da sua mensagem de texto. Uma por procedimento por conversa."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "procedimento": {"type": "string", "enum": list(midia.PROCEDIMENTOS)},
            },
            "required": ["procedimento"],
        },
    },
    {
        "name": "enviar_apresentacao",
        "description": (
            "Envia o PDF de apresentação da ORYA (Dra. Danielly, jornada em 5 etapas, metodologias, Plano Olhar Leve "
            "Anual, unidades). Chega logo depois da sua mensagem. Uma vez por conversa."
        ),
        "input_schema": {"type": "object", "additionalProperties": False, "properties": {}},
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
        "name": "solicitar_ligacao",
        "description": (
            "Pede para a equipe LIGAR para a cliente (ela pediu ligação ou precisa de atenção maior). "
            "Não pausa o atendimento por mensagem."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "motivo": {"type": "string"},
                "melhor_horario": {"type": "string", "description": "Quando ela prefere receber a ligação"},
                "resumo": {"type": "string", "description": "O que quem for ligar precisa saber"},
            },
            "required": ["motivo", "resumo"],
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
        return await _ver_horarios(entrada)
    if nome == "agendar_avaliacao":
        return await _agendar(contato, entrada)
    if nome == "remarcar_ou_cancelar":
        return await _remarcar(contato, entrada)
    if nome == "transferir_para_humano":
        return await _transferir(contato, entrada)
    if nome == "enviar_apresentacao":
        return _apresentacao(contato)
    if nome == "enviar_antes_depois":
        return _antes_depois(contato, entrada)
    if nome == "solicitar_ligacao":
        return await _ligacao(contato, entrada)
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


async def _ocupados_google() -> list:
    return await google_agenda.ocupados(*agenda.janela_busca())


async def _ver_horarios(entrada: dict) -> str:
    a_partir = None
    if entrada.get("a_partir_de"):
        try:
            a_partir = date.fromisoformat(entrada["a_partir_de"])
        except ValueError:
            pass
    unidade = entrada.get("unidade") or agenda.UNIDADE_PADRAO
    if unidade not in agenda.unidades():
        return "Unidade desconhecida. Use jardim_sao_paulo, tatuape ou jardins."
    if not agenda.agenda_aberta(unidade):
        return (f"A agenda da unidade {agenda.nome_unidade(unidade)} é sob consulta. Pergunte o dia e o período "
                "que ela prefere, diga que vai confirmar com a agenda da Dra. e use avisar_equipe com essa "
                "preferência. Ofereça também, como alternativa, horários no Jardim São Paulo.")
    livres = agenda.horarios_livres(unidade, a_partir, entrada.get("periodo"), ocupados=await _ocupados_google())
    if not livres:
        return "Sem horários livres nesse filtro. Tente outro período, outra data ou outra unidade."
    linhas = [f"{s.isoformat()} | {agenda.descrever(s)}" for s in livres]
    return (f"Horários livres com a Dra. Danielly na unidade {agenda.nome_unidade(unidade)} (ISO | como falar):\n"
            + "\n".join(linhas))


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
    prof = "danielly"
    unidade = entrada.get("unidade") or agenda.UNIDADE_PADRAO
    if not inicio:
        return "Data inválida. Use o ISO exatamente como veio de ver_horarios."
    google_agenda.limpar_cache()
    motivo = agenda.validar_horario(inicio, unidade, await _ocupados_google())
    if motivo:
        return f"Não foi possível agendar: {motivo}. Consulte ver_horarios de novo e ofereça outras opções."
    forma = entrada.get("forma_pagamento") or "a_definir"
    ag_id = db.criar_agendamento(tel, inicio.isoformat(), prof, entrada.get("procedimento_interesse"),
                                 entrada.get("resumo_para_equipe"), forma, unidade)
    prazo = agenda.prazo_pagamento(inicio)
    db.atualizar_agendamento(ag_id, prazo_pagamento=prazo.isoformat())
    await _criar_evento_google(ag_id, contato, inicio, unidade, entrada)
    db.atualizar_contato(tel, status="agendado", temperatura="quente", etapa="confirmacao")
    quando = agenda.descrever(inicio)
    await equipe.notificar(
        tel, "agendamento",
        f"✅ Nova avaliação agendada pelo bot\n{_rotulo_contato(contato)}\n"
        f"{quando} com {agenda.PROFISSIONAIS[prof]}, unidade {agenda.nome_unidade(unidade)}\nInteresse: {entrada.get('procedimento_interesse')}\n"
        f"💳 Avaliação R$ 200: pagamento PENDENTE ({ {'pix': 'Pix', 'cartao': 'link de cartão'}.get(forma, 'forma a definir') }), "
        f"prazo {prazo.strftime('%d/%m às %H:%M')}\n\n"
        f"{entrada.get('resumo_para_equipe', '')}",
    )
    clid = (contato.get("referral") or {}).get("ctwa_clid")
    if clid:
        await whatsapp.enviar_conversao("Schedule", clid)
    return (
        f"Agendado (id {ag_id}): {quando} ({inicio.strftime('%d/%m/%Y %H:%M')}) com {agenda.PROFISSIONAIS[prof]}, "
        f"unidade {agenda.nome_unidade(unidade)}. "
        f"Prazo do pagamento antecipado: até {_quando_prazo(prazo)} (sem pagamento até lá, o horário pode ser "
        "liberado). Agora siga com o pagamento (Pix ou link de cartão), depois o cadastro "
        "(nome, sobrenome e e-mail) se ainda faltar, e confirme com ela: data, hora, endereço "
        f"({agenda.endereco_unidade(unidade) or 'o endereço completo dessa unidade a equipe envia na confirmação'}), "
        "nome da Dra. e orientações "
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
        await _cancelar_evento_google(ag)
        db.atualizar_contato(tel, status="qualificado")
        await equipe.notificar(tel, "cancelamento",
                               f"❌ Avaliação cancelada pela cliente\n{_rotulo_contato(contato)}\n"
                               f"Era: {agenda.descrever(_parse_inicio(ag['inicio']))}\nMotivo: {entrada.get('motivo', '-')}")
        return "Cancelado. Acolha, pergunte se ela quer deixar um novo horário reservado."
    novo = _parse_inicio(entrada.get("novo_inicio"))
    if not novo:
        return "Para remarcar, informe novo_inicio no formato ISO de ver_horarios."
    google_agenda.limpar_cache()
    ocupados = [o for o in await _ocupados_google() if o[0] != _parse_inicio(ag["inicio"])]
    motivo = agenda.validar_horario(novo, ag.get("unidade") or agenda.UNIDADE_PADRAO, ocupados)
    if motivo:
        return f"Não foi possível remarcar: {motivo}. Consulte ver_horarios de novo."
    campos = {"inicio": novo.isoformat(), "lembrete_d1": 0, "lembrete_2h": 0}
    if ag.get("pagamento") != "pago":
        campos.update(prazo_pagamento=agenda.prazo_pagamento(novo).isoformat(), lembrete_pagamento=0)
    db.atualizar_agendamento(ag["id"], **campos)
    if ag.get("google_evento_id"):
        try:
            await google_agenda.mover_evento(ag["google_evento_id"], novo, config.carregar_agenda()["duracao_min"])
        except Exception:
            db.criar_aviso(tel, "google_agenda", f"Não consegui mover o evento no Google Agenda ({_rotulo_contato(contato)}).")
    await equipe.notificar(tel, "remarcacao",
                           f"🔁 Avaliação remarcada\n{_rotulo_contato(contato)}\n"
                           f"De: {agenda.descrever(_parse_inicio(ag['inicio']))}\nPara: {agenda.descrever(novo)}")
    extra = ""
    if ag.get("pagamento") != "pago":
        extra = f" O pagamento antecipado continua pendente: prazo até {_quando_prazo(agenda.prazo_pagamento(novo))}."
    return f"Remarcado para {agenda.descrever(novo)}. Confirme com ela.{extra}"


def _quando_prazo(prazo: datetime) -> str:
    return f"{agenda.descrever(prazo).split(' às')[0]} às {prazo.strftime('%H:%M')}"


async def _criar_evento_google(ag_id: int, contato: dict, inicio: datetime, unidade: str, entrada: dict):
    if not google_agenda.configurado():
        return
    f = contato["ficha"]
    nome = f.get("nome_completo") or f.get("nome") or contato.get("perfil_nome") or contato["telefone"]
    try:
        evento_id = await google_agenda.criar_evento(
            f"Avaliação · {nome} · {entrada.get('procedimento_interesse') or ''}".strip(" ·"),
            f"WhatsApp: +{contato['telefone']}\nUnidade: {agenda.nome_unidade(unidade)}\n"
            f"Pagamento: pendente (R$ 200)\n\n{entrada.get('resumo_para_equipe') or ''}\n\nAgendado pelo bot da ORYA.",
            inicio, config.carregar_agenda()["duracao_min"],
            agenda.endereco_unidade(unidade) or agenda.nome_unidade(unidade),
        )
        db.atualizar_agendamento(ag_id, google_evento_id=evento_id)
    except Exception:
        db.criar_aviso(contato["telefone"], "google_agenda",
                       f"Avaliação de {nome} agendada, mas não consegui criar o evento no Google Agenda.")


async def _cancelar_evento_google(ag: dict):
    if ag.get("google_evento_id"):
        try:
            await google_agenda.cancelar_evento(ag["google_evento_id"])
        except Exception:
            db.criar_aviso(ag["telefone"], "google_agenda", "Não consegui apagar o evento cancelado no Google Agenda.")


def _apresentacao(contato: dict) -> str:
    if not midia.apresentacao():
        return "A apresentação ainda não está disponível. Siga a conversa explicando a jornada em poucas linhas."
    ficha = dict(contato["ficha"])
    if ficha.get("apresentacao_enviada"):
        return "A apresentação já foi enviada nesta conversa. Pode fazer referência a ela."
    ficha["apresentacao_enviada"] = True
    db.atualizar_contato(contato["telefone"], ficha=ficha)
    anexos_pendentes.setdefault(contato["telefone"], []).append("apresentacao")
    return "PDF programado: chega logo depois da sua mensagem. Escreva uma frase curta apresentando o material."


def _antes_depois(contato: dict, entrada: dict) -> str:
    proc = entrada.get("procedimento")
    if proc not in midia.PROCEDIMENTOS:
        return "Procedimento inválido."
    if not midia.arquivo(proc):
        return ("Ainda não há foto de antes e depois cadastrada para esse procedimento. Não mencione foto; "
                "siga a conversa e use os diferenciais da Dra. Danielly.")
    ficha = dict(contato["ficha"])
    enviados = ficha.get("antes_depois_enviados") or []
    if proc in enviados:
        return "Essa foto já foi enviada nesta conversa. Não envie de novo; pode fazer referência a ela."
    ficha["antes_depois_enviados"] = [*enviados, proc]
    db.atualizar_contato(contato["telefone"], ficha=ficha)
    anexos_pendentes.setdefault(contato["telefone"], []).append(proc)
    return "Foto programada: ela chega logo depois da sua mensagem. Escreva uma frase curta apresentando a foto."


async def _ligacao(contato: dict, entrada: dict) -> str:
    tel = contato["telefone"]
    await equipe.notificar(
        tel, "ligacao",
        f"📞 Ligação do executivo de vendas: cliente pediu ligação ou precisa de atenção\n{_rotulo_contato(contato)}\n"
        f"Ligar para: +{tel}\nMelhor horário: {entrada.get('melhor_horario') or 'não informado'}\n"
        f"Motivo: {entrada.get('motivo')}\n\n{entrada.get('resumo', '')}",
    )
    return ("Pedido de ligação enviado para a equipe. Avise a cliente com carinho que vão ligar "
            "(no horário que ela preferir, entre 8h e 18h) e continue a conversa normalmente.")


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
        "continua com ela por aqui (fora das 8h às 18h, diga que retornam a partir das 8h). Não continue a venda."
    )
