"""Testes do fluxo sem chamar a API: o Claude é substituído por respostas roteirizadas."""

import asyncio
import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from anthropic.types.beta import BetaTextBlock, BetaToolUseBlock

from app import agenda, cerebro, config, db, processador, whatsapp


@pytest.fixture(autouse=True)
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(config, "AGRUPAR_SEGUNDOS", 0.05)
    monkeypatch.setattr(config, "WHATSAPP_TOKEN", "")
    db.iniciar()
    processador._pendentes.clear()
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
    slot = agenda.horarios_livres("danielly")[0]
    falso = ClaudeFalso([
        ([ferramenta("agendar_avaliacao", {"inicio": slot.isoformat(), "profissional": "danielly",
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
    assert any(a["tipo"] == "agendamento" for a in db.listar_avisos())
    # o mesmo horário não aparece mais como livre (1 avaliação por vez)
    assert slot not in agenda.horarios_livres("danielly")
    resultado = falso.chamadas[1][-1]["content"][0]["content"]
    assert resultado.startswith("Agendado")


def test_horario_ocupado_e_recusado(monkeypatch):
    slot = agenda.horarios_livres("danielly")[0]
    db.garantir_contato("a")
    db.criar_agendamento("a", slot.isoformat(), "danielly", "x", "y")
    assert agenda.validar_horario(slot, "danielly") == "horário já ocupado"
    assert agenda.validar_horario(slot, "suelen") is None


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
        assert cli.get("/painel").status_code == 200
        r = cli.post("/api/importar-clientes", json={"csv": "telefone,nome,ultimo_procedimento\n11999998888,Maria Souza,toxina"})
        assert r.json() == {"importados": 1}
        assert db.obter_contato("5511999998888")["tipo"] == "cliente"
        monkeypatch.setattr(config, "PAINEL_SENHA", "s3")
        assert cli.get("/painel").status_code == 401
        assert cli.get("/painel", auth=("orya", "s3")).status_code == 200


def test_dividir_baloes():
    assert cerebro.dividir_baloes("a\n\nb\n\nc\n\nd") == ["a", "b", "c\n\nd"]
    assert cerebro.dividir_baloes("Oi — tudo bem?") == ["Oi, tudo bem?"]


def test_prompt_sem_marcadores():
    p = cerebro.prompt_sistema()
    assert "{{" not in p and "Tabela de preços" in p
