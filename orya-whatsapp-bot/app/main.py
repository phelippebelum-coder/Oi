"""Servidor: webhook do WhatsApp, página de teste e painel de leads."""

import asyncio
import base64
import csv
import io
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from . import config, db, midia, processador, rotinas, whatsapp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("orya")

ESTATICO = config.BASE_DIR / "static"


@asynccontextmanager
async def ciclo(_: FastAPI):
    db.iniciar()
    if not config.PAINEL_SENHA:
        log.warning("PAINEL_SENHA vazio: painel e página de teste estão abertos. Defina uma senha em produção.")
    tarefa = asyncio.create_task(rotinas.laco())
    if whatsapp.configurado():
        try:
            await whatsapp.assinar_waba()
        except Exception:
            log.exception("Não consegui assinar a WABA")
    yield
    tarefa.cancel()


app = FastAPI(title="ORYA WhatsApp Bot", lifespan=ciclo)
seguranca = HTTPBasic(auto_error=False)


def autenticar(cred: HTTPBasicCredentials | None = Depends(seguranca)):
    if not config.PAINEL_SENHA:
        return
    if not cred or not secrets.compare_digest(cred.password.encode(), config.PAINEL_SENHA.encode()):
        raise HTTPException(401, "Senha necessária", headers={"WWW-Authenticate": "Basic"})


@app.get("/")
async def saude():
    return {"ok": True, "whatsapp_configurado": whatsapp.configurado(), "modelo": config.CLAUDE_MODEL}


@app.get("/privacidade")
async def privacidade():
    """Política de privacidade pública (exigida pela Meta para publicar o app)."""
    return FileResponse(ESTATICO / "privacidade.html")


# ---------- webhook do Meta ----------

@app.get("/webhook")
async def verificar(request: Request):
    p = request.query_params
    if p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == config.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(p.get("hub.challenge", ""))
    raise HTTPException(403, "Token de verificação inválido")


@app.post("/webhook")
async def webhook(request: Request):
    corpo = await request.body()
    if not whatsapp.assinatura_valida(corpo, request.headers.get("x-hub-signature-256")):
        raise HTTPException(401, "Assinatura inválida")
    payload = await request.json()
    for ev in whatsapp.extrair_eventos(payload):
        if ev["tipo"] == "mensagem":
            asyncio.create_task(processador.receber_mensagem(ev, "whatsapp"))
        elif ev["tipo"] == "eco":
            asyncio.create_task(processador.receber_eco(ev))
    return {"ok": True}


# ---------- página de teste (simula o WhatsApp sem precisar do Meta) ----------

class MsgTeste(BaseModel):
    telefone: str
    texto: str
    nome: str | None = None
    cliente_retorno: bool = False
    anuncio: str | None = None


@app.get("/api/whatsapp/status", dependencies=[Depends(autenticar)])
async def whatsapp_status():
    """Reassina o app na WABA e mostra o estado do número."""
    return await whatsapp.assinar_waba()


@app.get("/teste", dependencies=[Depends(autenticar)])
async def pagina_teste():
    return FileResponse(ESTATICO / "teste.html")


@app.post("/api/teste/enviar", dependencies=[Depends(autenticar)])
async def teste_enviar(m: MsgTeste):
    tel = "teste-" + "".join(ch for ch in m.telefone if ch.isalnum())[:20]
    novo = db.obter_contato(tel) is None
    db.garantir_contato(tel, "teste", m.nome)
    if novo and m.cliente_retorno:
        db.atualizar_contato(tel, tipo="cliente")
    evento = {"de": tel, "nome": m.nome, "texto": m.texto, "msg_tipo": "text", "id": None}
    if novo and m.anuncio:
        evento["referral"] = {"headline": m.anuncio, "body": "", "source_type": "ad", "ctwa_clid": None}
    await processador.receber_mensagem(evento, "teste")
    return {"telefone": tel}


