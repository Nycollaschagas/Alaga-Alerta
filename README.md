<!-- SPDX-License-Identifier: BSD-3-Clause
     Copyright (c) 2026, Nycollas Kaua Pereira Chagas
     Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD. -->

# AlagaAlerta

Alertas comunitários de alagamento em São Paulo. Projeto da **Global Solution CitizenTech** (FIAP, disciplina *Coding for Security*).

**Ideia:** cidadãos e sensores relatam pontos alagados; o sistema cruza esses relatos com a previsão de chuva das próximas 6 horas (API aberta Open-Meteo) para mostrar o risco por bairro.
**ODS:** 11 (Cidades e comunidades sustentáveis), 13 (Ação contra a mudança global do clima) e 9 (Indústria, inovação e infraestrutura).

## O que tem no projeto

| Requisito | Onde está |
|---|---|
| API REST Flask (GET, POST, PUT, DELETE) com status HTTP corretos | `app/routes.py` |
| MySQL com CRUD em Python puro (sem ORM), consultas parametrizadas | `app/db.py`, `schema.sql` |
| Fonte externa (requests + JSON): Open-Meteo | `app/weather.py` |
| Interface web mínima (HTML/CSS/JS) que consome a API | `static/` |
| Log em arquivo (data/hora, ação, resultado) | `app/logger.py` → `logs/alagaalerta.log` |
| Módulo à escolha: **sockets UDP** (sensores de nível de água) | `app/udp_listener.py`, `sensor_sim.py` |
| Validação de entrada, tratamento de exceções, erros genéricos | `app/validators.py`, `app/__init__.py` |
| Testes automatizados (33) | `tests/` |

## Executar do zero (Debian/Kali)

```bash
# 1. Dependências do sistema (MariaDB é o MySQL do Debian/Kali)
sudo apt update && sudo apt install -y python3-venv mariadb-server
sudo service mariadb start

# 2. Banco de dados e usuário com privilégios mínimos (escolha a SUA senha)
sudo mysql < schema.sql
sudo mysql -e "CREATE USER 'alaga_app'@'localhost' IDENTIFIED BY 'SUA_SENHA_FORTE'; \
  GRANT SELECT, INSERT, UPDATE, DELETE ON alagaalerta.ocorrencias TO 'alaga_app'@'localhost'; FLUSH PRIVILEGES;"

# 3. Ambiente Python
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 4. Configuração (.env nunca vai para o Git)
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # rode duas vezes: ADMIN_TOKEN e SENSOR_TOKEN
nano .env                                                       # preencha DB_PASSWORD e os dois tokens

# 5. Subir a aplicação
python run.py                      # http://127.0.0.1:5000
```

### Módulo UDP (opcional, em outros terminais)

```bash
source venv/bin/activate
python -m app.udp_listener         # terminal A: ouve sensores em udp://127.0.0.1:9999
python sensor_sim.py Pinheiros 3   # terminal B: envia uma leitura fictícia (bairro, nível 1-4)
```
A leitura aparece na lista da página como "· sensor". Leituras repetidas do mesmo ponto atualizam a ocorrência em vez de criar duplicatas.

### Testes

```bash
python -m unittest discover -s tests -v   # não precisa de MySQL nem de internet
```

## API

| Método | Rota | Descrição | Sucesso | Erros |
|---|---|---|---|---|
| GET | `/api/ocorrencias?bairro=&status=&limit=&offset=` | Lista ocorrências | 200 | 400 |
| GET | `/api/ocorrencias/<id>` | Detalha uma ocorrência | 200 | 404 |
| POST | `/api/ocorrencias` | Cria um relato (aberto, com limite de taxa) | 201 | 400, 413, 429 |
| PUT | `/api/ocorrencias/<id>` | Atualiza (exige `X-Admin-Token`) | 200 | 400, 401, 404 |
| DELETE | `/api/ocorrencias/<id>` | Remove (exige `X-Admin-Token`) | 204 | 401, 404 |
| GET | `/api/risco?bairro=` | Chuva prevista em 6 h (Open-Meteo) | 200 | 400, 503 |
| GET | `/api/bairros` | Bairros aceitos | 200 | – |

Níveis: 1 atenção · 2 via alagada · 3 intransitável · 4 risco grave.

```bash
curl -X POST http://127.0.0.1:5000/api/ocorrencias -H "Content-Type: application/json" \
  -d '{"bairro":"Pinheiros","referencia":"Rua Exemplo, 100","nivel":3,"descricao":"Água na calçada"}'

curl "http://127.0.0.1:5000/api/risco?bairro=Pinheiros"

curl -X PUT http://127.0.0.1:5000/api/ocorrencias/1 -H "Content-Type: application/json" \
  -H "X-Admin-Token: SEU_ADMIN_TOKEN" -d '{"status":"resolvida"}'

curl -X DELETE http://127.0.0.1:5000/api/ocorrencias/1 -H "X-Admin-Token: SEU_ADMIN_TOKEN"
```

## Segurança e privacidade (LGPD)

- **Credenciais só no `.env`** (ignorado pelo Git); a aplicação não inicia sem elas nem com tokens curtos.
- **Consultas parametrizadas** (`%s`) em todo SQL; nomes de coluna vêm de uma allowlist, nunca do cliente.
- **Validação por allowlist** de todo campo (tipo, tamanho, caracteres, bairro/nível/status permitidos) e rejeição de campos extras.
- **Erros sem detalhes internos:** o cliente recebe mensagens genéricas; o detalhe técnico fica só no log.
- **Coleta mínima:** nenhum nome, telefone, e-mail ou IP é gravado. Use apenas dados fictícios ou abertos.
- **Moderação:** PUT/DELETE exigem token (comparação em tempo constante); POST tem limite de taxa por IP.
- **Interface:** textos da API entram na página com `textContent` (sem `innerHTML`) e há Content-Security-Policy.
- **Log sem dados sensíveis:** não registra corpo de requisição, tokens nem IPs; quebras de linha são neutralizadas.

## Limitações conhecidas

HTTPS deve ser feito por proxy reverso (nginx/Apache) em produção; o limitador de taxa é em memória (por processo);
o token do sensor UDP trafega sem criptografia (em produção, usar VPN/DTLS); os limiares de risco são uma heurística
didática, não critérios oficiais da Defesa Civil.

## Licença

BSD 3-Clause (exigência FIAP: GPL v3 ou BSD). Texto completo em `LICENSE.MD`; o aviso também está no cabeçalho de cada arquivo.

## Enviar ao GitHub

```bash
git init && git add . && git commit -m "AlagaAlerta: Global Solution CitizenTech"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/alagaalerta.git
git push -u origin main
```
