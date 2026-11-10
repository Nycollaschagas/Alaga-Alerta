# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Nycollas Kaua Pereira Chagas
# Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"""Gera docs/relatorio_alagaalerta.pdf (até 3 páginas).  Uso: python docs/gerar_relatorio.py
Requer: pip install reportlab"""
import os

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relatorio_alagaalerta.pdf")

# Se você conversou com um morador/entregador/familiar sobre alagamentos, escreva 1-2 frases aqui
# (sem identificar a pessoa) e rode o script de novo: a frase entra na seção 2 do relatório.
CONVERSA = ""

AZUL, CINZA = colors.HexColor("#083d73"), colors.HexColor("#5b6b78")
corpo = ParagraphStyle("corpo", fontName="Helvetica", fontSize=8.7, leading=11, alignment=TA_JUSTIFY, spaceAfter=3)
h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=AZUL, spaceBefore=5, spaceAfter=2)
titulo = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=AZUL)
sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=8.5, leading=11, textColor=CINZA, spaceAfter=4)
celula = ParagraphStyle("celula", fontName="Helvetica", fontSize=7.8, leading=9.6)
celula_b = ParagraphStyle("celula_b", parent=celula, fontName="Helvetica-Bold")
item = ParagraphStyle("item", parent=corpo, leftIndent=9, bulletIndent=0, spaceAfter=1.5)


def P(texto, estilo=corpo):
    return Paragraph(texto, estilo)


def bullets(linhas):
    return [Paragraph(t, item, bulletText="\u2022") for t in linhas]


def tabela(dados, larguras, cabecalho=True):
    linhas = [[Paragraph(c, celula_b if (cabecalho and i == 0) else celula) for c in l] for i, l in enumerate(dados)]
    t = Table(linhas, colWidths=larguras, repeatRows=1 if cabecalho else 0)
    estilo = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c4ced8")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
              ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if cabecalho:
        estilo.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3ebf4")))
    t.setStyle(TableStyle(estilo))
    return t


def diagrama():
    d = Drawing(17.4 * cm, 4.3 * cm)
    larg, alt = 4.5 * cm, 1.15 * cm
    xs = [0.2 * cm, 6.4 * cm, 12.6 * cm]
    ys = [2.75 * cm, 0.95 * cm]

    def caixa(x, y, linha1, linha2, cor):
        d.add(Rect(x, y, larg, alt, rx=4, ry=4, fillColor=cor, strokeColor=AZUL, strokeWidth=0.8))
        d.add(String(x + larg / 2, y + 0.65 * cm, linha1, textAnchor="middle", fontName="Helvetica-Bold", fontSize=7.6))
        d.add(String(x + larg / 2, y + 0.25 * cm, linha2, textAnchor="middle", fontName="Helvetica", fontSize=6.6, fillColor=CINZA))

    def seta(x1, y1, x2, y2):
        d.add(Line(x1, y1, x2, y2, strokeColor=AZUL, strokeWidth=1))
        import math
        ang = math.atan2(y2 - y1, x2 - x1)
        a, b = 0.17 * cm, 0.08 * cm
        d.add(Polygon([x2, y2, x2 - a * math.cos(ang) + b * math.sin(ang), y2 - a * math.sin(ang) - b * math.cos(ang),
                       x2 - a * math.cos(ang) - b * math.sin(ang), y2 - a * math.sin(ang) + b * math.cos(ang)],
                      fillColor=AZUL, strokeColor=AZUL))

    azul_claro, verde, laranja = colors.HexColor("#e3ebf4"), colors.HexColor("#e5f3e6"), colors.HexColor("#fdf0dc")
    caixa(xs[0], ys[0], "Cidadão (navegador)", "HTML/CSS/JS - fetch()", azul_claro)
    caixa(xs[1], ys[0], "API REST Flask", "validação, token admin, limite de taxa", azul_claro)
    caixa(xs[2], ys[0], "Open-Meteo (externa)", "chuva prevista em 6 h (JSON)", laranja)
    caixa(xs[0], ys[1], "Sensor de nível (UDP)", "datagrama JSON com token", verde)
    caixa(xs[1], ys[1], "Listener UDP", "valida token e dados", verde)
    caixa(xs[2], ys[1], "MySQL: ocorrencias", "SQL parametrizado, sem ORM", azul_claro)
    seta(xs[0] + larg, ys[0] + alt / 2, xs[1], ys[0] + alt / 2)
    seta(xs[1] + larg, ys[0] + alt / 2, xs[2], ys[0] + alt / 2)
    seta(xs[0] + larg, ys[1] + alt / 2, xs[1], ys[1] + alt / 2)
    seta(xs[1] + larg, ys[1] + alt / 2, xs[2], ys[1] + alt / 2)
    seta(xs[1] + larg - 0.4 * cm, ys[0], xs[2] + 0.5 * cm, ys[1] + alt)  # API -> MySQL
    d.add(String(0.2 * cm, 0.25 * cm, "Log em arquivo (data/hora, ação, resultado) gravado pela API e pelo listener; sem dados pessoais.",
                 fontName="Helvetica-Oblique", fontSize=6.8, fillColor=CINZA))
    return d


def montar():
    h = []
    h.append(P("AlagaAlerta: alertas comunitários de alagamento em São Paulo", titulo))
    h.append(P("Global Solution CitizenTech · Coding for Security · FIAP 2026 · Autor: Nycollas Kaua Pereira Chagas", sub))

    h.append(P("1. Problema e cidadão", h1))
    h.append(P("<b>Cidadão afetado:</b> pessoas que moram, trabalham ou circulam perto de áreas de fundo de vale em São Paulo: "
               "pedestres, idosos, estudantes, entregadores, motoristas por aplicativo e pequenos comerciantes. "
               "<b>Problema:</b> em chuvas fortes o alagamento se forma rápido e rua a rua, mas a informação sobre quais pontos estão "
               "intransitáveis circula de forma fragmentada, atrasada e sem padrão (grupos de mensagem, redes sociais). Alertas oficiais "
               "costumam cobrir regiões amplas, não o ponto exato do trajeto. O resultado é gente entrando em vias alagadas, horas perdidas e "
               "risco à vida. A solução combina duas ideias da etapa de Inspiração: <i>previsão de enchentes com alertas direcionados</i> e "
               "<i>zeladoria colaborativa</i>: cidadãos e sensores relatam pontos alagados e o sistema os cruza com a chuva prevista."))

    h.append(P("2. Evidências e hipóteses", h1))
    evid = ["<b>Observação do cenário:</b> alagamentos em vias e córregos são recorrentes nos verões da capital paulista e atingem o deslocamento diário.",
            "<b>Dado público:</b> a previsão horária de precipitação da API aberta Open-Meteo, consumida pelo protótipo, é convertida em "
            "risco por bairro (soma das próximas 6 h)."]
    if CONVERSA.strip():
        evid.append("<b>Conversa:</b> " + CONVERSA.strip())
    evid.append("<b>Hipóteses a validar com usuários:</b> (H1) moradores reportam pontos se o relato for rápido e anônimo; "
                "(H2) previsão somada a relatos reais é mais útil que qualquer um dos dois isolados.")
    h += bullets(evid)

    h.append(P("3. ODS relacionados", h1))
    h.append(tabela([
        ["ODS", "Como a solução contribui"],
        ["<b>11</b> Cidades e comunidades sustentáveis", "Meta 11.5: reduzir mortes, pessoas afetadas e perdas por desastres relacionados à água, com informação por ponto da cidade."],
        ["<b>13</b> Ação contra a mudança global do clima", "Meta 13.1: fortalecer a resiliência a riscos climáticos; eventos extremos de chuva exigem alerta local e rápido."],
        ["<b>9</b> Indústria, inovação e infraestrutura", "Infraestrutura digital resiliente e de baixo custo; sensores simples via UDP funcionam com conectividade limitada."],
    ], [5.3 * cm, 12.1 * cm]))

    h.append(P("4. Arquitetura e modelo de dados", h1))
    h.append(diagrama())
    h.append(P("<b>Tecnologias:</b> Python 3, Flask, MySQL com mysql-connector-python (SQL puro, sem ORM), requests (Open-Meteo), sockets UDP, "
               "HTML/CSS/JS sem frameworks, logging com arquivo rotativo. Código dividido em módulos: <font face='Courier'>routes, db, validators, "
               "weather, security, logger, udp_listener</font>."))
    h.append(tabela([
        ["Endpoint", "Função", "Status"],
        ["GET /api/ocorrencias (e /&lt;id&gt;)", "Lista com filtros ou detalha uma ocorrência", "200, 400, 404"],
        ["POST /api/ocorrencias", "Cria relato do cidadão (limite de taxa)", "201, 400, 413, 429"],
        ["PUT /api/ocorrencias/&lt;id&gt;", "Atualiza nível, descrição ou status (token admin)", "200, 400, 401, 404"],
        ["DELETE /api/ocorrencias/&lt;id&gt;", "Remove ocorrência (token admin)", "204, 401, 404"],
        ["GET /api/risco?bairro=", "Chuva prevista em 6 h e nível de risco (fonte externa)", "200, 400, 503"],
    ], [5.6 * cm, 8.2 * cm, 3.6 * cm]))
    h.append(Spacer(1, 3))
    h.append(tabela([
        ["Tabela ocorrencias", "Tipo", "Observação"],
        ["id", "INT UNSIGNED, PK, auto incremento", "Identificador"],
        ["bairro / referencia", "VARCHAR(40) / VARCHAR(120)", "Bairro de lista fixa; ponto de referência (sem endereço residencial exato)"],
        ["nivel", "TINYINT, CHECK 1 a 4", "1 atenção, 2 via alagada, 3 intransitável, 4 risco grave"],
        ["descricao", "VARCHAR(280), nulo", "Texto livre curto, sem os símbolos &lt; e &gt;"],
        ["status / origem", "ENUM('ativa','resolvida') / ENUM('cidadao','sensor')", "Origem é definida pelo servidor, nunca pelo cliente"],
        ["criado_em / atualizado_em", "DATETIME", "Preenchidos pelo banco; índice por (bairro, status)"],
    ], [4.0 * cm, 6.0 * cm, 7.4 * cm]))

    h.append(P("5. Segurança e privacidade", h1))
    h.append(P("<b>LGPD e coleta mínima:</b> o sistema não grava nome, telefone, e-mail nem IP; o relato descreve um local público, não uma pessoa. "
               "O log registra data/hora, ação e resultado, sem corpo de requisição, tokens ou IPs (e neutraliza quebras de linha para evitar "
               "<i>log injection</i>). Todos os dados do protótipo são fictícios ou abertos. <b>Controles gerais:</b> credenciais em <font face='Courier'>.env</font> "
               "(fora do Git, tokens com mínimo de 16 caracteres), consultas parametrizadas, validação por allowlist de toda entrada, erros genéricos "
               "ao cliente (detalhes só no log), usuário do banco com privilégios mínimos e cabeçalhos de segurança (CSP, nosniff)."))
    h.append(tabela([
        ["Ameaça", "Como ocorreria", "Mitigação implementada"],
        ["<b>1. Injeção (SQL) e XSS armazenado</b>",
         "Texto malicioso em referencia/descricao ou nos filtros da URL alteraria consultas ou executaria script no navegador de outros usuários.",
         "SQL sempre com %s e colunas de UPDATE em allowlist; validação por regex e tamanho (rejeita &lt; &gt;); interface usa textContent (nunca innerHTML) e CSP; testes com payloads."],
        ["<b>2. Abuso e dados falsos</b> (spam, falsificação de sensores, adulteração)",
         "Robô enviando milhares de relatos; pacote UDP forjado criando alertas falsos; terceiro apagando ocorrências.",
         "Limite de taxa no POST (429); corpo máx. 8 KB; PUT/DELETE só com token admin comparado em tempo constante; origem fixada pelo servidor; leitura UDP só com token, até 512 bytes e validada."],
        ["<b>3. Exposição de credenciais e de detalhes internos</b>",
         "Senha do banco no repositório ou mensagem de erro revelando SQL, caminhos ou versões ajudaria um atacante.",
         "Segredos só no .env (.gitignore + .env.example sem valores reais); app recusa iniciar com segredo fraco; handler global devolve erro genérico e grava detalhe no log; debug desligado."],
    ], [3.5 * cm, 6.0 * cm, 7.9 * cm]))

    h.append(P("6. Validação e viabilidade", h1))
    h += bullets([
        "<b>Testes automatizados (33, todos aprovados):</b> CRUD com status corretos; 400 para 11 tipos de entrada inválida; payloads de SQL injection e XSS "
        "rejeitados; 401 sem token; 429 no limite de taxa; 500 sem vazar detalhes; 503 quando a fonte externa falha; log com data/hora, ação e resultado; "
        "camada db.py verificada com conexão simulada (nenhum valor do usuário entra no texto do SQL); socket UDP real em localhost.",
        "<b>Integração real:</b> MySQL e Open-Meteo são exercitados pelo roteiro do README (curl e interface), pois os testes usam banco simulado.",
        "<b>Viabilidade:</b> custo baixo (software livre, Open-Meteo gratuita para uso não comercial, sensor simples com microcontrolador). "
        "Operação natural por parceria com Defesa Civil/prefeituras ou ONGs de bairro; o mesmo modelo escala trocando a lista de bairros.",
    ])

    h.append(P("7. Limitações e próximos passos", h1))
    h += bullets([
        "Hipóteses H1 e H2 ainda não foram testadas com cidadãos; é preciso um piloto de usabilidade em um bairro.",
        "Os limiares de risco (10/25/50 mm em 6 h) são uma heurística didática, não critérios oficiais; devem ser calibrados com dados da Defesa Civil.",
        "Sem autenticação de cidadãos, relatos falsos são possíveis (mitigados por limite de taxa e moderação); falta HTTPS (proxy reverso), "
        "criptografia no UDP (VPN/DTLS), limitador de taxa compartilhado entre processos e expiração automática de relatos antigos.",
        "Lista fixa de 10 bairros com coordenadas aproximadas do centro; ampliar para busca por ponto no mapa.",
    ])

    h.append(P("8. Recursos além do conteúdo visto (bônus) e por que foram usados", h1))
    h.append(P("<b>Limitação de taxa em memória</b> (deque + lock): contém spam sem depender de serviços externos. <b>hmac.compare_digest</b>: compara tokens sem vazar "
               "informação por tempo de resposta. <b>Content-Security-Policy e demais cabeçalhos</b>: segunda barreira contra XSS. <b>unittest.mock</b>: permite testar banco, "
               "API externa e falhas sem infraestrutura. <b>threading.Event no listener UDP</b>: encerramento limpo e teste com socket real. <b>Cache com TTL</b>: respeita a "
               "fonte externa e mantém a página rápida. <b>RotatingFileHandler</b>: impede o log de crescer sem limite."))
    return h


def main():
    doc = SimpleDocTemplate(SAIDA, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.5 * cm, bottomMargin=1.4 * cm,
                            title="AlagaAlerta - Relatório Global Solution CitizenTech", author="Nycollas Kaua Pereira Chagas")
    doc.build(montar())
    print("Gerado:", SAIDA)


if __name__ == "__main__":
    main()
