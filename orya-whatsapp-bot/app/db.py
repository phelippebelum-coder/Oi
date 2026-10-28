"""Banco SQLite: contatos (ficha/categorização), histórico, agendamentos e avisos."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS contatos (
    telefone TEXT PRIMARY KEY,
    canal TEXT NOT NULL DEFAULT 'whatsapp',
    perfil_nome TEXT,
    tipo TEXT NOT NULL DEFAULT 'lead',          -- lead | cliente
    status TEXT NOT NULL DEFAULT 'novo',        -- novo | em_conversa | qualificado | agendado | humano | perdido | opt_out
    temperatura TEXT,                           -- quente | morna | fria
    etapa TEXT,
    interesses TEXT,
    origem TEXT,
    referral TEXT,
    ficha TEXT NOT NULL DEFAULT '{}',
    bot_pausado_ate TEXT,
    followups_enviados INTEGER NOT NULL DEFAULT 0,
    ultima_msg_cliente_em TEXT,
    ultima_msg_bot_em TEXT,
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telefone TEXT NOT NULL,
    papel TEXT NOT NULL,
    conteudo TEXT NOT NULL,
    criado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_historico_tel ON historico(telefone, id);
CREATE TABLE IF NOT EXISTS conversa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telefone TEXT NOT NULL,
    autor TEXT NOT NULL,                        -- cliente | bot | equipe | sistema
    texto TEXT NOT NULL,
    criado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_conversa_tel ON conversa(telefone, id);
CREATE TABLE IF NOT EXISTS agendamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telefone TEXT NOT NULL,
    inicio TEXT NOT NULL,
    profissional TEXT NOT NULL,
    procedimento TEXT,
    status TEXT NOT NULL DEFAULT 'agendado',    -- agendado | cancelado | compareceu | faltou
    resumo TEXT,
    lembrete_d1 INTEGER NOT NULL DEFAULT 0,
    lembrete_2h INTEGER NOT NULL DEFAULT 0,
    criado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS avisos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telefone TEXT,
    tipo TEXT NOT NULL,
    texto TEXT NOT NULL,
    lido INTEGER NOT NULL DEFAULT 0,
    criado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    chave TEXT PRIMARY KEY,
    valor TEXT
);
CREATE TABLE IF NOT EXISTS processados (
    wamid TEXT PRIMARY KEY,
    criado_em TEXT NOT NULL
);
"""


def agora() -> datetime:
    return datetime.now(timezone.utc)


def agora_iso() -> str:
    return agora().isoformat()


@contextmanager
def conectar():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def iniciar():
    with conectar() as con:
        con.executescript(ESQUEMA)
        colunas = {l["name"] for l in con.execute("PRAGMA table_info(agendamentos)")}
        if "pagamento" not in colunas:
            con.execute("ALTER TABLE agendamentos ADD COLUMN pagamento TEXT NOT NULL DEFAULT 'pendente'")
        if "forma_pagamento" not in colunas:
            con.execute("ALTER TABLE agendamentos ADD COLUMN forma_pagamento TEXT")
        if "unidade" not in colunas:
            con.execute("ALTER TABLE agendamentos ADD COLUMN unidade TEXT NOT NULL DEFAULT 'jardim_sao_paulo'")


# ---------- contatos ----------

def obter_contato(telefone: str) -> dict | None:
    with conectar() as con:
        linha = con.execute("SELECT * FROM contatos WHERE telefone = ?", (telefone,)).fetchone()
    return _contato(linha) if linha else None


def garantir_contato(telefone: str, canal: str = "whatsapp", perfil_nome: str | None = None) -> dict:
    with conectar() as con:
        con.execute(
            "INSERT OR IGNORE INTO contatos (telefone, canal, perfil_nome, criado_em, atualizado_em) "
            "VALUES (?, ?, ?, ?, ?)",
            (telefone, canal, perfil_nome, agora_iso(), agora_iso()),
        )
        if perfil_nome:
            con.execute(
                "UPDATE contatos SET perfil_nome = ? WHERE telefone = ? AND (perfil_nome IS NULL OR perfil_nome = '')",
                (perfil_nome, telefone),
            )
    return obter_contato(telefone)


def atualizar_contato(telefone: str, **campos):
    if not campos:
        return
    if "ficha" in campos and isinstance(campos["ficha"], dict):
        campos["ficha"] = json.dumps(campos["ficha"], ensure_ascii=False)
    if "referral" in campos and isinstance(campos["referral"], dict):
        campos["referral"] = json.dumps(campos["referral"], ensure_ascii=False)
    campos["atualizado_em"] = agora_iso()
    sets = ", ".join(f"{k} = ?" for k in campos)
    with conectar() as con:
        con.execute(f"UPDATE contatos SET {sets} WHERE telefone = ?", (*campos.values(), telefone))


def listar_contatos(filtro: dict | None = None) -> list[dict]:
    sql, params = "SELECT * FROM contatos", []
    if filtro:
        conds = []
        for k, v in filtro.items():
            conds.append(f"{k} = ?")
            params.append(v)
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY atualizado_em DESC"
    with conectar() as con:
        return [_contato(l) for l in con.execute(sql, params).fetchall()]


def _contato(linha: sqlite3.Row) -> dict:
    c = dict(linha)
    c["ficha"] = json.loads(c.get("ficha") or "{}")
    c["referral"] = json.loads(c["referral"]) if c.get("referral") else None
    return c


