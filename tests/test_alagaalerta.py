# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Nycollas Kaua Pereira Chagas
# Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"""Testes automatizados. Rodam sem MySQL: o banco é substituído por um objeto em memória,
e a camada db.py é testada à parte com uma conexão falsa que registra as consultas SQL."""
import json
import os
import re
import socket
import tempfile
import threading
import time
import unittest
from datetime import datetime
from unittest import mock

import requests

ADMIN = "token-admin-de-teste-1234567890"
SENSOR = "token-sensor-de-teste-1234567890"
_TMP = tempfile.mkdtemp()
LOG = os.path.join(_TMP, "teste.log")
os.environ.update({
    "DB_HOST": "x", "DB_USER": "x", "DB_PASSWORD": "x", "DB_NAME": "x",
    "ADMIN_TOKEN": ADMIN, "SENSOR_TOKEN": SENSOR, "LOG_FILE": LOG,
})

from app import create_app, db, udp_listener, validators, weather  # noqa: E402


class BancoFalso:
    """Mesma interface de app.db, guardando tudo em memória."""

    def __init__(self):
        self.dados, self.prox = {}, 1

    def _novo(self, dados, origem):
        agora = datetime.now().isoformat(timespec="seconds")
        item = {"id": self.prox, "bairro": dados["bairro"], "referencia": dados["referencia"],
                "nivel": dados["nivel"], "descricao": dados.get("descricao"), "status": "ativa",
                "origem": origem, "criado_em": agora, "atualizado_em": agora}
        self.dados[self.prox] = item
        self.prox += 1
        return dict(item)

    def criar_ocorrencia(self, dados, origem="cidadao"):
        return self._novo(dados, origem)

    def listar_ocorrencias(self, bairro=None, status=None, limit=50, offset=0):
        itens = [i for i in self.dados.values()
                 if (not bairro or i["bairro"] == bairro) and (not status or i["status"] == status)]
        return [dict(i) for i in itens][offset:offset + limit]

    def obter_ocorrencia(self, oc_id):
        return dict(self.dados[oc_id]) if oc_id in self.dados else None

    def atualizar_ocorrencia(self, oc_id, campos):
        if oc_id not in self.dados:
            return None
        self.dados[oc_id].update(campos)
        return dict(self.dados[oc_id])

    def remover_ocorrencia(self, oc_id):
        return self.dados.pop(oc_id, None) is not None

    def registrar_leitura_sensor(self, dados):
        for i in self.dados.values():
            if (i["origem"] == "sensor" and i["status"] == "ativa"
                    and i["bairro"] == dados["bairro"] and i["referencia"] == dados["referencia"]):
                i["nivel"] = dados["nivel"]
                return dict(i), False
        return self._novo(dados, "sensor"), True


VALIDO = {"bairro": "Pinheiros", "referencia": "Rua Exemplo, 100", "nivel": 3, "descricao": "Água na calçada"}
HDR_ADMIN = {"X-Admin-Token": ADMIN}


class BaseApi(unittest.TestCase):
    def setUp(self):
        self.banco = BancoFalso()
        for nome in ("criar_ocorrencia", "listar_ocorrencias", "obter_ocorrencia", "atualizar_ocorrencia",
                     "remover_ocorrencia", "registrar_leitura_sensor"):
            p = mock.patch.object(db, nome, getattr(self.banco, nome))
            p.start()
            self.addCleanup(p.stop)
        weather._cache.clear()
        self.app = create_app()
        self.cli = self.app.test_client()

    def criar(self, **extra):
        return self.cli.post("/api/ocorrencias", json={**VALIDO, **extra})


class TestCrud(BaseApi):
    def test_post_cria_201_com_location(self):
        r = self.criar()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json["origem"], "cidadao")
        self.assertEqual(r.headers["Location"], f"/api/ocorrencias/{r.json['id']}")

    def test_get_lista_e_filtra(self):
        self.criar()
        self.criar(bairro="Mooca")
        self.assertEqual(len(self.cli.get("/api/ocorrencias").json["dados"]), 2)
        filtrado = self.cli.get("/api/ocorrencias?bairro=Mooca").json["dados"]
        self.assertEqual([i["bairro"] for i in filtrado], ["Mooca"])

    def test_get_por_id_200_e_404(self):
        oc_id = self.criar().json["id"]
        self.assertEqual(self.cli.get(f"/api/ocorrencias/{oc_id}").status_code, 200)
        self.assertEqual(self.cli.get("/api/ocorrencias/999").status_code, 404)

    def test_put_atualiza_com_token(self):
        oc_id = self.criar().json["id"]
        r = self.cli.put(f"/api/ocorrencias/{oc_id}", json={"status": "resolvida"}, headers=HDR_ADMIN)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["status"], "resolvida")

    def test_put_404_e_400(self):
        self.assertEqual(self.cli.put("/api/ocorrencias/999", json={"nivel": 2}, headers=HDR_ADMIN).status_code, 404)
        oc_id = self.criar().json["id"]
        self.assertEqual(self.cli.put(f"/api/ocorrencias/{oc_id}", json={}, headers=HDR_ADMIN).status_code, 400)
        self.assertEqual(self.cli.put(f"/api/ocorrencias/{oc_id}", json={"status": "x"}, headers=HDR_ADMIN).status_code, 400)

    def test_delete_204_e_404(self):
        oc_id = self.criar().json["id"]
        self.assertEqual(self.cli.delete(f"/api/ocorrencias/{oc_id}", headers=HDR_ADMIN).status_code, 204)
        self.assertEqual(self.cli.delete(f"/api/ocorrencias/{oc_id}", headers=HDR_ADMIN).status_code, 404)


class TestValidacao(BaseApi):
    def setUp(self):
        super().setUp()
        self.app.extensions["limitador_post"].maximo = 1000  # aqui o foco é a validação, não o limite de taxa

    def test_entradas_invalidas_retornam_400(self):
        casos = [
            {**VALIDO, "nivel": 9}, {**VALIDO, "nivel": True}, {**VALIDO, "nivel": "3"},
            {**VALIDO, "bairro": "Gotham"}, {**VALIDO, "referencia": "ab"},
            {**VALIDO, "descricao": "x" * 281}, {**VALIDO, "origem": "sensor"},
            {**VALIDO, "status": "resolvida"}, {"bairro": "Pinheiros"}, [], "texto",
        ]
        for corpo in casos:
            with self.subTest(corpo=str(corpo)[:40]):
                self.assertEqual(self.cli.post("/api/ocorrencias", json=corpo).status_code, 400)

    def test_corpo_nao_json_retorna_400(self):
        r = self.cli.post("/api/ocorrencias", data="não sou json", content_type="text/plain")
        self.assertEqual(r.status_code, 400)

    def test_sql_injection_e_xss_sao_rejeitados(self):
        self.assertEqual(self.criar(referencia="x'; DROP TABLE ocorrencias;--").status_code, 400)
        self.assertEqual(self.criar(referencia="1' OR '1'='1").status_code, 400)  # "=" não está na allowlist
        self.assertEqual(self.criar(descricao="<script>alert(1)</script>").status_code, 400)

    def test_parametros_de_consulta_invalidos(self):
        for qs in ("?bairro=' OR 1=1--", "?status=qualquer", "?limit=0", "?limit=abc", "?offset=-1"):
            with self.subTest(qs=qs):
                self.assertEqual(self.cli.get("/api/ocorrencias" + qs).status_code, 400)

    def test_corpo_grande_demais_retorna_413(self):
        r = self.cli.post("/api/ocorrencias", data="{" + "a" * 9000 + "}", content_type="application/json")
        self.assertEqual(r.status_code, 413)


class TestSeguranca(BaseApi):
    def test_put_e_delete_exigem_token(self):
        oc_id = self.criar().json["id"]
        for headers in ({}, {"X-Admin-Token": "errado"}, {"X-Admin-Token": ""}):
            with self.subTest(headers=headers):
                self.assertEqual(self.cli.put(f"/api/ocorrencias/{oc_id}", json={"nivel": 1}, headers=headers).status_code, 401)
                self.assertEqual(self.cli.delete(f"/api/ocorrencias/{oc_id}", headers=headers).status_code, 401)

    def test_limite_de_taxa_no_post(self):
        codigos = [self.criar().status_code for _ in range(12)]
        self.assertEqual(codigos[:10], [201] * 10)
        self.assertEqual(codigos[10:], [429, 429])

    def test_erro_interno_nao_vaza_detalhes(self):
        with mock.patch.object(db, "listar_ocorrencias", side_effect=Exception("senha do banco: SEGREDO123")):
            r = self.cli.get("/api/ocorrencias")
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("SEGREDO123", r.get_data(as_text=True))
        self.assertEqual(r.json["erro"], "Erro interno. Tente novamente mais tarde.")

    def test_rota_inexistente_e_metodo_errado_em_json_generico(self):
        self.assertEqual(self.cli.get("/api/nada").status_code, 404)
        self.assertEqual(self.cli.patch("/api/ocorrencias").status_code, 405)

    def test_cabecalhos_de_seguranca(self):
        r = self.cli.get("/api/bairros")
        self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(r.headers["Cache-Control"], "no-store")

    def test_pagina_inicial_e_estaticos(self):
        self.assertEqual(self.cli.get("/").status_code, 200)
        self.assertEqual(self.cli.get("/static/app.js").status_code, 200)

    def test_log_registra_data_hora_acao_e_resultado(self):
        self.criar()
        with open(LOG, encoding="utf-8") as f:
            linhas = f.read()
        self.assertRegex(linhas, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| INFO \| acao=criar_ocorrencia resultado=sucesso")
        self.assertNotIn(ADMIN, linhas)
        self.assertNotIn("Rua Exemplo", linhas)  # corpo da requisição não vai para o log


class TestFonteExterna(BaseApi):
    def _resposta(self, valores):
        r = mock.Mock()
        r.raise_for_status.return_value = None
        r.json.return_value = {"hourly": {"time": ["t"] * len(valores), "precipitation": valores}}
        return r

    def test_risco_soma_e_classifica(self):
        with mock.patch.object(requests, "get", return_value=self._resposta([5, 10, 12.5, 0, None, 3])) as g:
            r = self.cli.get("/api/risco?bairro=Pinheiros")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["chuva_prevista_mm"], 30.5)
        self.assertEqual(r.json["nivel_risco"], "alto")
        self.assertEqual(g.call_args.kwargs["timeout"], 5)

    def test_cache_evita_nova_chamada(self):
        with mock.patch.object(requests, "get", return_value=self._resposta([1, 1, 1, 1, 1, 1])) as g:
            self.cli.get("/api/risco?bairro=Mooca")
            self.cli.get("/api/risco?bairro=Mooca")
        self.assertEqual(g.call_count, 1)

    def test_falha_externa_retorna_503_generico(self):
        with mock.patch.object(requests, "get", side_effect=requests.ConnectionError("detalhe interno")):
            r = self.cli.get("/api/risco?bairro=Penha")
        self.assertEqual(r.status_code, 503)
        self.assertNotIn("detalhe interno", r.get_data(as_text=True))

    def test_resposta_inesperada_retorna_503(self):
        ruim = mock.Mock()
        ruim.raise_for_status.return_value = None
        ruim.json.return_value = {"outra": "coisa"}
        with mock.patch.object(requests, "get", return_value=ruim):
            self.assertEqual(self.cli.get("/api/risco?bairro=Sé").status_code, 503)

    def test_bairro_invalido_retorna_400(self):
        self.assertEqual(self.cli.get("/api/risco?bairro=Gotham").status_code, 400)
        self.assertEqual(self.cli.get("/api/risco").status_code, 400)

    def test_limiares_de_classificacao(self):
        self.assertEqual([weather.classificar(x) for x in (0, 9.9, 10, 24.9, 25, 49.9, 50)],
                         ["baixo", "baixo", "moderado", "moderado", "alto", "alto", "muito alto"])


class FakeCursor:
    def __init__(self):
        self.chamadas, self.lastrowid, self.rowcount = [], 7, 1

    def execute(self, sql, params=None):
        self.chamadas.append((sql, params))

    def fetchone(self):
        return {"id": 7, "bairro": "Pinheiros", "referencia": "r", "nivel": 1, "descricao": None,
                "status": "ativa", "origem": "cidadao",
                "criado_em": datetime(2026, 11, 9, 10, 0, 0), "atualizado_em": datetime(2026, 11, 9, 10, 0, 0)}

    def fetchall(self):
        return [self.fetchone()]

    def close(self):
        pass


class FakeConn:
    def __init__(self):
        self.cur = FakeCursor()

    def cursor(self, dictionary=False):
        return self.cur

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class TestCamadaDb(unittest.TestCase):
    """Garante que valores do usuário NUNCA entram no texto do SQL (consultas parametrizadas)."""

    PAYLOAD = "x'; DROP TABLE ocorrencias;-- "

    def _executar(self, funcao, *args, **kwargs):
        conn = FakeConn()
        with mock.patch.object(db, "get_connection", return_value=conn):
            funcao(*args, **kwargs)
        return conn.cur.chamadas

    def test_insert_parametrizado(self):
        dados = {"bairro": "Pinheiros", "referencia": self.PAYLOAD, "nivel": 2, "descricao": self.PAYLOAD}
        chamadas = self._executar(db.criar_ocorrencia, dados)
        sql, params = chamadas[0]
        self.assertNotIn("DROP", sql)
        self.assertIn(self.PAYLOAD, params)
        self.assertEqual(sql.count("%s"), len(params))

    def test_select_com_filtros_parametrizado(self):
        chamadas = self._executar(db.listar_ocorrencias, bairro=self.PAYLOAD, status=self.PAYLOAD, limit=5, offset=0)
        sql, params = chamadas[0]
        self.assertNotIn("DROP", sql)
        self.assertEqual(sql.count("%s"), len(params))

    def test_update_so_aceita_colunas_da_allowlist(self):
        with self.assertRaises(ValueError):
            db.atualizar_ocorrencia(1, {"nivel = 1; DROP TABLE ocorrencias; --": 1})
        chamadas = self._executar(db.atualizar_ocorrencia, 1, {"descricao": self.PAYLOAD})
        sql, params = chamadas[0]
        self.assertNotIn("DROP", sql)
        self.assertEqual(params, (self.PAYLOAD, 1))

    def test_delete_parametrizado(self):
        sql, params = self._executar(db.remover_ocorrencia, 3)[0]
        self.assertEqual((sql.count("%s"), params), (1, (3,)))


class TestUdp(unittest.TestCase):
    def setUp(self):
        self.banco = BancoFalso()
        p = mock.patch.object(db, "registrar_leitura_sensor", self.banco.registrar_leitura_sensor)
        p.start()
        self.addCleanup(p.stop)

    def _msg(self, **extra):
        corpo = {"token": SENSOR, "bairro": "Pinheiros", "referencia": "Sensor S01", "nivel": 3}
        corpo.update(extra)
        return json.dumps(corpo).encode()

    def test_leitura_valida_cria_e_depois_atualiza(self):
        self.assertEqual(udp_listener.processar_datagrama(self._msg()), "criada")
        self.assertEqual(udp_listener.processar_datagrama(self._msg(nivel=4)), "atualizada")
        self.assertEqual(len(self.banco.dados), 1)
        self.assertEqual(self.banco.dados[1]["nivel"], 4)
        self.assertEqual(self.banco.dados[1]["origem"], "sensor")

    def test_rejeicoes(self):
        self.assertEqual(udp_listener.processar_datagrama(self._msg(token="errado")), "token")
        self.assertEqual(udp_listener.processar_datagrama(b"\xff\xfe nao e json"), "malformada")
        self.assertEqual(udp_listener.processar_datagrama(b"[1,2,3]"), "malformada")
        self.assertEqual(udp_listener.processar_datagrama(self._msg(nivel=99)), "validacao")
        self.assertEqual(udp_listener.processar_datagrama(self._msg(descricao="a" * 600)), "tamanho")
        self.assertEqual(len(self.banco.dados), 0)

    def test_socket_udp_real_em_localhost(self):
        sock = udp_listener.criar_socket("127.0.0.1", 0)
        porta = sock.getsockname()[1]
        parar = threading.Event()
        t = threading.Thread(target=udp_listener.servir, args=(sock, parar), daemon=True)
        t.start()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as cliente:
            cliente.sendto(self._msg(bairro="Mooca"), ("127.0.0.1", porta))
        for _ in range(50):
            if self.banco.dados:
                break
            time.sleep(0.05)
        parar.set()
        t.join(timeout=3)
        sock.close()
        self.assertEqual([i["bairro"] for i in self.banco.dados.values()], ["Mooca"])


class TestValidadores(unittest.TestCase):
    def test_normaliza_espacos_e_aceita_acentos(self):
        dados, erros = validators.validar_ocorrencia(
            {"bairro": "Sé", "referencia": "  Praça da Sé, nº 1 (metrô)  ", "nivel": 1})
        self.assertEqual(erros, {})
        self.assertEqual(dados["referencia"], "Praça da Sé, nº 1 (metrô)")

    def test_descricao_vazia_vira_none(self):
        dados, _ = validators.validar_ocorrencia({"descricao": "   "}, parcial=True)
        self.assertIsNone(dados["descricao"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
