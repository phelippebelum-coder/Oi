"""Testes do fluxo sem chamar a API: o Claude é substituído por respostas roteirizadas."""

import asyncio
import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from anthropic.types.beta import BetaTextBlock, BetaToolUseBlock

from datetime import timedelta

from app import (agenda, cerebro, config, db, ferramentas, google_agenda, midia, processador, relatorio, rotinas,
                 whatsapp)


@pytest.fixture(autouse=True)
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(config, "AGRUPAR_SEGUNDOS", 0.05)
    monkeypatch.setattr(config, "ESPERA_CLIENTE_SEGUNDOS", 0.05)
    monkeypatch.setattr(config, "RESPONDER_A_PARTIR_DE", (0, 0))  # testes rodam a qualquer hora
    monkeypatch.setattr(config, "WHATSAPP_TOKEN", "")
    db.iniciar()
    processador._timers.clear()
    processador._travas.clear()


class ClaudeFalso:
    def __init__(self, roteiro):
        self.roteiro = list(roteiro)
        self.chamadas = []

    async def __call__(self, mensagens):
        self.chamadas.append(json.loads(json.dumps(mensagens)))
        blocos, parada = self.roteiro.pop(0)
        return SimpleNamespace(content=blocos, stop_reason=parada, stop_details=None)


def texto(t):
    return BetaTextBlock(type="text", text=t)


def ferramenta(nome, entrada, i="t1"):
    return BetaToolUseBlock(type="tool_use", id=i, name=nome, input=entrada)


async def esperar():
    await asyncio.sleep(0.05)
    while processador._timers or any(t.locked() for t in processador._travas.values()):
        await asyncio.sleep(0.02)


def test_conversa_com_ficha_e_baloes(monkeypatch):
    falso = ClaudeFalso([
        ([ferramenta("atualizar_ficha", {"nome": "Carla", "interesses": ["bioestimulador"],
                                         "temperatura": "morna", "etapa": "descoberta"})], "tool_use"),
        ([texto("Oi, Carla! Que bom que você chamou 🤍\n\nMe conta: o que mais te incomoda?")], "end_turn"),
    ])
    monkeypatch.setattr(cerebro, "_chamar", falso)

    async def rodar():
        await processador.receber_mensagem(
            {"de": "5511999990000", "nome": "Carla", "texto": "oi", "msg_tipo": "text", "id": "w1"})
        await processador.receber_mensagem(
            {"de": "5511999990000", "nome": "Carla", "texto": "quanto custa o bioestimulador?",
             "msg_tipo": "text", "id": "w2"})
        await esperar()

    asyncio.run(rodar())
    # as duas mensagens seguidas viram uma única chamada
    assert len(falso.chamadas) == 2
    primeira = falso.chamadas[0]
    assert [m["role"] for m in primeira] == ["user", "system"]
    assert [b["text"] for b in primeira[0]["content"]] == ["oi", "quanto custa o bioestimulador?"]
    assert [m["role"] for m in falso.chamadas[1]] == ["user", "system", "assistant", "user"]

    conversa = db.obter_conversa("5511999990000")
    assert [c["autor"] for c in conversa] == ["cliente", "cliente", "bot", "bot"]
    c = db.obter_contato("5511999990000")
    assert c["ficha"]["interesses"] == ["bioestimulador"]
    assert c["temperatura"] == "morna"
    assert c["status"] == "em_conversa"


def test_agendamento_avisa_equipe(monkeypatch):
    slot = agenda.horarios_livres()[0]
    falso = ClaudeFalso([
        ([ferramenta("agendar_avaliacao", {"inicio": slot.isoformat(), "forma_pagamento": "pix",
                                           "unidade": "jardim_sao_paulo",
                                           "procedimento_interesse": "preenchimento labial",
                                           "resumo_para_equipe": "Ana, 32, Santana"})], "tool_use"),
        ([texto("Prontinho, Ana! Tá agendado.")], "end_turn"),
    ])
    monkeypatch.setattr(cerebro, "_chamar", falso)
    db.garantir_contato("5511988887777")
    baloes = asyncio.run(cerebro.responder("5511988887777", [{"type": "text", "text": "pode ser esse"}]))
    assert baloes == ["Prontinho, Ana! Tá agendado."]
    assert db.obter_contato("5511988887777")["status"] == "agendado"
    assert db.agendamentos_ativos("5511988887777")[0]["inicio"] == slot.isoformat()
    aviso = next(a for a in db.listar_avisos() if a["tipo"] == "agendamento")
    assert "pagamento PENDENTE (Pix)" in aviso["texto"]
    # o mesmo horário não aparece mais como livre (1 avaliação por vez)
    assert slot not in agenda.horarios_livres()
    resultado = falso.chamadas[1][-1]["content"][0]["content"]
    assert resultado.startswith("Agendado")


def test_horario_ocupado_e_recusado(monkeypatch):
    slot = agenda.horarios_livres()[0]
    db.garantir_contato("a")
    db.criar_agendamento("a", slot.isoformat(), "danielly", "x", "y")
    assert agenda.validar_horario(slot) == "horário já ocupado"
    assert 8 <= slot.hour < 18


