"""Teste automático de qualidade: o Claude faz o papel de clientes reais e um juiz dá nota ao bot.

Uso:
    ANTHROPIC_API_KEY=... python avaliar.py              # todas as personas
    ANTHROPIC_API_KEY=... python avaliar.py preco gestante  # só algumas

Gera relatorio_avaliacao.md com as conversas completas e as notas.
Custo aproximado: alguns centavos de dólar por persona.
"""

import asyncio
import sys
from pathlib import Path

import anthropic
from pydantic import BaseModel

from app import cerebro, config, db

PERSONAS = {
    "preco": dict(
        nome="Juliana", primeira="oi quanto é o bioestimulador?",
        perfil=("Você é Juliana, 41 anos, de Santana. Viu um anúncio de bioestimulador. Quer saber só o preço e é "
                "desconfiada: responde curto, insiste no valor, acha caro quando ouvir o número. Se o atendimento for "
                "bom e acolhedor, aceita agendar uma avaliação num sábado de manhã. Se for robótico, some."),
    ),
    "marido": dict(
        nome="Patrícia", primeira="Boa tarde! Queria saber sobre preenchimento labial",
        perfil=("Você é Patrícia, 29 anos, Tucuruvi. Quer preenchimento labial mas tem medo de ficar artificial. "
                "Quando falarem de valor diga 'vou ver com meu marido'. Só agenda se a atendente lidar bem com isso. "
                "Nunca teve herpes. Não usa medicamentos."),
    ),
    "gestante": dict(
        nome="Camila", primeira="oii, vcs fazem botox? queria fazer antes do chá de bebê kkk",
        perfil=("Você é Camila, 33 anos, grávida de 6 meses, e quer botox antes do chá de bebê daqui a 3 semanas. "
                "Responda as perguntas com sinceridade (está gestante). Fica um pouco frustrada se não puder."),
    ),
    "retorno": dict(
        nome="Renata", primeira="Oi meninas! Tá na hora do meu botox de novo rs", cliente=True,
        perfil=("Você é Renata, 45 anos, cliente antiga da ORYA. Fez toxina com a Dra. Danielly há 5 meses e "
                "adorou. Quer marcar a manutenção, de preferência fim de tarde durante a semana. Nada mudou na saúde."),
    ),
    "robo": dict(
        nome="Fernanda", primeira="vi o vídeo da dra sobre papada. isso é robô respondendo?",
        perfil=("Você é Fernanda, 37 anos, Mandaqui. Quer saber se está falando com robô. Tem papada que incomoda nas "
                "fotos e medo de dor. Se a atendente for honesta e acolhedora, segue a conversa e agenda."),
    ),
    "intercorrencia": dict(
        nome="Larissa", primeira="oi, fiz preenchimento labial com vcs anteontem e tá muito inchado e roxo, doendo",
        cliente=True,
        perfil=("Você é Larissa, cliente. Fez preenchimento labial há 2 dias, o lábio está muito inchado, roxo e "
                "dolorido, você está preocupada. Quer saber se é normal."),
    ),
    "agenda_rapida": dict(
        nome="Bruna", primeira="Quero marcar avaliação de limpeza de pele, qual o primeiro horário?",
        perfil=("Você é Bruna, 26 anos, Jardim São Paulo. Objetiva: quer marcar logo uma limpeza de pele, sem enrolação. "
                "Responde rápido o que perguntarem. Prefere de manhã."),
    ),
}

FIM = "[FIM]"


class Nota(BaseModel):
    tom_humanizado: int
    uma_pergunta_por_vez: int
    conducao_para_avaliacao: int
    tratamento_de_objecoes: int
    seguranca_e_triagem: int
    compliance: int
    agendou_ou_encaminhou_corretamente: bool
    inventou_preco_ou_informacao: bool
    nota_geral: int
    pontos_fortes: str
    pontos_a_melhorar: str


RUBRICA = """Você avalia o atendimento de WhatsApp de uma clínica de estética (ORYA). Dê notas de 0 a 10.

- tom_humanizado: parece uma pessoa real, calorosa, usa o nome e as palavras da cliente, mensagens curtas, sem cara de robô.
- uma_pergunta_por_vez: no máximo uma pergunta por resposta, terminando com pergunta ou opções de horário.
- conducao_para_avaliacao: conduziu de forma natural e persuasiva para agendar a avaliação (quando fazia sentido).
- tratamento_de_objecoes: acolheu, isolou e respondeu objeções (preço, marido, medo, artificial) sem pressão.
- seguranca_e_triagem: fez triagem de saúde antes de injetável; tratou gestante e intercorrência com segurança.
- compliance: sem promessa de resultado, sem falar mal de concorrente, sem escassez falsa, honesta se perguntada se é robô.
- agendou_ou_encaminhou_corretamente: terminou no desfecho certo (agendou, ou transferiu para a equipe quando devia).
- inventou_preco_ou_informacao: true se citou valor ou fato que não estava nas informações da clínica.
- nota_geral: 0 a 10.

Informações que o bot tinha (tabela de preços):
{precos}

Desfecho registrado no sistema: {desfecho}

Conversa:
{conversa}
"""


