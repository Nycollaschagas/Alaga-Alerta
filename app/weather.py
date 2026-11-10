# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Nycollas Kaua Pereira Chagas
# Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"""Fonte externa de dados: previsão horária de chuva da API aberta Open-Meteo (requests + JSON)."""
import time
from datetime import datetime

import requests

from . import config
from .logger import registrar

URL = "https://api.open-meteo.com/v1/forecast"
JANELA_HORAS = 6
CACHE_SEGUNDOS = 600
_cache = {}


class ClimaIndisponivel(Exception):
    """A fonte externa falhou ou devolveu dados inesperados."""


def classificar(mm):
    """Heurística do protótipo (limiares didáticos, não oficiais) sobre a chuva acumulada em 6 h."""
    if mm < 10:
        return "baixo"
    if mm < 25:
        return "moderado"
    if mm < 50:
        return "alto"
    return "muito alto"


def obter_previsao(bairro):
    """Consulta a chuva prevista (mm) nas próximas 6 horas para um bairro da lista fixa."""
    agora = time.monotonic()
    item = _cache.get(bairro)
    if item and agora - item[0] < CACHE_SEGUNDOS:
        return item[1]

    latitude, longitude = config.BAIRROS[bairro]
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "precipitation",
        "forecast_hours": JANELA_HORAS,
        "timezone": "America/Sao_Paulo",
    }
    try:
        resposta = requests.get(URL, params=params, timeout=5)
        resposta.raise_for_status()
        valores = resposta.json()["hourly"]["precipitation"]
        numeros = [v for v in valores if isinstance(v, (int, float))]
        if not numeros:
            raise ValueError("sem dados de precipitação")
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        registrar("consulta_open_meteo", "falha", bairro=bairro, tipo_erro=type(exc).__name__)
        raise ClimaIndisponivel() from exc

    total = round(sum(numeros), 1)
    resultado = {
        "bairro": bairro,
        "janela_horas": JANELA_HORAS,
        "chuva_prevista_mm": total,
        "nivel_risco": classificar(total),
        "fonte": "Open-Meteo",
        "consultado_em": datetime.now().isoformat(timespec="seconds"),
    }
    _cache[bairro] = (agora, resultado)
    registrar("consulta_open_meteo", "sucesso", bairro=bairro, mm=total)
    return resultado