def test_eco_da_equipe_pausa_o_bot(monkeypatch):
    falso = ClaudeFalso([([texto("Oi!")], "end_turn")])
    monkeypatch.setattr(cerebro, "_chamar", falso)

    async def rodar():
        await processador.receber_mensagem({"de": "5511977776666", "texto": "oi", "msg_tipo": "text", "id": "a1"})
        await esperar()
        await processador.receber_eco({"para": "5511977776666", "texto": "Oi, aqui é a Ju!", "id": "e1"})
        await processador.receber_mensagem({"de": "5511977776666", "texto": "oi Ju", "msg_tipo": "text", "id": "a2"})
        await esperar()

    asyncio.run(rodar())
    assert len(falso.chamadas) == 1  # depois do eco, o bot não respondeu
    autores = [c["autor"] for c in db.obter_conversa("5511977776666")]
    assert autores == ["cliente", "bot", "equipe", "cliente"]
    hist = db.obter_historico("5511977776666")
    assert hist[-1] == {"role": "user", "content": [{"type": "text", "text": "oi Ju"}]}


def test_mensagem_duplicada_e_ignorada(monkeypatch):
    falso = ClaudeFalso([([texto("Oi!")], "end_turn")])
    monkeypatch.setattr(cerebro, "_chamar", falso)

    async def rodar():
        ev = {"de": "5511900001111", "texto": "oi", "msg_tipo": "text", "id": "dup"}
        await processador.receber_mensagem(ev)
        await processador.receber_mensagem(dict(ev))
        await esperar()

    asyncio.run(rodar())
    assert len(db.obter_conversa("5511900001111")) == 2


def test_transferencia_pausa_e_avisa(monkeypatch):
    falso = ClaudeFalso([
        ([ferramenta("transferir_para_humano", {"motivo": "inchaço", "urgente": True, "resumo": "fez labial ontem"})],
         "tool_use"),
        ([texto("Já chamei a equipe pra falar com você agora 🤍")], "end_turn"),
    ])
    monkeypatch.setattr(cerebro, "_chamar", falso)
    db.garantir_contato("5511955554444")
    asyncio.run(cerebro.responder("5511955554444", [{"type": "text", "text": "meu labial inchou muito"}]))
    c = db.obter_contato("5511955554444")
    assert c["status"] == "humano" and processador.bot_pausado(c)
    assert "URGENTE" in db.listar_avisos()[0]["texto"]


def test_nono_digito_unifica_cliente_importada():
    db.garantir_contato("5511987654321")
    db.atualizar_contato("5511987654321", tipo="cliente")
    assert db.resolver_telefone_br("551187654321") == "551187654321"
    assert db.obter_contato("551187654321")["tipo"] == "cliente"
    assert db.obter_contato("5511987654321") is None


def test_webhook_parse_e_assinatura(monkeypatch):
    payload = {"entry": [{"changes": [{"value": {
        "contacts": [{"wa_id": "5511911112222", "profile": {"name": "Bia"}}],
        "messages": [{"from": "5511911112222", "id": "wamid.X", "type": "text", "text": {"body": "oi"},
                      "referral": {"headline": "Bioestimulador", "ctwa_clid": "abc"}}],
    }}, {"value": {"message_echoes": [{"to": "5511911112222", "id": "wamid.E", "type": "text",
                                        "text": {"body": "oi, sou da equipe"}}]}}]}]}
    evs = whatsapp.extrair_eventos(payload)
    assert evs[0]["tipo"] == "mensagem" and evs[0]["nome"] == "Bia" and evs[0]["referral"]["ctwa_clid"] == "abc"
    assert evs[1] == {"tipo": "eco", "id": "wamid.E", "para": "5511911112222", "msg_tipo": "text",
                      "texto": "oi, sou da equipe"}

    monkeypatch.setattr(config, "META_APP_SECRET", "segredo")
    corpo = json.dumps(payload).encode()
    assinatura = "sha256=" + hmac.new(b"segredo", corpo, hashlib.sha256).hexdigest()
    assert whatsapp.assinatura_valida(corpo, assinatura)
    assert not whatsapp.assinatura_valida(corpo, "sha256=errado")


def test_rotas_http(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setattr(config, "WHATSAPP_VERIFY_TOKEN", "tk")
    with TestClient(app) as cli:
        r = cli.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "tk", "hub.challenge": "123"})
        assert r.text == "123"
        assert cli.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "x"}).status_code == 403
        assert cli.get("/teste").status_code == 200
        assert "LGPD" in cli.get("/privacidade").text
        assert cli.get("/painel").status_code == 200
        r = cli.post("/api/importar-clientes", json={"csv": "telefone,nome,ultimo_procedimento\n11999998888,Maria Souza,toxina"})
        assert r.json() == {"importados": 1}
        assert db.obter_contato("5511999998888")["tipo"] == "cliente"
        r = cli.post("/api/importar-leads", json={"csv": "telefone,nome,interesse,resumo,ultima_msg_cliente,ultima_msg_equipe,etapa\n"
                                                  '11988887777,Bia,botox,"Quer botox, sumiu",24/10/2026 09:26,27/10/2026 10:33,2'})
        assert r.json() == {"importados": 1, "erros": []}
        lead = db.obter_contato(db.resolver_telefone_br("5511988887777"))
        assert lead["followups_enviados"] == 2 and lead["ficha"]["nome"] == "Bia"
        assert lead["ultima_msg_bot_em"] > lead["ultima_msg_cliente_em"]
        monkeypatch.setattr(config, "PAINEL_SENHA", "s3")
        assert cli.get("/painel").status_code == 401
        assert cli.get("/painel", auth=("orya", "s3")).status_code == 200


def test_dividir_baloes():
    assert cerebro.dividir_baloes("a\n\nb\n\nc\n\nd") == ["a", "b", "c\n\nd"]
    assert cerebro.dividir_baloes("Oi — tudo bem?") == ["Oi, tudo bem?"]


def test_prompt_sem_marcadores():
    p = cerebro.prompt_sistema()
    assert "{{" not in p and "Tabela de preços" in p


