# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Nycollas Kaua Pereira Chagas
# Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"""Módulo de sockets UDP: recebe leituras de sensores de nível de água.

UDP foi escolhido porque o datagrama é pequeno e não exige conexão, o que combina com
sensores baratos e redes instáveis. Formato (JSON, até 512 bytes):
  {"token": "...", "bairro": "Pinheiros", "referencia": "Sensor S01", "nivel": 3}
Execute: python -m app.udp_listener
"""
import json
import socket
import threading

from . import config, db, validators
from .logger import registrar
from .security import token_valido

TAMANHO_MAX = 512


def processar_datagrama(dados):
    """Valida e grava uma leitura. Devolve uma string descrevendo o resultado (usada no log e nos testes)."""
    if len(dados) > TAMANHO_MAX:
        registrar("udp_leitura", "rejeitada", motivo="tamanho")
        return "tamanho"
    try:
        mensagem = json.loads(dados.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        registrar("udp_leitura", "rejeitada", motivo="malformada")
        return "malformada"
    if not isinstance(mensagem, dict):
        registrar("udp_leitura", "rejeitada", motivo="malformada")
        return "malformada"

    token = mensagem.pop("token", None)
    if not token_valido(token, config.env("SENSOR_TOKEN")):
        registrar("udp_leitura", "rejeitada", motivo="token")
        return "token"

    campos, erros = validators.validar_ocorrencia(mensagem)
    if erros:
        registrar("udp_leitura", "rejeitada", motivo="validacao", campos=",".join(erros))
        return "validacao"

    try:
        ocorrencia, criada = db.registrar_leitura_sensor(campos)
    except Exception as exc:  # o listener nunca deve cair por causa de uma leitura
        registrar("udp_leitura", "falha", motivo="banco", tipo_erro=type(exc).__name__)
        return "erro"
    resultado = "criada" if criada else "atualizada"
    registrar("udp_leitura", resultado, id=ocorrencia["id"], bairro=ocorrencia["bairro"])
    return resultado


def criar_socket(host, porta):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, porta))
    sock.settimeout(1.0)
    return sock


def servir(sock, parar):
    """Laço principal; encerra quando o evento `parar` é sinalizado."""
    while not parar.is_set():
        try:
            dados, _origem = sock.recvfrom(TAMANHO_MAX + 1)
        except socket.timeout:
            continue
        except OSError:
            break
        processar_datagrama(dados)


def main():
    config.validar_ambiente()
    host = config.env("UDP_HOST", "127.0.0.1")
    porta = int(config.env("UDP_PORT", "9999"))
    sock = criar_socket(host, porta)
    parar = threading.Event()
    registrar("udp_listener", "iniciado", host=host, porta=porta)
    print(f"Ouvindo sensores em udp://{host}:{porta} (Ctrl+C para sair)")
    try:
        servir(sock, parar)
    except KeyboardInterrupt:
        pass
    finally:
        parar.set()
        sock.close()
        registrar("udp_listener", "encerrado")


if __name__ == "__main__":
    main()
