# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Nycollas Kaua Pereira Chagas
# Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"""Utilidades de segurança: comparação de tokens em tempo constante e limitador de taxa."""
import hmac
import threading
import time
from collections import defaultdict, deque


def token_valido(recebido, esperado):
    """Compara tokens em tempo constante (evita ataques de temporização)."""
    if not isinstance(recebido, str) or not isinstance(esperado, str) or not esperado:
        return False
    return hmac.compare_digest(recebido.encode("utf-8"), esperado.encode("utf-8"))


class LimitadorTaxa:
    """Janela deslizante em memória: no máximo `maximo` eventos a cada `janela` segundos por chave."""

    def __init__(self, maximo, janela=60):
        self.maximo = maximo
        self.janela = janela
        self._historico = defaultdict(deque)
        self._trava = threading.Lock()

    def permitido(self, chave):
        agora = time.monotonic()
        with self._trava:
            fila = self._historico[chave]
            while fila and agora - fila[0] > self.janela:
                fila.popleft()
            if len(fila) >= self.maximo:
                return False
            fila.append(agora)
            return True