def _segunda_4h_no_passado():
    """Uma segunda-feira às 4h, uns 90 dias atrás (antes da última mensagem do bot)."""
    d = (db.agora() - timedelta(days=90)).astimezone(config.TZ)
    d -= timedelta(days=d.weekday())
    return d.replace(hour=4, minute=0, second=0, microsecond=0)


def test_momento_do_followup_e_as_10h():
    seg = _segunda_4h_no_passado()
    um_dia = timedelta(days=1)
    # contato às 4h da manhã: follow-up no dia seguinte às 10h
    assert rotinas.momento_followup(seg, um_dia) == (seg + um_dia).replace(hour=10)
    # contato às 17h: dia seguinte às 10h (um pouco antes das 24h)
    assert rotinas.momento_followup(seg.replace(hour=17), um_dia) == (seg + um_dia).replace(hour=10)
    # D+1 que cairia no domingo passa para segunda
    sab = seg + timedelta(days=5)
    assert rotinas.momento_followup(sab, um_dia) == (sab + timedelta(days=2)).replace(hour=10)
    # D+3 a partir de segunda: quinta às 10h
    assert rotinas.momento_followup(seg, timedelta(days=3)) == (seg + timedelta(days=3)).replace(hour=10)
    # só em horário comercial e nunca no domingo
    assert not rotinas.horario_de_followup(seg.replace(hour=7, minute=59))
    assert rotinas.horario_de_followup(seg.replace(hour=8))
    assert rotinas.horario_de_followup(seg.replace(hour=17, minute=59))
    assert not rotinas.horario_de_followup(seg.replace(hour=18))
    assert not rotinas.horario_de_followup((seg + timedelta(days=6)).replace(hour=10))


def test_cadencia_de_followup_e_resgate(monkeypatch):
    falso = ClaudeFalso([([texto("Oi!")], "end_turn")] + [([texto(f"follow {i}")], "end_turn") for i in range(7)]
                        + [([texto("Que bom te ver de novo!")], "end_turn")])
    monkeypatch.setattr(cerebro, "_chamar", falso)
    monkeypatch.setattr(config, "FOLLOWUP_DOMINGO", True)  # a cadência longa pode cair em qualquer dia
    tel = "teste-cad"

    async def rodar():
        await processador.receber_mensagem({"de": tel, "texto": "oi", "msg_tipo": "text"}, "teste")
        await esperar()
        enviados = []
        ultima = _segunda_4h_no_passado()
        for _ in range(7):
            c = db.obter_contato(tel)
            chave, espera = rotinas.etapa_followup(c["followups_enviados"])
            db.atualizar_contato(tel, ultima_msg_cliente_em=ultima.isoformat())
            prazo = rotinas.momento_followup(ultima, espera)
            assert prazo.hour == 10
            # um minuto antes das 10h do dia da etapa: não envia
            await rotinas.followups(prazo - timedelta(minutes=1))
            assert db.obter_contato(tel)["followups_enviados"] == c["followups_enviados"]
            await rotinas.followups(prazo)
            assert db.obter_contato(tel)["followups_enviados"] == c["followups_enviados"] + 1
            enviados.append(chave)
        assert enviados == ["1", "3", "7", "15", "30", "mensal", "mensal"]
        assert db.obter_contato(tel)["temperatura"] == "fria"
        # ela responde: cadência zera e o bot recebe a nota de resgate
        await processador.receber_mensagem({"de": tel, "texto": "oi, ainda tenho interesse", "msg_tipo": "text"},
                                           "teste")
        await esperar()

    asyncio.run(rodar())
    c = db.obter_contato(tel)
    assert c["followups_enviados"] == 0 and c["temperatura"] == "morna"
    ultima = falso.chamadas[-1]
    assert "VOLTOU a responder" in ultima[-1]["content"]
    nota_d3 = falso.chamadas[2][-1]["content"]
    assert "3 dias" in nota_d3 and "nunca SOBRE ela" in nota_d3


def test_followup_fora_do_horario_comercial_nao_sai(monkeypatch):
    falso = ClaudeFalso([([texto("Oi!")], "end_turn"), ([texto("follow")], "end_turn")])
    monkeypatch.setattr(cerebro, "_chamar", falso)
    tel = "teste-hora"

    async def rodar():
        await processador.receber_mensagem({"de": tel, "texto": "oi", "msg_tipo": "text"}, "teste")
        await esperar()
        ultima = _segunda_4h_no_passado()
        db.atualizar_contato(tel, ultima_msg_cliente_em=ultima.isoformat())
        terca = ultima + timedelta(days=1)
        for hora in (5, 7, 9):  # madrugada e antes das 10h: espera
            await rotinas.followups(terca.replace(hour=hora))
        assert db.obter_contato(tel)["followups_enviados"] == 0
        await rotinas.followups(terca.replace(hour=19))  # passou das 18h: espera o dia seguinte
        assert db.obter_contato(tel)["followups_enviados"] == 0
        await rotinas.followups(terca.replace(hour=10))
        assert db.obter_contato(tel)["followups_enviados"] == 1

    asyncio.run(rodar())