def apagar_contato(telefone: str):
    with conectar() as con:
        for tabela in ("contatos", "historico", "conversa", "agendamentos", "avisos"):
            con.execute(f"DELETE FROM {tabela} WHERE telefone = ?", (telefone,))


# ---------- histórico da API (append-only) ----------

def adicionar_historico(telefone: str, papel: str, conteudo):
    with conectar() as con:
        con.execute(
            "INSERT INTO historico (telefone, papel, conteudo, criado_em) VALUES (?, ?, ?, ?)",
            (telefone, papel, json.dumps(conteudo, ensure_ascii=False), agora_iso()),
        )


def obter_historico(telefone: str) -> list[dict]:
    with conectar() as con:
        linhas = con.execute(
            "SELECT papel, conteudo FROM historico WHERE telefone = ? ORDER BY id", (telefone,)
        ).fetchall()
    return [{"role": l["papel"], "content": json.loads(l["conteudo"])} for l in linhas]


# ---------- conversa legível (painel) ----------

def registrar_conversa(telefone: str, autor: str, texto: str):
    with conectar() as con:
        con.execute(
            "INSERT INTO conversa (telefone, autor, texto, criado_em) VALUES (?, ?, ?, ?)",
            (telefone, autor, texto, agora_iso()),
        )


def obter_conversa(telefone: str, depois_de: int = 0) -> list[dict]:
    with conectar() as con:
        return [
            dict(l)
            for l in con.execute(
                "SELECT * FROM conversa WHERE telefone = ? AND id > ? ORDER BY id", (telefone, depois_de)
            ).fetchall()
        ]


# ---------- agendamentos ----------

def criar_agendamento(telefone, inicio_iso, profissional, procedimento, resumo, forma_pagamento=None,
                      unidade="jardim_sao_paulo") -> int:
    with conectar() as con:
        cur = con.execute(
            "INSERT INTO agendamentos (telefone, inicio, profissional, procedimento, resumo, forma_pagamento, unidade, "
            "criado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (telefone, inicio_iso, profissional, procedimento, resumo, forma_pagamento, unidade, agora_iso()),
        )
        return cur.lastrowid


def agendamentos_ativos(telefone: str | None = None) -> list[dict]:
    sql = "SELECT * FROM agendamentos WHERE status = 'agendado'"
    params = []
    if telefone:
        sql += " AND telefone = ?"
        params.append(telefone)
    with conectar() as con:
        return [dict(l) for l in con.execute(sql + " ORDER BY inicio", params).fetchall()]


def listar_agendamentos() -> list[dict]:
    with conectar() as con:
        return [dict(l) for l in con.execute("SELECT * FROM agendamentos ORDER BY inicio DESC").fetchall()]


def atualizar_agendamento(ag_id: int, **campos):
    sets = ", ".join(f"{k} = ?" for k in campos)
    with conectar() as con:
        con.execute(f"UPDATE agendamentos SET {sets} WHERE id = ?", (*campos.values(), ag_id))


# ---------- avisos para a equipe ----------

def criar_aviso(telefone: str | None, tipo: str, texto: str):
    with conectar() as con:
        con.execute(
            "INSERT INTO avisos (telefone, tipo, texto, criado_em) VALUES (?, ?, ?, ?)",
            (telefone, tipo, texto, agora_iso()),
        )


def listar_avisos(limite: int = 100) -> list[dict]:
    with conectar() as con:
        return [dict(l) for l in con.execute("SELECT * FROM avisos ORDER BY id DESC LIMIT ?", (limite,)).fetchall()]


def marcar_avisos_lidos():
    with conectar() as con:
        con.execute("UPDATE avisos SET lido = 1")


# ---------- deduplicação de webhooks ----------

def ja_processado(wamid: str) -> bool:
    with conectar() as con:
        cur = con.execute(
            "INSERT OR IGNORE INTO processados (wamid, criado_em) VALUES (?, ?)", (wamid, agora_iso())
        )
        return cur.rowcount == 0


def resolver_telefone_br(telefone: str) -> str:
    """O WhatsApp às vezes manda celulares do Brasil sem o 9º dígito (ou com).

    Se já existe um contato com a outra grafia (ex.: importado da lista de clientes), unifica.
    """
    if obter_contato(telefone) or not telefone.startswith("55"):
        return telefone
    ddd, resto = telefone[2:4], telefone[4:]
    if len(resto) == 8:
        alternativo = f"55{ddd}9{resto}"
    elif len(resto) == 9 and resto.startswith("9"):
        alternativo = f"55{ddd}{resto[1:]}"
    else:
        return telefone
    if obter_contato(alternativo):
        with conectar() as con:
            for tabela in ("contatos", "historico", "conversa", "agendamentos", "avisos"):
                con.execute(f"UPDATE {tabela} SET telefone = ? WHERE telefone = ?", (telefone, alternativo))
    return telefone


def obter_meta(chave: str) -> str | None:
    with conectar() as con:
        linha = con.execute("SELECT valor FROM meta WHERE chave = ?", (chave,)).fetchone()
    return linha["valor"] if linha else None


def definir_meta(chave: str, valor: str):
    with conectar() as con:
        con.execute("INSERT INTO meta (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                    (chave, valor))
