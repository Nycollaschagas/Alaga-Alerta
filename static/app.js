// SPDX-License-Identifier: BSD-3-Clause
// Copyright (c) 2026, Nycollas Kaua Pereira Chagas
// Licenciado sob a licença BSD de 3 cláusulas. Veja LICENSE.MD.
"use strict";

const NIVEIS = {
  1: "Atenção", 2: "Via alagada", 3: "Intransitável", 4: "Risco grave",
};
const el = (id) => document.getElementById(id);
let tokenAdmin = "";

// Todo texto vindo da API é inserido com textContent (nunca innerHTML): evita XSS.
function mostrarMensagem(texto, ehErro) {
  const caixa = el("mensagem");
  caixa.textContent = texto;
  caixa.className = ehErro ? "erro" : "";
}

async function api(caminho, opcoes = {}) {
  const resposta = await fetch(caminho, opcoes);
  if (resposta.status === 204) return null;
  const corpo = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    const detalhes = corpo.detalhes ? " " + Object.values(corpo.detalhes).join(" ") : "";
    throw new Error((corpo.erro || "Falha na requisição.") + detalhes);
  }
  return corpo;
}

function cabecalhosJson() {
  const cab = { "Content-Type": "application/json" };
  if (tokenAdmin) cab["X-Admin-Token"] = tokenAdmin;
  return cab;
}

function preencherSelect(select, bairros, comTodos) {
  select.replaceChildren();
  if (comTodos) select.append(new Option("Todos os bairros", ""));
  bairros.forEach((b) => select.append(new Option(b, b)));
}

async function carregarRisco() {
  const bairro = el("sel-risco").value;
  const caixa = el("risco-resultado");
  try {
    const r = await api("/api/risco?bairro=" + encodeURIComponent(bairro));
    caixa.className = "risco-" + r.nivel_risco.replace(" ", "-");
    caixa.textContent = `Risco ${r.nivel_risco}: ${r.chuva_prevista_mm} mm previstos em ${r.janela_horas} h (fonte: ${r.fonte}).`;
  } catch (e) {
    caixa.className = "";
    caixa.textContent = e.message;
  }
}

function criarItem(o) {
  const li = document.createElement("li");
  li.className = `item n${o.nivel} ${o.status}`;

  const titulo = document.createElement("h3");
  titulo.textContent = `${o.referencia} — ${o.bairro}`;
  const selo = document.createElement("span");
  selo.className = "selo";
  selo.textContent = `${NIVEIS[o.nivel]}${o.origem === "sensor" ? " · sensor" : ""}${o.status === "resolvida" ? " · resolvida" : ""}`;
  titulo.append(selo);
  li.append(titulo);

  if (o.descricao) {
    const p = document.createElement("p");
    p.textContent = o.descricao;
    li.append(p);
  }
  const meta = document.createElement("p");
  meta.className = "meta";
  meta.textContent = "Atualizado em " + new Date(o.atualizado_em).toLocaleString("pt-BR");
  li.append(meta);

  if (tokenAdmin) {
    const acoes = document.createElement("div");
    acoes.className = "acoes";
    if (o.status === "ativa") {
      const b = document.createElement("button");
      b.type = "button"; b.className = "secundario"; b.textContent = "Resolver";
      b.addEventListener("click", () => acao(o.id, "PUT", { status: "resolvida" }, "Ponto marcado como resolvido."));
      acoes.append(b);
    }
    const r = document.createElement("button");
    r.type = "button"; r.className = "perigo"; r.textContent = "Remover";
    r.addEventListener("click", () => acao(o.id, "DELETE", null, "Ocorrência removida."));
    acoes.append(r);
    li.append(acoes);
  }
  return li;
}

async function carregarLista() {
  const bairro = el("filtro-bairro").value;
  const consulta = bairro ? "?bairro=" + encodeURIComponent(bairro) : "";
  const lista = el("lista");
  try {
    const { dados } = await api("/api/ocorrencias" + consulta);
    lista.replaceChildren();
    if (dados.length === 0) {
      const vazio = document.createElement("li");
      vazio.className = "aviso";
      vazio.textContent = "Nenhum ponto reportado.";
      lista.append(vazio);
    }
    dados.forEach((o) => lista.append(criarItem(o)));
  } catch (e) {
    mostrarMensagem(e.message, true);
  }
}

async function acao(id, metodo, corpo, sucesso) {
  try {
    await api(`/api/ocorrencias/${id}`, {
      method: metodo,
      headers: cabecalhosJson(),
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
    mostrarMensagem(sucesso, false);
    carregarLista();
  } catch (e) {
    mostrarMensagem(e.message, true);
  }
}

async function enviarRelato(evento) {
  evento.preventDefault();
  const corpo = {
    bairro: el("rel-bairro").value,
    referencia: el("rel-ref").value,
    nivel: Number(el("rel-nivel").value),
    descricao: el("rel-desc").value,
  };
  try {
    await api("/api/ocorrencias", { method: "POST", headers: cabecalhosJson(), body: JSON.stringify(corpo) });
    mostrarMensagem("Relato enviado. Obrigado por ajudar a comunidade!", false);
    el("form-relato").reset();
    carregarLista();
  } catch (e) {
    mostrarMensagem(e.message, true);
  }
}

async function iniciar() {
  try {
    const { dados: bairros } = await api("/api/bairros");
    preencherSelect(el("sel-risco"), bairros, false);
    preencherSelect(el("rel-bairro"), bairros, false);
    preencherSelect(el("filtro-bairro"), bairros, true);
  } catch (e) {
    mostrarMensagem(e.message, true);
    return;
  }
  el("sel-risco").addEventListener("change", carregarRisco);
  el("filtro-bairro").addEventListener("change", carregarLista);
  el("form-relato").addEventListener("submit", enviarRelato);
  el("admin-token").addEventListener("input", (e) => { tokenAdmin = e.target.value.trim(); carregarLista(); });
  carregarRisco();
  carregarLista();
}

iniciar();