@app.post("/api/teste/reiniciar", dependencies=[Depends(autenticar)])
async def teste_reiniciar(m: MsgTeste):
    tel = "teste-" + "".join(ch for ch in m.telefone if ch.isalnum())[:20]
    db.apagar_contato(tel)
    return {"ok": True}


@app.post("/api/teste/followup/{telefone}", dependencies=[Depends(autenticar)])
async def teste_followup(telefone: str):
    """Simula o próximo passo da cadência (1, 3, 7, 15, 30 dias, mensal) como se ela tivesse sumido."""
    contato = db.obter_contato(telefone)
    if not contato:
        raise HTTPException(404)
    chave, limiar = rotinas.etapa_followup(contato["followups_enviados"])
    passado = (db.agora() - limiar - timedelta(minutes=1)).isoformat()
    db.atualizar_contato(telefone, ultima_msg_cliente_em=passado)
    await rotinas.enviar_followup(db.obter_contato(telefone), chave)
    return {"etapa": chave}


# ---------- painel ----------

@app.get("/painel", dependencies=[Depends(autenticar)])
async def pagina_painel():
    return FileResponse(ESTATICO / "painel.html")


@app.get("/api/contatos", dependencies=[Depends(autenticar)])
async def contatos():
    lista = db.listar_contatos()
    for c in lista:
        c["bot_pausado"] = processador.bot_pausado(c)
    return lista


@app.get("/api/contatos/{telefone}", dependencies=[Depends(autenticar)])
async def contato(telefone: str, depois_de: int = 0):
    c = db.obter_contato(telefone)
    if not c:
        raise HTTPException(404)
    c["bot_pausado"] = processador.bot_pausado(c)
    return {
        "contato": c,
        "conversa": db.obter_conversa(telefone, depois_de),
        "agendamentos": [a for a in db.listar_agendamentos() if a["telefone"] == telefone],
        "processando": telefone in processador._timers or (
            telefone in processador._travas and processador._travas[telefone].locked()),
    }


class AcaoContato(BaseModel):
    bot: str | None = None        # pausar | retomar
    tipo: str | None = None       # lead | cliente
    status: str | None = None


@app.post("/api/contatos/{telefone}", dependencies=[Depends(autenticar)])
async def alterar_contato(telefone: str, a: AcaoContato):
    if not db.obter_contato(telefone):
        raise HTTPException(404)
    campos = {}
    if a.bot == "pausar":
        campos["bot_pausado_ate"] = (db.agora() + timedelta(days=30)).isoformat()
    elif a.bot == "retomar":
        campos["bot_pausado_ate"] = None
    if a.tipo in ("lead", "cliente"):
        campos["tipo"] = a.tipo
    if a.status:
        campos["status"] = a.status
    db.atualizar_contato(telefone, **campos)
    return {"ok": True}


@app.get("/api/agendamentos", dependencies=[Depends(autenticar)])
async def agendamentos():
    return db.listar_agendamentos()


class AcaoAgendamento(BaseModel):
    status: str | None = None     # compareceu | faltou | cancelado | agendado
    pagamento: str | None = None  # pendente | pago


@app.post("/api/agendamentos/{ag_id}", dependencies=[Depends(autenticar)])
async def alterar_agendamento(ag_id: int, a: AcaoAgendamento):
    campos = {}
    if a.status:
        if a.status not in ("compareceu", "faltou", "cancelado", "agendado"):
            raise HTTPException(400)
        campos["status"] = a.status
    if a.pagamento:
        if a.pagamento not in ("pendente", "pago"):
            raise HTTPException(400)
        campos["pagamento"] = a.pagamento
    if campos:
        db.atualizar_agendamento(ag_id, **campos)
    return {"ok": True}


# ---------- fotos de antes e depois ----------

@app.get("/api/antes-depois", dependencies=[Depends(autenticar)])
async def listar_antes_depois():
    return [{"procedimento": p, "nome": n, "tem_foto": bool(midia.arquivo(p))} for p, n in midia.PROCEDIMENTOS.items()]


