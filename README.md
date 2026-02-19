# 🌐 Mini-NET — Implementação de uma Pilha de Protocolos de Rede

> Projeto Integrador — Disciplina: Redes de Computadores 2025/4  
Professor: _Hugo Marciano de Melo_  
Alunos: _João Gabriel Cavalcante França, Leonardo Moreira de Araújo, Vitor Martins Castanheira_

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

## 🚀 Como Rodar

### Execução (Pilha Completa)

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

**Arquivos:** `client.py`, `server.py`, `router.py`, `protocol.py`

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
# Minha porta real: 5003
# Meu VIP: SERVIDOR
# IP do roteador: 127.0.0.1  |  Porta: 5000

# Terminal 3 — Cliente A
python client.py
# Minha porta real: 5001
# Meu VIP: HOST_A
# IP do roteador: 127.0.0.1  |  Porta: 5000
# VIP destino: SERVIDOR
# Seu nome: Alice

# Terminal 4 — Cliente B
python client.py
# Minha porta real: 5002
# Meu VIP: HOST_B
# IP do roteador: 127.0.0.1  |  Porta: 5000
# VIP destino: SERVIDOR
# Seu nome: Bob
```

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