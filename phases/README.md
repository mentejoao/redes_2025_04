# 🌐 Mini-NET — Implementação de uma Pilha de Protocolos de Rede

> Projeto Integrador — Disciplina: Redes de Computadores 2025/4  

---

## 📖 Visão Geral

O **Mini-NET** é uma implementação didática de uma pilha de protocolos de rede inspirada no modelo OSI/TCP-IP. O objetivo é construir um **chat funcional sobre UDP** — um canal propositalmente não confiável — implementando via código todas as garantias de entrega, integridade, endereçamento e roteamento.

O projeto é dividido em **4 fases incrementais**, cada uma adicionando uma nova camada de protocolo sobre a anterior.

---

## 🏗️ Arquitetura

O encapsulamento segue o modelo de "Bonecas Russas":

```
┌──────────────────────────────────────────────┐
│  QUADRO (Enlace — L2)                        │
│  ┌────────────────────────────────────────┐  │
│  │  PACOTE (Rede — L3)                   │  │
│  │  ┌──────────────────────────────────┐ │  │
│  │  │  SEGMENTO (Transporte — L4)      │ │  │
│  │  │  ┌────────────────────────────┐  │ │  │
│  │  │  │  JSON (Aplicação — L7)     │  │ │  │
│  │  │  └────────────────────────────┘  │ │  │
│  │  └──────────────────────────────────┘ │  │
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

## 📡 Simulador de Canal Físico

O arquivo `protocol.py` simula um meio físico ruidoso. Os parâmetros podem ser ajustados para os testes:

```python
PROBABILIDADE_PERDA    = 0.2   # 20% de chance de o pacote ser descartado
PROBABILIDADE_CORRUPCAO = 0.2  # 20% de chance de corrupção de bits
LATENCIA_MIN           = 0.1   # Atraso mínimo (segundos)
LATENCIA_MAX           = 0.5   # Atraso máximo (segundos)
```

> 💡 **Dica para demonstração:** configure `PROBABILIDADE_PERDA = 0.5` e `PROBABILIDADE_CORRUPCAO = 0.5` para estressar o sistema e evidenciar as retransmissões nos logs.

---

## 🚀 Como Rodar — Fase a Fase

---

### Fase 1 — Aplicação e Sockets

**O que foi implementado:**
- Arquitetura **P2P** (peer-to-peer) com UDP
- Formato **JSON** para as mensagens (`type`, `sender`, `message`, `timestamp`)
- Thread dedicada para receber mensagens em paralelo ao envio

**Arquivos:** `phase_01.py`

**Execução (2 ou mais terminais):**

```bash
# Terminal 1
python phase_01.py
# Minha porta: 5001
# Peers > 127.0.0.1:5002
# Peers > (vazio para terminar)
# Seu nome: Alice

# Terminal 2
python phase_01.py
# Minha porta: 5002
# Peers > 127.0.0.1:5001
# Peers > (vazio para terminar)
# Seu nome: Bob
```

---

### Fase 2 — Transporte (Stop-and-Wait)

**O que foi implementado:**
- Migração para **arquitetura Cliente-Servidor**
- Protocolo **Stop-and-Wait**: o cliente trava até receber confirmação antes de enviar a próxima mensagem
- **ACKs**: o servidor confirma cada segmento recebido
- **Timeout + Retransmissão**: se o ACK não chegar em 2s, o cliente retransmite automaticamente
- **Números de Sequência alternantes (0/1)**: o receptor detecta e descarta duplicatas

**Arquivos:** `phase_02.py`

**Execução (2 terminais):**

```bash
# Terminal 1 — Servidor
python phase_02.py
# Modo: server
# Porta do servidor: 5000

# Terminal 2 — Cliente
python phase_02.py
# Modo: client
# IP do servidor: 127.0.0.1
# Porta do servidor: 5000
# Seu nome: Alice
```

---

### Fase 3 — Rede e Roteamento

**O que foi implementado:**
- **Endereços virtuais (VIPs):** `HOST_A`, `HOST_B`, `SERVIDOR`
- **TTL (Time To Live):** pacotes com TTL ≤ 0 são descartados pelo roteador
- **Roteador intermediário:** clientes nunca enviam diretamente ao servidor; todo tráfego passa pelo roteador
- **Tabela de roteamento estática:** configurada na inicialização do `router.py`
- **ACK retorna pelo roteador:** o caminho de volta também passa pelas camadas de rede

**Arquivos:** `phase_03.py` + `router.py`

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
python phase_03.py
# Modo: server
# IP do roteador: 127.0.0.1  |  Porta: 5000
# Minha porta real: 5003
# Meu VIP: SERVIDOR

# Terminal 3 — Cliente A
python phase_03.py
# Modo: client
# IP do roteador: 127.0.0.1  |  Porta: 5000
# Minha porta real: 5001
# Meu VIP: HOST_A
# VIP destino: SERVIDOR
# Seu nome: Alice

# Terminal 4 — Cliente B
python phase_03.py
# Modo: client
# IP do roteador: 127.0.0.1  |  Porta: 5000
# Minha porta real: 5002
# Meu VIP: HOST_B
# VIP destino: SERVIDOR
# Seu nome: Bob
```

---

### Fase 4 — Enlace e Integridade (Pilha Completa)

**O que foi implementado:**
- **Endereços MAC fictícios** para cada nó da rede:

  | VIP       | MAC                 |
  |-----------|---------------------|
  | HOST_A    | AA:AA:AA:AA:AA:01   |
  | HOST_B    | BB:BB:BB:BB:BB:02   |
  | SERVIDOR  | CC:CC:CC:CC:CC:03   |
  | ROTEADOR  | DD:DD:DD:DD:DD:04   |

- **CRC32 (FCS):** calculado e embutido no Quadro antes do envio via `Quadro.serializar()`
- **Verificação de integridade:** ao receber, `Quadro.deserializar()` recalcula o CRC; divergência → descarte silencioso
- **Re-encapsulamento no Roteador:** o roteador consome o quadro antigo, atualiza MACs e TTL, e gera um novo quadro com CRC recalculado para o próximo salto
- **Recuperação transparente:** a Camada de Transporte (Fase 2) cobre as perdas por CRC via timeout + retransmissão

**Arquivos:** `phase_04.py` + `router.py`

**Execução (4 terminais — mesma configuração da Fase 3):**

```bash
# Terminal 1 — Roteador (iniciar primeiro)
python router.py
# Porta do roteador: 5000
# Rota> SERVIDOR 127.0.0.1 5003
# Rota> HOST_A 127.0.0.1 5001
# Rota> HOST_B 127.0.0.1 5002
# Rota> (vazio para confirmar)

# Terminal 2 — Servidor
python phase_04.py
# Modo: server
# IP do roteador: 127.0.0.1  |  Porta: 5000
# Minha porta real: 5003
# Meu VIP: SERVIDOR

# Terminal 3 — Cliente A
python phase_04.py
# Modo: client
# IP do roteador: 127.0.0.1  |  Porta: 5000
# Minha porta real: 5001
# Meu VIP: HOST_A
# VIP destino: SERVIDOR
# Seu nome: Alice

# Terminal 4 — Cliente B
python phase_04.py
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