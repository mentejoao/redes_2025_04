# 🌐 Mini-NET — Implementação de uma Pilha de Protocolos de Rede

> Projeto Integrador — Disciplina: Redes de Computadores 2025/4  
> Professor: _Hugo Marciano de Melo_  
> Alunos: _João Gabriel Cavalcante França, Leonardo Moreira de Araújo, Vitor Martins Castanheira_

---

## 📖 Visão Geral

O **Mini-NET** é uma implementação didática de uma pilha de protocolos de rede inspirada no modelo OSI/TCP-IP. O objetivo é construir um **chat funcional sobre UDP** — um canal propositalmente não confiável — implementando via código todas as garantias de entrega, integridade, endereçamento e roteamento.

O projeto é dividido em **4 fases incrementais**, cada uma adicionando uma nova camada de protocolo sobre a anterior.
Até chegarmos ao modelo final que será executado, e está em **/final_phase**

---

## 📁 Estrutura do Repositório

```
mini-net/
│
├── final_phase/        ← ✅ VERSÃO FINAL — use estes arquivos para executar
│   ├── client.py       #    Cliente com pilha completa (L7 → L2)
│   ├── server.py       #    Servidor com pilha completa (L2 → L7)
│   ├── router.py       #    Roteador intermediário (L2/L3)
│   ├── protocol.py     #    Fornecido pelo professor — NÃO MODIFICAR
│   └── README.md
│
├── phases/             ← 📚 Fases incrementais (apenas para referência)
│   ├── phase_01.py     #    Fase 1: Aplicação (JSON + UDP + P2P)
│   ├── phase_02.py     #    Fase 2: Transporte (Stop-and-Wait, ACK, Timeout)
│   ├── phase_03.py     #    Fase 3: Rede (VIPs, TTL, Roteamento)
│   └── phase_04.py     #    Fase 4: Enlace (MACs, CRC32) — equivalente ao final_phase
│
└── video/              ← 🎥 Vídeo de demonstração
```

> **Importante:** O diretório `final_phase/` contém a versão final e consolidada do projeto, separada em arquivos por papel (`client.py`, `server.py`, `router.py`), conforme exigido pelo professor. O diretório `phases/` existe apenas para evidenciar o raciocínio incremental de desenvolvimento — cada arquivo representa uma etapa da construção da pilha de protocolos.

---

## 🏗️ Arquitetura

O encapsulamento segue o modelo de "Bonecas Russas":

```
┌──────────────────────────────────────────────┐
│  QUADRO (Enlace — L2)                        │
│  ┌────────────────────────────────────────┐  │
│  │  PACOTE (Rede — L3)                    │  │
│  │  ┌──────────────────────────────────┐  │  │
│  │  │  SEGMENTO (Transporte — L4)      │  │  │
│  │  │  ┌────────────────────────────┐  │  │  │
│  │  │  │  JSON (Aplicação — L7)     │  │  │  │
│  │  │  └────────────────────────────┘  │  │  │
│  │  └──────────────────────────────────┘  │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

**Fluxo de comunicação (Fase 4 completa):**

```
[HOST_A] ──┐
           ├──→ [ROTEADOR] ──→ [SERVIDOR]
[HOST_B] ──┘
```

---

## 🚀 Como Rodar 


**Arquivos:** `router.py` + `server.py` + `client.py`

**Execução (4 terminais):**

```bash
# Terminal 1 — Roteador (iniciar primeiro)
python router.py
# Porta do roteador: 5000
# Rota> SERVIDOR 127.0.0.1 5003
# Rota> HOST_A 127.0.0.1 5001
# Rota> HOST_B 127.0.0.1 5002
# Rota> (vazio para confirmar)

# Terminal 2 — Servidor
python server.py
# Modo: server
# IP do roteador: 127.0.0.1  |  Porta: 5000
# Minha porta real: 5003
# Meu VIP: SERVIDOR

# Terminal 3 — Cliente A
python client.py
# Modo: client
# IP do roteador: 127.0.0.1  |  Porta: 5000
# Minha porta real: 5001
# Meu VIP: HOST_A
# VIP destino: SERVIDOR
# Seu nome: Alice

# Terminal 4 — Cliente B
python client.py
# Modo: client
# IP do roteador: 127.0.0.1  |  Porta: 5000
# Minha porta real: 5002
# Meu VIP: HOST_B
# VIP destino: SERVIDOR
# Seu nome: Bob
```

---

## 🎨 Legenda dos Logs

Cada camada tem uma cor dedicada no terminal para facilitar a visualização:

| Cor       | Camada / Evento                              |
|-----------|----------------------------------------------|
| 🔴 Vermelho | Erros físicos, corrupção, CRC inválido      |
| 🟡 Amarelo  | Retransmissões, timeouts, duplicatas        |
| 🔵 Azul     | Enlace (MACs, CRC OK, encaminhamento)       |
| 🟣 Magenta  | Rede (VIPs, TTL, roteamento)                |
| 🩵 Ciano    | Transporte (SEQ, ACK, Stop-and-Wait)        |
| 🟢 Verde    | Aplicação (mensagem entregue com sucesso)   |

---

## 🧩 Resumo das Camadas por Fase

| Fase | Camada       | PDU      | Recurso Principal                        |
|------|--------------|----------|------------------------------------------|
| 1    | Aplicação    | JSON     | Formato de mensagem, sockets UDP         |
| 2    | Transporte   | Segmento | Stop-and-Wait, ACK, Timeout, SEQ 0/1    |
| 3    | Rede         | Pacote   | VIPs, TTL, roteamento estático           |
| 4    | Enlace       | Quadro   | MACs, CRC32, detecção de corrupção       |
