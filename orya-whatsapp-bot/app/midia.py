"""Fotos de antes e depois por procedimento (enviadas pelo bot como referência)."""

import json
import time
from pathlib import Path

from . import config, db, whatsapp

PROCEDIMENTOS = {
    "botox": "Botox",
    "harmonizacao_facial": "Harmonização facial",
    "labial": "Preenchimento labial",
    "harmonizacao_glutea": "Harmonização glútea",
}
TIPOS = {"image/jpeg": "jpg", "image/png": "png"}  # formatos aceitos pelo WhatsApp
VALIDADE_MEDIA_ID = 25 * 24 * 3600  # o WhatsApp guarda a mídia por 30 dias


def pasta() -> Path:
    p = config.DATA_DIR / "antes_depois"
    p.mkdir(parents=True, exist_ok=True)
    return p


def arquivo(proc: str) -> Path | None:
    for ext in TIPOS.values():
        f = pasta() / f"{proc}.{ext}"
        if f.exists():
            return f
    return None


def apresentacao() -> Path | None:
    """PDF de apresentação: o enviado pelo painel tem prioridade sobre o padrão do repositório."""
    personalizado = config.DATA_DIR / "apresentacao.pdf"
    if personalizado.exists():
        return personalizado
    padrao = config.BASE_DIR / "materiais" / "apresentacao_orya.pdf"
    return padrao if padrao.exists() else None


def salvar_apresentacao(dados: bytes):
    if not dados.startswith(b"%PDF") or len(dados) > 15_000_000:
        raise ValueError("envie um PDF de até 15 MB")
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    (config.DATA_DIR / "apresentacao.pdf").write_bytes(dados)
    db.definir_meta("media_id:apresentacao", "")


def disponiveis() -> list[str]:
    return [p for p in PROCEDIMENTOS if arquivo(p)]


def salvar(proc: str, dados: bytes, mime: str):
    if proc not in PROCEDIMENTOS or mime not in TIPOS:
        raise ValueError("procedimento ou formato inválido (use JPG ou PNG)")
    if len(dados) > 5_000_000:
        raise ValueError("imagem maior que 5 MB")
    for ext in TIPOS.values():
        (pasta() / f"{proc}.{ext}").unlink(missing_ok=True)
    (pasta() / f"{proc}.{TIPOS[mime]}").write_bytes(dados)
    db.definir_meta(f"media_id:{proc}", "")


def remover(proc: str):
    for ext in TIPOS.values():
        (pasta() / f"{proc}.{ext}").unlink(missing_ok=True)
    db.definir_meta(f"media_id:{proc}", "")


async def _media_id(chave: str, f: Path, mime: str) -> str:
    """Sobe o arquivo para o WhatsApp uma vez e reaproveita o id enquanto ele vale."""
    cache = json.loads(db.obter_meta(f"media_id:{chave}") or "{}")
    if not cache.get("id") or time.time() - cache.get("em", 0) > VALIDADE_MEDIA_ID:
        cache = {"id": await whatsapp.subir_midia(f.read_bytes(), mime, f.name), "em": time.time()}
        db.definir_meta(f"media_id:{chave}", json.dumps(cache))
    return cache["id"]


async def enviar(telefone: str, proc: str):
    """Envia a foto de antes e depois (ou o PDF de apresentação) pelo WhatsApp."""
    if proc == "apresentacao":
        f = apresentacao()
        if f:
            mid = await _media_id("apresentacao", f, "application/pdf")
            await whatsapp.enviar_documento(telefone, mid, "ORYA - Como funciona.pdf")
        return
    f = arquivo(proc)
    if not f:
        return
    mid = await _media_id(proc, f, "image/png" if f.suffix == ".png" else "image/jpeg")
    await whatsapp.enviar_imagem(telefone, mid, config.LEGENDA_ANTES_DEPOIS)
