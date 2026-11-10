# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Nycollas Kaua Pereira Chagas
# Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"""Acesso ao MySQL com mysql-connector-python (sem ORM). Toda consulta é parametrizada (%s)."""
from contextlib import contextmanager

from . import config

COLUNAS = "id, bairro, referencia, nivel, descricao, status, origem, criado_em, atualizado_em"
COLUNAS_ATUALIZAVEIS = ("bairro", "referencia", "nivel", "descricao", "status")


def get_connection():
    import mysql.connector  # importado aqui para os testes rodarem sem o driver instalado

    return mysql.connector.connect(
        host=config.env("DB_HOST"),
        port=int(config.env("DB_PORT", "3306")),
        user=config.env("DB_USER"),
        password=config.env("DB_PASSWORD"),
        database=config.env("DB_NAME"),
        charset="utf8mb4",
        connection_timeout=5,
    )


@contextmanager
def _cursor(commit=False):
    conexao = get_connection()
    try:
        cursor = conexao.cursor(dictionary=True)
        try:
            yield cursor
            if commit:
                conexao.commit()
        finally:
            cursor.close()
    except Exception:
        try:
            conexao.rollback()
        except Exception:
            pass
        raise
    finally:
        conexao.close()


def _serializar(linha):
    if linha is None:
        return None
    return {k: (v.isoformat(timespec="seconds") if hasattr(v, "isoformat") else v) for k, v in linha.items()}


def _buscar(cursor, oc_id):
    cursor.execute(f"SELECT {COLUNAS} FROM ocorrencias WHERE id = %s", (oc_id,))
    return _serializar(cursor.fetchone())


# ---------- CRUD ----------

def criar_ocorrencia(dados, origem="cidadao"):
    sql = "INSERT INTO ocorrencias (bairro, referencia, nivel, descricao, origem) VALUES (%s, %s, %s, %s, %s)"
    params = (dados["bairro"], dados["referencia"], dados["nivel"], dados.get("descricao"), origem)
    with _cursor(commit=True) as cur:
        cur.execute(sql, params)
        return _buscar(cur, cur.lastrowid)


def listar_ocorrencias(bairro=None, status=None, limit=50, offset=0):
    condicoes, params = [], []
    if bairro:
        condicoes.append("bairro = %s")
        params.append(bairro)
    if status:
        condicoes.append("status = %s")
        params.append(status)
    where = (" WHERE " + " AND ".join(condicoes)) if condicoes else ""
    sql = f"SELECT {COLUNAS} FROM ocorrencias{where} ORDER BY criado_em DESC, id DESC LIMIT %s OFFSET %s"
    params += [limit, offset]
    with _cursor() as cur:
        cur.execute(sql, tuple(params))
        return [_serializar(linha) for linha in cur.fetchall()]


def obter_ocorrencia(oc_id):
    with _cursor() as cur:
        return _buscar(cur, oc_id)


def atualizar_ocorrencia(oc_id, campos):
    """Atualiza só colunas da allowlist; nomes de coluna nunca vêm do cliente, valores vão como parâmetros."""
    invalidas = set(campos) - set(COLUNAS_ATUALIZAVEIS)
    if invalidas:
        raise ValueError("coluna não permitida")
    with _cursor(commit=True) as cur:
        if campos:
            partes = ", ".join(f"{coluna} = %s" for coluna in campos)
            cur.execute(f"UPDATE ocorrencias SET {partes} WHERE id = %s", (*campos.values(), oc_id))
        return _buscar(cur, oc_id)


def remover_ocorrencia(oc_id):
    with _cursor(commit=True) as cur:
        cur.execute("DELETE FROM ocorrencias WHERE id = %s", (oc_id,))
        return cur.rowcount > 0


def registrar_leitura_sensor(dados):
    """Leitura de sensor: atualiza a ocorrência ativa do mesmo ponto ou cria uma nova.
    Retorna (ocorrencia, criada)."""
    with _cursor(commit=True) as cur:
        cur.execute(
            "SELECT id FROM ocorrencias WHERE origem = 'sensor' AND status = 'ativa' "
            "AND bairro = %s AND referencia = %s LIMIT 1",
            (dados["bairro"], dados["referencia"]),
        )
        existente = cur.fetchone()
        if existente:
            cur.execute("UPDATE ocorrencias SET nivel = %s WHERE id = %s", (dados["nivel"], existente["id"]))
            return _buscar(cur, existente["id"]), False
        cur.execute(
            "INSERT INTO ocorrencias (bairro, referencia, nivel, descricao, origem) "
            "VALUES (%s, %s, %s, %s, 'sensor')",
            (dados["bairro"], dados["referencia"], dados["nivel"], dados.get("descricao")),
        )
        return _buscar(cur, cur.lastrowid), True
