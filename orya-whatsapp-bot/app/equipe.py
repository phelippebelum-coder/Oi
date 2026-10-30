"""Avisos para a equipe: painel + WhatsApp dos números em EQUIPE_WHATSAPP."""

import logging

from . import config, db, relatorio, whatsapp

log = logging.getLogger("orya.equipe")


CAMPANHAS = {"ADS LAVIEEN": ("lavieen", "lavien", "laser"), "ADS BOTOX": ("botox", "toxina", "botulínica")}


def listas(contato: dict) -> list[str]:
    """Listas do WhatsApp Business em que a equipe deve colocar a cliente (a API não marca sozinha)."""
    if not contato:
        return []
    saida = ["LEAD NOVO"] if contato.get("tipo") != "cliente" else []
    ref = contato.get("referral") or {}
    if ref or contato.get("origem") == "anuncio":
        ficha = contato.get("ficha") or {}
        texto = " ".join([ref.get("headline") or "", ref.get("body") or "", ficha.get("queixa") or "",
                          " ".join(ficha.get("interesses") or [])]).lower()
        saida += [lista for lista, chaves in CAMPANHAS.items() if any(k in texto for k in chaves)]
    return saida


async def notificar(telefone: str | None, tipo: str, texto: str):
    db.criar_aviso(telefone, tipo, texto)
    contato = db.obter_contato(telefone) if telefone else None
    if contato and contato["canal"] == "teste":
        return  # conversa da página de teste: só registra no painel
    if nomes := listas(contato):
        texto += "\n📋 Listas no WhatsApp: " + " + ".join(nomes)
    await relatorio.aviso_imediato(tipo, texto)
    if not whatsapp.configurado():
        return
    for numero in config.EQUIPE_WHATSAPP:
        try:
            await whatsapp.enviar_texto(numero, texto)
        except Exception:
            # Fora da janela de 24 h o WhatsApp só aceita template aprovado.
            if config.TEMPLATE_AVISO_EQUIPE:
                try:
                    # Parâmetro de template não aceita quebra de linha.
                    linha = " | ".join(p.strip() for p in texto.splitlines() if p.strip())
                    await whatsapp.enviar_template(numero, config.TEMPLATE_AVISO_EQUIPE, [linha[:900]])
                    continue
                except Exception:
                    pass
            log.warning("Não consegui avisar %s; o aviso ficou no painel", numero)
