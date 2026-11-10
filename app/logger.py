# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Nycollas Kaua Pereira Chagas
# Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"""Log em arquivo: data/hora, ação e resultado. Nunca registra corpo de requisição, tokens ou IPs."""
import logging
import os
import re
from logging.handlers import RotatingFileHandler

from . import config


def get_logger():
    lg = logging.getLogger("alagaalerta")
    if lg.handlers:
        return lg
    caminho = config.env("LOG_FILE", "logs/alagaalerta.log")
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    handler = RotatingFileHandler(caminho, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"))
    lg.setLevel(logging.INFO)
    lg.addHandler(handler)
    lg.propagate = False
    return lg


def _limpar(valor):
    """Remove quebras de linha/controles (evita log injection) e limita o tamanho."""
    texto = re.sub(r"\s+", "_", str(valor))
    texto = re.sub(r"[^\x20-\x7eà-ÿÀ-ß]", "?", texto)
    return texto[:100]


def registrar(acao, resultado, nivel=logging.INFO, **extra):
    """Escreve uma linha: 2026-11-09 14:03:11 | INFO | acao=... resultado=... chave=valor"""
    campos = " ".join(f"{k}={_limpar(v)}" for k, v in extra.items())
    get_logger().log(nivel, f"acao={acao} resultado={resultado} {campos}".strip())
