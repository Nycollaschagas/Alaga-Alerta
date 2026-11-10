# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Nycollas Kaua Pereira Chagas
# Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"""Ponto de entrada: python run.py"""
from app import config, create_app

app = create_app()

if __name__ == "__main__":
    # debug=False de propósito: o modo debug do Flask expõe um console interativo.
    app.run(host=config.env("FLASK_HOST", "127.0.0.1"), port=int(config.env("FLASK_PORT", "5000")), debug=False)
