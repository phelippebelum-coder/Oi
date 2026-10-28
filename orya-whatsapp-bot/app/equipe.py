"""Avisos para a equipe: painel + WhatsApp dos números em EQUIPE_WHATSAPP."""

import logging

from . import config, db, relatorio, whatsapp

log = logging.getLogger("orya.equipe")


async def notificar(telefone: str | None, tipo: str, texto: str):
    db.criar_aviso(telefone, tipo, texto)
    contato = db.obter_contato(telefone) if telefone else None
    if contato and contato["canal"] == "teste":
        return  # conversa da página de teste: só registra no painel
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
                    await whatsapp.enviar_template(numero, config.TEMPLATE_AVISO_EQUIPE, [texto[:900]])
                    continue
                except Exception:
                    pass
            log.warning("Não consegui avisar %s; o aviso ficou no painel", numero)