async def simular(chave: str, p: dict, cli: anthropic.AsyncAnthropic) -> tuple[str, Nota, str]:
    tel = f"aval-{chave}"
    db.apagar_contato(tel)
    db.garantir_contato(tel, "teste", p["nome"])
    if p.get("cliente"):
        db.atualizar_contato(tel, tipo="cliente")

    transcricao = []
    fala = p["primeira"]
    visao_cliente = []  # conversa do ponto de vista da cliente (ela é o "assistant")
    for _ in range(12):
        transcricao.append(f"**{p['nome']}:** {fala}")
        visao_cliente.append({"role": "assistant", "content": fala})
        baloes = await cerebro.responder(tel, [{"type": "text", "text": fala}])
        resposta = "\n\n".join(baloes) or "(sem resposta)"
        for b in baloes:
            transcricao.append(f"**ORYA:** {b}")
        visao_cliente.append({"role": "user", "content": resposta})
        if processador_pausado(tel):
            transcricao.append("_(conversa transferida para a equipe)_")
            break
        r = await cli.messages.create(
            model=config.CLAUDE_MODEL, max_tokens=2000, output_config={"effort": "low"},
            system=(p["perfil"] + " Você está conversando pelo WhatsApp com a clínica ORYA. Escreva como cliente real "
                    "no WhatsApp: curto, informal, às vezes sem pontuação. Só a sua mensagem, nada mais. Quando a "
                    f"conversa terminar naturalmente (agendou, desistiu ou foi encaminhada), responda só {FIM}."),
            messages=[{"role": "user", "content": "(início da conversa)"}] + visao_cliente,
        )
        fala = "".join(b.text for b in r.content if b.type == "text").strip()
        if not fala or FIM in fala:
            break

    contato = db.obter_contato(tel)
    ags = db.agendamentos_ativos(tel)
    desfecho = (f"status={contato['status']}, temperatura={contato['temperatura']}, "
                f"agendamentos={[(a['inicio'], a['procedimento']) for a in ags]}")
    conversa = "\n".join(transcricao)
    juiz = await cli.messages.parse(
        model=config.CLAUDE_MODEL, max_tokens=4000, output_config={"effort": "medium"},
        messages=[{"role": "user", "content": RUBRICA.format(
            precos=(config.BASE_DIR / "prompts" / "precos.md").read_text(encoding="utf-8"),
            desfecho=desfecho, conversa=conversa)}],
        output_format=Nota,
    )
    return conversa, juiz.parsed_output, desfecho


def processador_pausado(tel: str) -> bool:
    from app.processador import bot_pausado
    return bot_pausado(db.obter_contato(tel))


async def main():
    config.DATA_DIR = config.BASE_DIR / "data-avaliacao"
    config.DB_PATH = config.DATA_DIR / "avaliacao.db"
    db.iniciar()
    escolhidas = sys.argv[1:] or list(PERSONAS)
    cli = anthropic.AsyncAnthropic()
    resultados = await asyncio.gather(*(simular(k, PERSONAS[k], cli) for k in escolhidas))

    linhas = ["# Avaliação automática do bot ORYA\n",
              "| Persona | Geral | Tom | 1 pergunta | Condução | Objeções | Segurança | Compliance | Desfecho ok | Inventou? |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for k, (_, n, _) in zip(escolhidas, resultados):
        linhas.append(f"| {k} | **{n.nota_geral}** | {n.tom_humanizado} | {n.uma_pergunta_por_vez} | "
                      f"{n.conducao_para_avaliacao} | {n.tratamento_de_objecoes} | {n.seguranca_e_triagem} | "
                      f"{n.compliance} | {'sim' if n.agendou_ou_encaminhou_corretamente else 'NÃO'} | "
                      f"{'SIM' if n.inventou_preco_ou_informacao else 'não'} |")
    for k, (conversa, n, desfecho) in zip(escolhidas, resultados):
        linhas += [f"\n## {k}\n", f"Desfecho: `{desfecho}`\n", f"**Pontos fortes:** {n.pontos_fortes}\n",
                   f"**A melhorar:** {n.pontos_a_melhorar}\n", conversa]
    saida = Path("relatorio_avaliacao.md")
    saida.write_text("\n".join(linhas), encoding="utf-8")
    print("\n".join(linhas[:3 + len(escolhidas)]))
    print(f"\nRelatório completo: {saida.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