def test_followup_fora_da_janela_usa_template(monkeypatch):
    enviados = []

    async def template(para, nome, params):
        enviados.append((para, nome, params))

    monkeypatch.setattr(config, "WHATSAPP_TOKEN", "x")
    monkeypatch.setattr(config, "WHATSAPP_PHONE_NUMBER_ID", "1")
    monkeypatch.setattr(config, "FOLLOWUP_TEMPLATES", {"3": "orya_d3", "mensal": "orya_mensal"})
    monkeypatch.setattr(config, "GRUPO_VIP_LINK", "https://chat.whatsapp.com/xyz")
    monkeypatch.setattr(whatsapp, "enviar_template", template)
    tel = "5511912345678"
    seg = _segunda_4h_no_passado()
    db.garantir_contato(tel)
    db.atualizar_contato(tel, status="em_conversa", followups_enviados=1, ficha={"nome": "Ana"},
                         ultima_msg_cliente_em=seg.isoformat(), ultima_msg_bot_em=db.agora_iso())
    asyncio.run(rotinas.followups((seg + timedelta(days=3)).replace(hour=10)))
    assert enviados == [(tel, "orya_d3", ["Ana"])]
    # etapa sem template: não envia e avisa no painel
    asyncio.run(rotinas.followups((seg + timedelta(days=7)).replace(hour=10)))
    assert len(enviados) == 1 and db.listar_avisos()[0]["tipo"] == "followup_pendente"
    db.atualizar_contato(tel, followups_enviados=5)
    asyncio.run(rotinas.followups((seg + timedelta(days=60)).replace(hour=10)))
    assert enviados[-1] == (tel, "orya_mensal", ["Ana", "https://chat.whatsapp.com/xyz"])


def test_anotacao_interna_nao_vai_para_a_cliente(monkeypatch):
    vazou = "Resumo: a cliente entrou em contato pelo anúncio e pediu direto o valor do botox."
    falso = ClaudeFalso([
        ([texto("Oi, Bia! Lembrei de você aqui 🤍\n\n" + vazou)], "end_turn"),
        ([texto("Oi, Bia! Lembrei de você aqui 🤍 Ainda tá pensando no botox?")], "end_turn"),
    ])
    monkeypatch.setattr(cerebro, "_chamar", falso)
    tel = "teste-vazamento"
    db.garantir_contato(tel, "teste")
    baloes = asyncio.run(cerebro.responder(tel, [{"type": "text", "text": "oi"}]))
    assert baloes == ["Oi, Bia! Lembrei de você aqui 🤍 Ainda tá pensando no botox?"]
    assert "NÃO foi enviada" in falso.chamadas[1][-1]["content"]
    assert db.listar_avisos()[0]["tipo"] == "mensagem_bloqueada"
    for ok in ("Oi, Carla! Que bom que você chamou 🤍", "olha esse resultado de uma paciente da Dra., bem natural, né?",
               "vou deixar anotado pra Dra. avaliar com calma", "A jornada tem 5 etapas, da avaliação ao retorno."):
        assert not cerebro.parece_anotacao_interna(ok)
    for ruim in ("A cliente não respondeu desde ontem.", "Motivo: quer saber o valor", "ela pediu o preço direto",
                 "Vou usar atualizar_ficha agora", "Temperatura: morna"):
        assert cerebro.parece_anotacao_interna(ruim)


def test_agendado_nao_recebe_followup(monkeypatch):
    monkeypatch.setattr(config, "FOLLOWUP_HORARIO", (0, 24))
    tel = "teste-ag"
    db.garantir_contato(tel, "teste")
    db.atualizar_contato(tel, status="agendado", ultima_msg_cliente_em=(db.agora() - timedelta(days=5)).isoformat(),
                         ultima_msg_bot_em=(db.agora() - timedelta(days=4)).isoformat())
    asyncio.run(rotinas.followups())
    assert db.obter_contato(tel)["followups_enviados"] == 0


def test_ligacao_e_email(monkeypatch):
    emails = []
    monkeypatch.setattr(relatorio, "_enviar", lambda assunto, texto, h=None: emails.append((assunto, texto)))
    monkeypatch.setattr(config, "SMTP_USUARIO", "bot@x.com")
    monkeypatch.setattr(config, "SMTP_SENHA", "s")
    monkeypatch.setattr(config, "RELATORIO_EMAIL", ["dono@x.com"])
    falso = ClaudeFalso([
        ([ferramenta("solicitar_ligacao", {"motivo": "muitas dúvidas", "melhor_horario": "após 18h",
                                           "resumo": "quer harmonização"}),
          ferramenta("atualizar_ficha", {"nome_completo": "Paula Lima", "email": "paula@x.com",
                                         "aceita_email_marketing": True, "resumo_conversa": "Quer harmonização.",
                                         "temperatura": "quente"}, "t2")], "tool_use"),
        ([texto("Combinado, Paula! Vão te ligar depois das 18h.")], "end_turn"),
    ])
    monkeypatch.setattr(cerebro, "_chamar", falso)
    tel = "5511933332222"
    db.garantir_contato(tel)
    asyncio.run(cerebro.responder(tel, [{"type": "text", "text": "pode me ligar?"}]))
    assert emails[0][0] == "ORYA · Cliente pediu ligação" and "+5511933332222" in emails[0][1]
    # dois resultados de ferramenta voltam numa única mensagem
    assert len(falso.chamadas[1][-1]["content"]) == 2
    texto_rel, html_rel, n = relatorio.montar_relatorio(db.agora() - timedelta(hours=24))
    assert n == 1 and "Paula Lima" in texto_rel and "paula@x.com" in texto_rel and "LIGAÇÕES PEDIDAS" in texto_rel


def test_exportar_csv():
    from fastapi.testclient import TestClient
    from app.main import app

    db.garantir_contato("5511944443333")
    db.atualizar_contato("5511944443333", ficha={"nome_completo": "Bia Reis", "email": "bia@x.com",
                                                 "aceita_email_marketing": True})
    with TestClient(app) as cli:
        r = cli.get("/api/exportar.csv")
    assert "Bia Reis,bia@x.com,sim,5511944443333" in r.text


