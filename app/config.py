# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Nycollas Kaua Pereira Chagas
# Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"""Configuração: lê variáveis do .env e define a lista fixa de bairros."""
import os

from dotenv import load_dotenv

load_dotenv()

# Bairros aceitos pelo sistema (nome -> latitude, longitude aproximadas do centro).
# Lista fixa: evita texto livre no campo "bairro" e permite consultar a previsão do tempo.
BAIRROS = {
    "Campo Limpo": (-23.6489, -46.7567),
    "Freguesia do Ó": (-23.4997, -46.6969),
    "Itaquera": (-23.5365, -46.4570),
    "Mooca": (-23.5596, -46.5997),
    "Penha": (-23.5262, -46.5410),
    "Pinheiros": (-23.5667, -46.7019),
    "Santana": (-23.5018, -46.6285),
    "Santo Amaro": (-23.6549, -46.7090),
    "Sé": (-23.5505, -46.6333),
    "Vila Mariana": (-23.5890, -46.6340),
}

OBRIGATORIAS = ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME", "ADMIN_TOKEN", "SENSOR_TOKEN")


def env(nome, padrao=None):
    """Lê uma variável de ambiente."""
    return os.environ.get(nome, padrao)


def validar_ambiente():
    """Falha na inicialização (e só nela) se faltar configuração ou se um token for fraco."""
    faltando = [n for n in OBRIGATORIAS if not env(n)]
    if faltando:
        raise RuntimeError(
            "Variáveis de ambiente ausentes: " + ", ".join(faltando)
            + ". Copie .env.example para .env e preencha."
        )
    for nome in ("ADMIN_TOKEN", "SENSOR_TOKEN"):
        if len(env(nome)) < 16:
            raise RuntimeError(f"{nome} precisa ter ao menos 16 caracteres (use um valor aleatório).")
