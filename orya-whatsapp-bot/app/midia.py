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


async def enviar(telefone: str, proc: str):
    """Envia a foto pelo WhatsApp, reaproveitando o upload enquanto ele vale."""
    f = arquivo(proc)
    if not f:
        return
    cache = json.loads(db.obter_meta(f"media_id:{proc}") or "{}")
    if not cache.get("id") or time.time() - cache.get("em", 0) > VALIDADE_MEDIA_ID:
        mime = "image/png" if f.suffix == ".png" else "image/jpeg"
        media_id = await whatsapp.subir_midia(f.read_bytes(), mime, f.name)
        cache = {"id": media_id, "em": time.time()}
        db.definir_meta(f"media_id:{proc}", json.dumps(cache))
    await whatsapp.enviar_imagem(telefone, cache["id"], config.LEGENDA_ANTES_DEPOIS)