def test_prompt_regras_de_preco():
    p = cerebro.prompt_sistema()
    assert "Suelen" not in p and "{{" not in p
    for trecho in ("Paris", "Tatuapé", "Shopping Center Norte", "Jardins", "Domingo é sob consulta",
                   "link de cartão", "executivo de vendas"):
        assert trecho in p
    for trecho in ("R$ 1.100", "R$ 1.400", "R$ 229", "R$ 1.037", "R$ 150", "R$ 200", "10x sem juros"):
        assert trecho in p


PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
       b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\xa0\x9b\x00\x00\x00\x00IEND\xaeB`\x82")


def test_antes_depois_enviado_depois_do_texto(monkeypatch):
    midia.salvar("botox", PNG, "image/png")
    falso = ClaudeFalso([
        ([ferramenta("enviar_antes_depois", {"procedimento": "botox"}),
          ferramenta("enviar_antes_depois", {"procedimento": "labial"}, "t2")], "tool_use"),
        ([texto("Olha esse resultado de uma paciente da Dra., bem natural, né? 🤍")], "end_turn"),
        ([ferramenta("enviar_antes_depois", {"procedimento": "botox"})], "tool_use"),
        ([texto("Lembra daquela foto?")], "end_turn"),
    ])
    monkeypatch.setattr(cerebro, "_chamar", falso)
    tel = "teste-foto"
    db.garantir_contato(tel, "teste")
    asyncio.run(processador.responder_e_enviar(tel, "teste", [{"type": "text", "text": "quero botox"}]))
    resultados = falso.chamadas[1][-1]["content"]
    assert resultados[0]["content"].startswith("Foto programada")
    assert "Ainda não há foto" in resultados[1]["content"]
    assert [c["texto"] for c in db.obter_conversa(tel)][-2:] == [
        "Olha esse resultado de uma paciente da Dra., bem natural, né? 🤍", "[foto:botox]"]
    # não reenvia a mesma foto
    asyncio.run(processador.responder_e_enviar(tel, "teste", [{"type": "text", "text": "e aí?"}]))
    assert "já foi enviada" in falso.chamadas[3][-1]["content"][0]["content"]
    assert db.obter_conversa(tel)[-1]["texto"] == "Lembra daquela foto?"
    assert not ferramentas.anexos_pendentes


def test_foto_whatsapp_reaproveita_upload(monkeypatch):
    chamadas = []

    async def subir(dados, mime, nome):
        chamadas.append(("subir", mime))
        return "MID1"

    async def enviar_img(para, mid, legenda):
        chamadas.append(("enviar", para, mid, "autorizada" in legenda))

    monkeypatch.setattr(whatsapp, "subir_midia", subir)
    monkeypatch.setattr(whatsapp, "enviar_imagem", enviar_img)
    midia.salvar("labial", PNG, "image/png")
    asyncio.run(midia.enviar("5511900000001", "labial"))
    asyncio.run(midia.enviar("5511900000002", "labial"))
    assert chamadas == [("subir", "image/png"), ("enviar", "5511900000001", "MID1", True),
                        ("enviar", "5511900000002", "MID1", True)]


def test_upload_exige_autorizacao_e_pagamento_no_painel():
    import base64 as b64
    from fastapi.testclient import TestClient
    from app.main import app

    corpo = {"imagem_base64": "data:image/png;base64," + b64.b64encode(PNG).decode(), "tipo": "image/png"}
    with TestClient(app) as cli:
        assert cli.post("/api/antes-depois/botox", json={**corpo, "autorizacao_paciente": False}).status_code == 400
        assert cli.post("/api/antes-depois/botox", json={**corpo, "autorizacao_paciente": True}).status_code == 200
        assert cli.get("/api/antes-depois/botox").content == PNG
        assert [f["tem_foto"] for f in cli.get("/api/antes-depois").json()] == [True, False, False, False]
        db.garantir_contato("x")
        ag = db.criar_agendamento("x", "2030-01-01T10:00:00-03:00", "danielly", "botox", "r", "pix")
        assert db.listar_agendamentos()[0]["pagamento"] == "pendente"
        cli.post(f"/api/agendamentos/{ag}", json={"pagamento": "pago"})
        assert db.listar_agendamentos()[0]["pagamento"] == "pago"


def test_unidades_compartilham_a_agenda_da_dra(monkeypatch):
    from app import ferramentas as f
    base = config.carregar_agenda()
    unidades = {k: dict(v) for k, v in base["unidades"].items()}
    unidades["tatuape"]["expediente"] = unidades["jardim_sao_paulo"]["expediente"]
    monkeypatch.setattr(config, "carregar_agenda", lambda: {**base, "unidades": unidades})
    slot = agenda.horarios_livres("tatuape")[0]
    db.garantir_contato("a")
    db.criar_agendamento("a", slot.isoformat(), "danielly", "botox", "r", "pix", "jardim_sao_paulo")
    # ocupada no Jardim São Paulo = ocupada no Tatuapé também
    assert agenda.validar_horario(slot, "tatuape") == "horário já ocupado"
    assert slot not in agenda.horarios_livres("tatuape")
    # Jardins sem expediente: sob consulta
    assert "sob consulta" in asyncio.run(f._ver_horarios({"unidade": "jardins"}))
    assert "sob consulta" in agenda.validar_horario(slot, "jardins")


def test_apresentacao_pdf_enviada_uma_vez(monkeypatch):
    falso = ClaudeFalso([
        ([ferramenta("enviar_apresentacao", {})], "tool_use"),
        ([texto("Te mandei nossa apresentação, dá uma olhadinha 🤍")], "end_turn"),
        ([ferramenta("enviar_apresentacao", {})], "tool_use"),
        ([texto("Conseguiu ver?")], "end_turn"),
    ])
    monkeypatch.setattr(cerebro, "_chamar", falso)
    tel = "teste-pdf"
    db.garantir_contato(tel, "teste")
    asyncio.run(processador.responder_e_enviar(tel, "teste", [{"type": "text", "text": "como funciona?"}]))
    assert db.obter_conversa(tel)[-1]["texto"] == "[pdf:apresentacao]"
    asyncio.run(processador.responder_e_enviar(tel, "teste", [{"type": "text", "text": "ok"}]))
    assert "já foi enviada" in falso.chamadas[3][-1]["content"][0]["content"]
    assert midia.apresentacao().name == "apresentacao_orya.pdf"


def test_prompt_plano_anual_e_unidades():
    p = cerebro.prompt_sistema()
    for trecho in ("R$ 3.080", "Plano Olhar Leve Anual", "Método Essência ORYA", "Tatuapé", "enviar_apresentacao"):
        assert trecho in p


def test_prazo_de_pagamento():
    from datetime import datetime
    agora = datetime(2026, 11, 2, 10, 0, tzinfo=config.TZ)
    # marcou com antecedência: até 24 h antes
    assert agenda.prazo_pagamento(datetime(2026, 11, 5, 15, 0, tzinfo=config.TZ), agora) == \
        datetime(2026, 11, 4, 15, 0, tzinfo=config.TZ)
    # marcou para o mesmo dia: até 3 h antes
    assert agenda.prazo_pagamento(datetime(2026, 11, 2, 18, 0, tzinfo=config.TZ), agora) == \
        datetime(2026, 11, 2, 15, 0, tzinfo=config.TZ)
    # marcou para amanhã cedo (menos de 25 h): também até 3 h antes
    assert agenda.prazo_pagamento(datetime(2026, 11, 3, 9, 0, tzinfo=config.TZ), agora) == \
        datetime(2026, 11, 3, 6, 0, tzinfo=config.TZ)


def test_lembrete_e_cancelamento_automatico_sem_pagamento(monkeypatch):
    monkeypatch.setattr(config, "CANCELAR_SEM_PAGAMENTO", True)
    tel = "teste-pag"
    db.garantir_contato(tel, "teste")
    db.atualizar_contato(tel, status="agendado", ficha={"nome": "Lu"}, ultima_msg_cliente_em=db.agora_iso())
    inicio = db.agora() + timedelta(hours=26)
    ag = db.criar_agendamento(tel, inicio.astimezone(config.TZ).isoformat(), "danielly", "botox", "r", "pix")
    criado = (db.agora() - timedelta(hours=3)).isoformat()
    db.atualizar_agendamento(ag, criado_em=criado, prazo_pagamento=(db.agora() + timedelta(hours=1)).isoformat())
    asyncio.run(rotinas.pagamentos())
    assert "Lu, passando pra lembrar" in db.obter_conversa(tel)[-1]["texto"]
    assert db.listar_avisos()[0]["tipo"] == "pagamento"
    asyncio.run(rotinas.pagamentos())  # não repete o lembrete
    assert len(db.obter_conversa(tel)) == 1
    # passou do prazo: cancela, libera o horário e avisa
    db.atualizar_agendamento(ag, prazo_pagamento=(db.agora() - timedelta(minutes=1)).isoformat())
    asyncio.run(rotinas.pagamentos())
    assert db.agendamentos_ativos(tel) == []
    assert db.obter_contato(tel)["status"] == "qualificado"
    assert "liberou o seu horário" in db.obter_conversa(tel)[-1]["texto"]
    assert "cancelada automaticamente" in db.listar_avisos()[0]["texto"]


def test_pago_nao_cancela():
    tel = "teste-pago"
    db.garantir_contato(tel, "teste")
    ag = db.criar_agendamento(tel, (db.agora() + timedelta(hours=5)).isoformat(), "danielly", "botox", "r", "pix")
    db.atualizar_agendamento(ag, pagamento="pago", prazo_pagamento=(db.agora() - timedelta(hours=1)).isoformat())
    asyncio.run(rotinas.pagamentos())
    assert len(db.agendamentos_ativos(tel)) == 1


def test_google_agenda_bloqueia_e_recebe_evento(monkeypatch):
    slots = agenda.horarios_livres()
    ocupado = slots[0]
    criados = []

    async def ocupados(ini, fim):
        return [(ocupado, ocupado + timedelta(minutes=30))]

    async def criar(titulo, descricao, inicio, dur, local):
        criados.append((titulo, inicio, local, "Pagamento: pendente" in descricao))
        return "EVT1"

    monkeypatch.setattr(google_agenda, "configurado", lambda: True)
    monkeypatch.setattr(google_agenda, "ocupados", ocupados)
    monkeypatch.setattr(google_agenda, "criar_evento", criar)
    texto_horarios = asyncio.run(ferramentas._ver_horarios({"unidade": "jardim_sao_paulo"}))
    assert ocupado.isoformat() not in texto_horarios
    tel = "5511966665555"
    db.garantir_contato(tel)
    db.atualizar_contato(tel, ficha={"nome_completo": "Rita Alves"})
    r = asyncio.run(ferramentas.executar("agendar_avaliacao", {
        "inicio": ocupado.isoformat(), "unidade": "jardim_sao_paulo", "procedimento_interesse": "botox",
        "resumo_para_equipe": "x"}, tel))
    assert "ocupado no Google Agenda" in r
    livre = next(s for s in slots[1:])
    r = asyncio.run(ferramentas.executar("agendar_avaliacao", {
        "inicio": livre.isoformat(), "unidade": "jardim_sao_paulo", "procedimento_interesse": "botox",
        "resumo_para_equipe": "x", "forma_pagamento": "pix"}, tel))
    assert r.startswith("Agendado") and "Prazo do pagamento" in r
    assert criados == [("Avaliação · Rita Alves · botox", livre, "Rua Viri, 62, Jardim São Paulo, São Paulo/SP (CEP 02046-030)", True)]
    ag = db.agendamentos_ativos(tel)[0]
    assert ag["google_evento_id"] == "EVT1" and ag["prazo_pagamento"]


def test_prazo_vencido_so_avisa_por_padrao():
    assert config.CANCELAR_SEM_PAGAMENTO is False
    tel = "teste-avisa"
    db.garantir_contato(tel, "teste")
    ag = db.criar_agendamento(tel, (db.agora() + timedelta(hours=5)).isoformat(), "danielly", "botox", "r", "pix")
    db.atualizar_agendamento(ag, prazo_pagamento=(db.agora() - timedelta(minutes=1)).isoformat(), lembrete_pagamento=1)
    asyncio.run(rotinas.pagamentos())
    asyncio.run(rotinas.pagamentos())
    assert len(db.agendamentos_ativos(tel)) == 1
    avisos = [a for a in db.listar_avisos() if "Prazo do pagamento venceu" in a["texto"]]
    assert len(avisos) == 1


def test_aurora_no_prompt():
    p = cerebro.prompt_sistema()
    assert "Aurora, do atendimento da ORYA" in p and "sou a Aurora" in p


def test_espera_1min30_e_madrugada():
    from datetime import datetime
    tz = config.TZ
    tarde = datetime(2026, 10, 29, 15, 0, tzinfo=tz)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config, "ESPERA_CLIENTE_SEGUNDOS", 90)
        mp.setattr(config, "RESPONDER_A_PARTIR_DE", (6, 30))
        assert processador.momento_de_responder(tarde, "whatsapp") == tarde + timedelta(seconds=90)
        # de madrugada: só às 6h30
        for h, m in ((0, 0), (3, 15), (6, 0), (6, 28)):
            assert processador.momento_de_responder(datetime(2026, 10, 29, h, m, tzinfo=tz), "whatsapp") == \
                datetime(2026, 10, 29, 6, 30, tzinfo=tz)
        # 23h59: a espera passaria da meia-noite, então fica para as 6h30 do dia seguinte
        assert processador.momento_de_responder(datetime(2026, 10, 29, 23, 59, tzinfo=tz), "whatsapp") == \
            datetime(2026, 10, 30, 6, 30, tzinfo=tz)
        assert processador.momento_de_responder(datetime(2026, 10, 29, 6, 30, tzinfo=tz), "whatsapp") == \
            datetime(2026, 10, 29, 6, 31, 30, tzinfo=tz)
        # página de teste não espera nem respeita a madrugada
        assert processador.momento_de_responder(datetime(2026, 10, 29, 3, 0, tzinfo=tz), "teste") < \
            datetime(2026, 10, 29, 3, 1, tzinfo=tz)


def test_whatsapp_junta_mensagens_e_responde_uma_vez(monkeypatch):
    falso = ClaudeFalso([([texto("Oi, Ju! Me conta mais 🤍")], "end_turn")])
    monkeypatch.setattr(cerebro, "_chamar", falso)
    tel = "5511955554444"

    async def rodar():
        for i, t in enumerate(("oi", "vi o anúncio", "quanto é o botox?")):
            await processador.receber_mensagem({"de": tel, "texto": t, "msg_tipo": "text", "id": f"w{i}"})
        assert db.obter_contato(tel)["pendente"]["blocos"][-1]["text"] == "quanto é o botox?"
        await esperar()

    asyncio.run(rodar())
    assert len(falso.chamadas) == 1
    textos = [b["text"] for m in falso.chamadas[0] if m["role"] == "user" for b in m["content"]]
    assert textos == ["oi", "vi o anúncio", "quanto é o botox?"]
    assert db.obter_contato(tel)["pendente"] is None


def test_mensagem_da_madrugada_e_respondida_depois_mesmo_com_reinicio(monkeypatch):
    falso = ClaudeFalso([([texto("Bom dia, Ana! 🤍")], "end_turn")])
    monkeypatch.setattr(cerebro, "_chamar", falso)
    tel = "5511944443333"
    db.garantir_contato(tel)
    futuro = db.agora() + timedelta(hours=3)
    db.atualizar_contato(tel, pendente={"blocos": [{"type": "text", "text": "oi, tô sem sono kkk"}],
                                         "canal": "whatsapp", "responder_em": futuro.isoformat()})

    async def rodar():
        await processador.retomar_pendentes()  # ainda não é hora: só agenda
        await asyncio.sleep(0.05)
        assert not falso.chamadas and tel in processador._timers
        processador._timers.pop(tel).cancel()  # simula o servidor reiniciando
        db.atualizar_contato(tel, pendente={**db.obter_contato(tel)["pendente"],
                                             "responder_em": (db.agora() - timedelta(minutes=1)).isoformat()})
        await processador.retomar_pendentes()
        await esperar()

    asyncio.run(rodar())
    assert len(falso.chamadas) == 1 and db.obter_contato(tel)["pendente"] is None


def test_equipe_responde_durante_a_espera(monkeypatch):
    falso = ClaudeFalso([])
    monkeypatch.setattr(cerebro, "_chamar", falso)
    monkeypatch.setattr(config, "ESPERA_CLIENTE_SEGUNDOS", 5)
    tel = "5511933332222"

    async def rodar():
        await processador.receber_mensagem({"de": tel, "texto": "oi", "msg_tipo": "text", "id": "x1"})
        await processador.receber_eco({"para": tel, "texto": "Oi! Aqui é a Bruna", "msg_tipo": "text", "id": "e1"})
        await asyncio.sleep(0.05)

    asyncio.run(rodar())
    assert not falso.chamadas and db.obter_contato(tel)["pendente"] is None
    assert db.obter_historico(tel)[0] == {"role": "user", "content": [{"type": "text", "text": "oi"}]}


def test_fornecedor_recebe_uma_resposta_e_depois_silencio(monkeypatch):
    falso = ClaudeFalso([
        ([ferramenta("marcar_fornecedor", {"resumo": "Distribuidora X oferecendo ácido hialurônico"})], "tool_use"),
        ([texto("Recebido, obrigada! Vou repassar pra equipe responsável.")], "end_turn"),
        ([texto("Que legal! O botox do terço superior é R$ 1.100...")], "end_turn"),
    ])
    monkeypatch.setattr(cerebro, "_chamar", falso)
    triagens = []

    async def triagem(texto):
        triagens.append(texto)
        return "botox" in texto

    monkeypatch.setattr(cerebro, "fornecedor_quer_servico", triagem)
    tel = "5511922221111"

    async def rodar():
        await processador.receber_mensagem({"de": tel, "texto": "Bom dia, sou representante da Distribuidora X",
                                            "msg_tipo": "text", "id": "f1"})
        await esperar()
        assert db.obter_contato(tel)["status"] == "fornecedor"
        assert db.listar_avisos()[0]["tipo"] == "fornecedor"
        for i, t in enumerate(("segue nosso catálogo", "conseguiu ver?")):
            await processador.receber_mensagem({"de": tel, "texto": t, "msg_tipo": "text", "id": f"f2{i}"})
            await esperar()
        assert len(falso.chamadas) == 2  # nenhuma chamada ao Claude depois da primeira resposta
        await processador.receber_mensagem({"de": tel, "texto": "aliás, quanto é o botox pra minha esposa?",
                                            "msg_tipo": "text", "id": "f3"})
        await esperar()

    asyncio.run(rodar())
    assert triagens == ["segue nosso catálogo", "conseguiu ver?", "aliás, quanto é o botox pra minha esposa?"]
    assert len(falso.chamadas) == 3 and db.obter_contato(tel)["status"] == "em_conversa"
    assert "marcado como fornecedor" in falso.chamadas[2][-1]["content"]
    # o silêncio não perdeu o contexto: as mensagens do catálogo estão no histórico
    assert any(b.get("text") == "segue nosso catálogo" for m in falso.chamadas[2] if m["role"] == "user"
               for b in (m["content"] if isinstance(m["content"], list) else []))
    conversa = [m["texto"] for m in db.obter_conversa(tel) if m["autor"] == "bot"]
    assert conversa == ["Recebido, obrigada! Vou repassar pra equipe responsável.", "[pdf:apresentacao]",
                        "Que legal! O botox do terço superior é R$ 1.100..."]


def test_fornecedor_sem_followup(monkeypatch):
    tel = "teste-forn"
    db.garantir_contato(tel, "teste")
    db.atualizar_contato(tel, status="fornecedor", ultima_msg_cliente_em=(db.agora() - timedelta(days=5)).isoformat(),
                         ultima_msg_bot_em=(db.agora() - timedelta(days=4)).isoformat())
    asyncio.run(rotinas.followups((db.agora() - timedelta(days=0)).astimezone(config.TZ).replace(hour=10)))
    assert db.obter_contato(tel)["followups_enviados"] == 0


def test_listas_whatsapp_por_anuncio():
    from app import equipe
    lead = {"tipo": "lead", "origem": "anuncio", "referral": {"headline": "Lavieen Day"}, "ficha": {}}
    assert equipe.listas(lead) == ["LEAD NOVO", "ADS LAVIEEN"]
    lead = {"tipo": "lead", "origem": "anuncio", "referral": None, "ficha": {"interesses": ["botox"]}}
    assert equipe.listas(lead) == ["LEAD NOVO", "ADS BOTOX"]
    assert equipe.listas({"tipo": "lead", "ficha": {"interesses": ["botox"]}}) == ["LEAD NOVO"]
    assert equipe.listas({"tipo": "cliente", "ficha": {}}) == []


def test_lavieen_day_horarios_do_evento(monkeypatch):
    from datetime import datetime as dt
    from app import agenda
    cfg = dict(config.AGENDA_PADRAO)
    amanha = (dt.now(config.TZ) + timedelta(days=2)).date().isoformat()
    cfg["eventos"] = {"lavieen_day": {"nome": "Lavieen Day", "data": amanha, "unidade": "jardim_sao_paulo",
                                      "inicio": "08:00", "fim": "20:00", "duracao_min": 60}}
    monkeypatch.setattr(config, "carregar_agenda", lambda: cfg)
    livres = agenda.horarios_evento("lavieen_day")
    assert [s.hour for s in livres] == list(range(8, 20))
    assert agenda.validar_evento("lavieen_day", livres[4]) is None
    # o dia do evento sai da agenda normal
    assert not [s for s in agenda.horarios_livres("jardim_sao_paulo", limite=100) if s.date().isoformat() == amanha]
    assert agenda.validar_horario(livres[0], "jardim_sao_paulo") is not None
