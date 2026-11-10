# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Nycollas Kaua Pereira Chagas
# Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"""Endpoints da API REST."""
from functools import wraps

from flask import Blueprint, current_app, jsonify, request

from . import config, db, validators, weather
from .logger import registrar
from .security import token_valido

bp = Blueprint("api", __name__, url_prefix="/api")


def erro(mensagem, status, detalhes=None):
    corpo = {"erro": mensagem}
    if detalhes:
        corpo["detalhes"] = detalhes
    return jsonify(corpo), status


def exige_admin(func):
    """PUT e DELETE exigem o cabeçalho X-Admin-Token (moderação)."""

    @wraps(func)
    def interno(*args, **kwargs):
        if not token_valido(request.headers.get("X-Admin-Token", ""), config.env("ADMIN_TOKEN")):
            registrar("autorizacao", "negada", rota=request.path, metodo=request.method)
            return erro("Não autorizado.", 401)
        return func(*args, **kwargs)

    return interno


@bp.get("/bairros")
def listar_bairros():
    return jsonify({"dados": sorted(config.BAIRROS)}), 200


@bp.get("/risco")
def risco_chuva():
    """Fonte externa (Open-Meteo): chuva prevista nas próximas 6 h para um bairro."""
    bairro = request.args.get("bairro", "")
    if bairro not in config.BAIRROS:
        return erro("Bairro inválido. Consulte GET /api/bairros.", 400)
    try:
        return jsonify(weather.obter_previsao(bairro)), 200
    except weather.ClimaIndisponivel:
        return erro("Previsão indisponível no momento. Tente novamente em instantes.", 503)


@bp.get("/ocorrencias")
def listar():
    filtros, erros = validators.validar_consulta(request.args)
    if erros:
        registrar("listar_ocorrencias", "falha_validacao")
        return erro("Parâmetros inválidos.", 400, erros)
    itens = db.listar_ocorrencias(**filtros)
    registrar("listar_ocorrencias", "sucesso", quantidade=len(itens))
    return jsonify({"dados": itens}), 200


@bp.get("/ocorrencias/<int:oc_id>")
def obter(oc_id):
    item = db.obter_ocorrencia(oc_id)
    if item is None:
        registrar("obter_ocorrencia", "nao_encontrada", id=oc_id)
        return erro("Ocorrência não encontrada.", 404)
    registrar("obter_ocorrencia", "sucesso", id=oc_id)
    return jsonify(item), 200


@bp.post("/ocorrencias")
def criar():
    if not current_app.extensions["limitador_post"].permitido(request.remote_addr or "desconhecido"):
        registrar("criar_ocorrencia", "limite_excedido")
        return erro("Muitas requisições. Aguarde um minuto.", 429)
    corpo = request.get_json(silent=True)
    if corpo is None:
        registrar("criar_ocorrencia", "falha_validacao", motivo="json_invalido")
        return erro("Envie um corpo JSON válido (Content-Type: application/json).", 400)
    dados, erros = validators.validar_ocorrencia(corpo)
    if erros:
        registrar("criar_ocorrencia", "falha_validacao", campos=",".join(erros))
        return erro("Dados inválidos.", 400, erros)
    item = db.criar_ocorrencia(dados, origem="cidadao")
    registrar("criar_ocorrencia", "sucesso", id=item["id"], bairro=item["bairro"])
    resposta = jsonify(item)
    resposta.status_code = 201
    resposta.headers["Location"] = f"/api/ocorrencias/{item['id']}"
    return resposta


@bp.put("/ocorrencias/<int:oc_id>")
@exige_admin
def atualizar(oc_id):
    corpo = request.get_json(silent=True)
    if corpo is None:
        registrar("atualizar_ocorrencia", "falha_validacao", id=oc_id, motivo="json_invalido")
        return erro("Envie um corpo JSON válido (Content-Type: application/json).", 400)
    campos, erros = validators.validar_ocorrencia(corpo, parcial=True)
    if erros:
        registrar("atualizar_ocorrencia", "falha_validacao", id=oc_id, campos=",".join(erros))
        return erro("Dados inválidos.", 400, erros)
    item = db.atualizar_ocorrencia(oc_id, campos)
    if item is None:
        registrar("atualizar_ocorrencia", "nao_encontrada", id=oc_id)
        return erro("Ocorrência não encontrada.", 404)
    registrar("atualizar_ocorrencia", "sucesso", id=oc_id, campos=",".join(campos))
    return jsonify(item), 200


@bp.delete("/ocorrencias/<int:oc_id>")
@exige_admin
def remover(oc_id):
    if not db.remover_ocorrencia(oc_id):
        registrar("remover_ocorrencia", "nao_encontrada", id=oc_id)
        return erro("Ocorrência não encontrada.", 404)
    registrar("remover_ocorrencia", "sucesso", id=oc_id)
    return "", 204
