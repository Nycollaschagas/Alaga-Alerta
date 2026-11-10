# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Nycollas Kaua Pereira Chagas
# Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"""Validação de toda entrada (allowlist). Retorna (dados_limpos, erros)."""
import re

from . import config

STATUS_VALIDOS = ("ativa", "resolvida")
CAMPOS_CRIACAO = {"bairro", "referencia", "nivel", "descricao"}
CAMPOS_ATUALIZACAO = CAMPOS_CRIACAO | {"status"}

_RE_REFERENCIA = re.compile(r"^[\w .,\-/ºª'()]+$", re.UNICODE)
_RE_DESCRICAO = re.compile(r"^[^\x00-\x1f\x7f<>]*$")


def validar_ocorrencia(payload, parcial=False):
    """Valida o corpo de POST (parcial=False) ou PUT (parcial=True)."""
    if not isinstance(payload, dict):
        return {}, {"corpo": "Envie um objeto JSON."}

    erros, dados = {}, {}
    permitidos = CAMPOS_ATUALIZACAO if parcial else CAMPOS_CRIACAO
    if set(payload) - permitidos:
        erros["campos"] = "A requisição contém campos não permitidos."
    if parcial and not (set(payload) & permitidos):
        erros["corpo"] = "Informe ao menos um campo para atualizar."
    if not parcial:
        for campo in ("bairro", "referencia", "nivel"):
            if campo not in payload:
                erros[campo] = "Campo obrigatório."

    if "bairro" in payload:
        v = payload["bairro"]
        if isinstance(v, str) and v in config.BAIRROS:
            dados["bairro"] = v
        else:
            erros["bairro"] = "Bairro inválido. Consulte GET /api/bairros."

    if "referencia" in payload:
        v = payload["referencia"]
        v = v.strip() if isinstance(v, str) else v
        if isinstance(v, str) and 3 <= len(v) <= 120 and _RE_REFERENCIA.match(v):
            dados["referencia"] = v
        else:
            erros["referencia"] = "Use de 3 a 120 caracteres (letras, números, espaço e . , - / ( ) ' )."

    if "nivel" in payload:
        v = payload["nivel"]
        if isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 4:
            dados["nivel"] = v
        else:
            erros["nivel"] = "Nível deve ser um inteiro de 1 a 4."

    if "descricao" in payload:
        v = payload["descricao"]
        if v is None or (isinstance(v, str) and v.strip() == ""):
            dados["descricao"] = None
        elif isinstance(v, str) and len(v.strip()) <= 280 and _RE_DESCRICAO.match(v.strip()):
            dados["descricao"] = v.strip()
        else:
            erros["descricao"] = "Até 280 caracteres, sem os símbolos < e >."

    if "status" in payload:
        if payload["status"] in STATUS_VALIDOS:
            dados["status"] = payload["status"]
        else:
            erros["status"] = "Status deve ser 'ativa' ou 'resolvida'."

    return dados, erros


def validar_consulta(args):
    """Valida os parâmetros de GET /api/ocorrencias (?bairro=&status=&limit=&offset=)."""
    erros, filtros = {}, {"bairro": None, "status": None, "limit": 50, "offset": 0}

    bairro = args.get("bairro")
    if bairro is not None:
        if bairro in config.BAIRROS:
            filtros["bairro"] = bairro
        else:
            erros["bairro"] = "Bairro inválido."

    status = args.get("status")
    if status is not None:
        if status in STATUS_VALIDOS:
            filtros["status"] = status
        else:
            erros["status"] = "Status inválido."

    for nome, minimo, maximo in (("limit", 1, 100), ("offset", 0, 100000)):
        bruto = args.get(nome)
        if bruto is None:
            continue
        if bruto.isdigit() and minimo <= int(bruto) <= maximo:
            filtros[nome] = int(bruto)
        else:
            erros[nome] = f"Deve ser um inteiro entre {minimo} e {maximo}."

    return filtros, erros
