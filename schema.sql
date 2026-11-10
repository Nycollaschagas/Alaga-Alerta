-- SPDX-License-Identifier: BSD-3-Clause
-- Copyright (c) 2026, Nycollas Kaua Pereira Chagas
-- Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
-- Execute como administrador do MySQL/MariaDB:  sudo mysql < schema.sql

CREATE DATABASE IF NOT EXISTS alagaalerta CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE alagaalerta;

-- Coleta mínima (LGPD): nenhum nome, e-mail, telefone ou IP é armazenado.
CREATE TABLE IF NOT EXISTS ocorrencias (
    id            INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    bairro        VARCHAR(40)  NOT NULL,
    referencia    VARCHAR(120) NOT NULL,
    nivel         TINYINT UNSIGNED NOT NULL,
    descricao     VARCHAR(280) NULL,
    status        ENUM('ativa', 'resolvida') NOT NULL DEFAULT 'ativa',
    origem        ENUM('cidadao', 'sensor')  NOT NULL DEFAULT 'cidadao',
    criado_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT ck_nivel CHECK (nivel BETWEEN 1 AND 4),
    INDEX idx_bairro_status (bairro, status),
    INDEX idx_criado_em (criado_em)
) ENGINE = InnoDB;
