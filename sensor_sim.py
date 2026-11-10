# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Nycollas Kaua Pereira Chagas
# Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"""Simulador de sensor: envia leituras fictícias ao listener UDP.

Uso: python sensor_sim.py [bairro] [nivel 1-4]
"""
import json
import socket
import sys

from app import config

bairro = sys.argv[1] if len(sys.argv) > 1 else "Pinheiros"
nivel = int(sys.argv[2]) if len(sys.argv) > 2 else 3

leitura = {
    "token": config.env("SENSOR_TOKEN", ""),
    "bairro": bairro,
    "referencia": "Sensor simulado S01",
    "nivel": nivel,
}
destino = (config.env("UDP_HOST", "127.0.0.1"), int(config.env("UDP_PORT", "9999")))
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.sendto(json.dumps(leitura).encode("utf-8"), destino)
print(f"Leitura enviada para {destino[0]}:{destino[1]} (bairro={bairro}, nivel={nivel})")
