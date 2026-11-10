# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Nycollas Kaua Pereira Chagas
# Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"""AlagaAlerta: alertas comunitários de alagamento (Flask)."""
import logging
import os

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from . import config
from .logger import registrar
from .routes import bp
from .security import LimitadorTaxa

MENSAGENS_HTTP = {
    400: "Requisição inválida.",
    404: "Recurso não encontrado.",
    405: "Método não permitido.",
    413: "Corpo da requisição grande demais.",
    415: "Tipo de conteúdo não suportado.",
}

CSP = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'"


def create_app():
    config.validar_ambiente()
    pasta_static = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
    app = Flask(__name__, static_folder=pasta_static, static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024  # 8 KB: nenhum corpo legítimo é maior
    app.json.ensure_ascii = False
    app.extensions["limitador_post"] = LimitadorTaxa(int(config.env("RATE_LIMIT_POST_POR_MIN", "10")), 60)
    app.register_blueprint(bp)

    @app.get("/")
    def index():
        return send_from_directory(pasta_static, "index.html")

    @app.after_request
    def cabecalhos_seguranca(resposta):
        resposta.headers["Content-Security-Policy"] = CSP
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        if request.path.startswith("/api/"):
            resposta.headers["Cache-Control"] = "no-store"
        return resposta

    @app.errorhandler(Exception)
    def tratar_erro(exc):
        if isinstance(exc, HTTPException):
            codigo = exc.code or 500
            return jsonify({"erro": MENSAGENS_HTTP.get(codigo, "Erro na requisição.")}), codigo
        # Detalhes técnicos vão só para o log; o cliente recebe mensagem genérica.
        registrar("erro_interno", "falha", nivel=logging.ERROR, tipo_erro=type(exc).__name__, rota=request.path)
        return jsonify({"erro": "Erro interno. Tente novamente mais tarde."}), 500

    return app