@app.get("/api/antes-depois/{proc}", dependencies=[Depends(autenticar)])
async def ver_antes_depois(proc: str):
    f = midia.arquivo(proc) if proc in midia.PROCEDIMENTOS else None
    if not f:
        raise HTTPException(404)
    return FileResponse(f, headers={"Cache-Control": "no-store"})


class FotoUpload(BaseModel):
    imagem_base64: str
    tipo: str
    autorizacao_paciente: bool


@app.post("/api/antes-depois/{proc}", dependencies=[Depends(autenticar)])
async def subir_antes_depois(proc: str, foto: FotoUpload):
    if not foto.autorizacao_paciente:
        raise HTTPException(400, "Confirme que a paciente assinou o termo de autorização de imagem.")
    try:
        midia.salvar(proc, base64.b64decode(foto.imagem_base64.split(",")[-1]), foto.tipo)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.get("/api/apresentacao", dependencies=[Depends(autenticar)])
async def ver_apresentacao():
    f = midia.apresentacao()
    if not f:
        raise HTTPException(404)
    return FileResponse(f, media_type="application/pdf", filename="ORYA - Como funciona.pdf")


class PdfUpload(BaseModel):
    pdf_base64: str


@app.post("/api/apresentacao", dependencies=[Depends(autenticar)])
async def subir_apresentacao(arq: PdfUpload):
    try:
        midia.salvar_apresentacao(base64.b64decode(arq.pdf_base64.split(",")[-1]))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.delete("/api/antes-depois/{proc}", dependencies=[Depends(autenticar)])
async def apagar_antes_depois(proc: str):
    midia.remover(proc)
    return {"ok": True}


@app.get("/api/avisos", dependencies=[Depends(autenticar)])
async def avisos():
    return db.listar_avisos()


@app.post("/api/avisos/lidos", dependencies=[Depends(autenticar)])
async def avisos_lidos():
    db.marcar_avisos_lidos()
    return {"ok": True}


@app.get("/api/exportar.csv", dependencies=[Depends(autenticar)])
async def exportar():
    """Lista para e-mail marketing: nome, e-mail, WhatsApp e categoria."""
    saida = io.StringIO()
    w = csv.writer(saida)
    w.writerow(["nome", "email", "aceita_email_marketing", "whatsapp", "tipo", "status", "temperatura", "interesses"])
    for c in db.listar_contatos():
        if c["canal"] == "teste":
            continue
        f = c["ficha"]
        w.writerow([f.get("nome_completo") or f.get("nome") or c.get("perfil_nome") or "", f.get("email") or "",
                    "sim" if f.get("aceita_email_marketing") else "não", c["telefone"], c["tipo"], c["status"],
                    c["temperatura"] or "", c.get("interesses") or ""])
    return PlainTextResponse(saida.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=contatos_orya.csv"})


class Importacao(BaseModel):
    csv: str


@app.post("/api/importar-clientes", dependencies=[Depends(autenticar)])
async def importar_clientes(imp: Importacao):
    """CSV com cabeçalho: telefone,nome,ultimo_procedimento,data_ultimo_procedimento"""
    total = 0
    for linha in csv.DictReader(io.StringIO(imp.csv.strip())):
        tel = "".join(ch for ch in (linha.get("telefone") or "") if ch.isdigit())
        if not tel:
            continue
        if len(tel) <= 11:
            tel = "55" + tel
        c = db.garantir_contato(tel, "whatsapp", linha.get("nome"))
        ficha = dict(c["ficha"])
        if linha.get("nome"):
            ficha.setdefault("nome_completo", linha["nome"])
            ficha.setdefault("nome", linha["nome"].split(" ")[0])
        if linha.get("ultimo_procedimento"):
            ficha["ultimo_procedimento_orya"] = (
                f"{linha['ultimo_procedimento']} ({linha.get('data_ultimo_procedimento') or 'data não informada'})")
        db.atualizar_contato(tel, tipo="cliente", ficha=ficha)
        total += 1
    return {"importados": total}
