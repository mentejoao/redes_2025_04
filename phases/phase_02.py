"""
phase_02.py - Fase 2: Camada de Transporte

Implementa:
  - Arquitetura Cliente-Servidor
  - Protocolo Stop-and-Wait (RDT 2.2 / 3.0)
  - ACKs (confirmações de recebimento)
  - Timeouts com retransmissão automática
  - Números de Sequência (bit alternante 0/1) para descartar duplicatas

Uso:
  Modo servidor  →  python phase_02.py  e escolha "server"
  Modo cliente   →  python phase_02.py  e escolha "client"

Dependência: protocol.py 
"""

import socket
import json
import threading
from datetime import datetime
from protocol import Segmento, enviar_pela_rede_ruidosa

# ──────────────────────────────────────────────
# CONFIGURAÇÕES
# ──────────────────────────────────────────────
TIMEOUT_SEGUNDOS = 2.0   # Tempo máximo aguardando ACK antes de retransmitir
BUFFER_SIZE      = 65535 # Tamanho máximo do buffer UDP

# ──────────────────────────────────────────────
# CORES ANSI para os logs 
# ──────────────────────────────────────────────
VERMELHO  = "\033[91m"   # Erros físicos / corrupção
AMARELO   = "\033[93m"   # Retransmissões / timeouts
CIANO     = "\033[96m"   # Eventos de transporte (ACK, SEQ)
VERDE     = "\033[92m"   # Mensagens de aplicação
RESET     = "\033[0m"


def log(camada: str, msg: str, cor: str = ""):
    """Imprime log padronizado com identificação de camada."""
    print(f"{cor}[{camada}] {msg}{RESET}")


# ══════════════════════════════════════════════════════════════════
# SERVIDOR
# ══════════════════════════════════════════════════════════════════
def run_server(minha_porta: int):
    """
    Servidor de chat.
    Recebe segmentos do cliente, verifica integridade básica,
    envia ACK e exibe a mensagem na tela.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", minha_porta))

    log("SERVIDOR", f"Aguardando conexões em 127.0.0.1:{minha_porta}", VERDE)
    log("SERVIDOR", "Pronto para receber mensagens...\n", VERDE)

    # Estado do receptor Stop-and-Wait
    seq_esperado = 0

    while True:
        # ── Camada Física: recebe bytes crus ──
        try:
            dados_brutos, endereco_cliente = sock.recvfrom(BUFFER_SIZE)
        except Exception as e:
            log("SERVIDOR", f"Erro ao receber dados: {e}", VERMELHO)
            continue

        # ── Camada de Transporte: desempacota Segmento ──
        try:
            seg_dict = json.loads(dados_brutos.decode("utf-8"))
            seg = Segmento(
                seq_num = seg_dict["seq_num"],
                is_ack  = seg_dict["is_ack"],
                payload = seg_dict["payload"]
            )
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
            # Segmento chegou tão corrompido que nem o JSON sobreviveu.
            # Descartamos silenciosamente; o timeout do cliente tratará isso.
            log("TRANSPORTE", "Segmento corrompido recebido → descartado (sem ACK)", VERMELHO)
            continue

        # Ignorar ACKs chegando no servidor (não esperado nesta fase)
        if seg.is_ack:
            continue

        log("TRANSPORTE",
            f"Segmento recebido | SEQ={seg.seq_num} | Esperado={seq_esperado} "
            f"| De: {endereco_cliente}",
            CIANO)

        # ── Envia ACK de volta (mesmo para duplicatas — comportamento RDT correto) ──
        ack = Segmento(seq_num=seg.seq_num, is_ack=True, payload=None)
        ack_bytes = json.dumps(ack.to_dict()).encode("utf-8")

        log("TRANSPORTE", f"Enviando ACK {seg.seq_num} → {endereco_cliente}", CIANO)
        enviar_pela_rede_ruidosa(sock, ack_bytes, endereco_cliente)

        # ── Verifica se é pacote novo ou duplicata ──
        if seg.seq_num == seq_esperado:
            # Pacote novo → processa e avança o número de sequência esperado
            payload = seg.payload
            ts  = payload.get("timestamp", "??:??")
            remetente = payload.get("sender", "Desconhecido")
            mensagem  = payload.get("message", "")

            log("APLICAÇÃO",
                f"[{ts[:19]}] {remetente}: {mensagem}",
                VERDE)

            seq_esperado = 1 - seq_esperado  # Alterna: 0→1 ou 1→0

        else:
            # Duplicata → descarta (o ACK já foi reenviado acima)
            log("TRANSPORTE",
                f"Duplicata detectada (SEQ={seg.seq_num}) → descartada",
                AMARELO)

        print()  # Linha em branco para legibilidade


# ══════════════════════════════════════════════════════════════════
# CLIENTE
# ══════════════════════════════════════════════════════════════════
def run_client(ip_servidor: str, porta_servidor: int, nome: str):
    """
    Cliente de chat com Stop-and-Wait.
    Cada mensagem só avança para a próxima após receber ACK correto.
    Em caso de timeout ou ACK corrompido, retransmite automaticamente.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT_SEGUNDOS)
    endereco_servidor = (ip_servidor, porta_servidor)

    log("CLIENTE", f"Apontando para servidor {ip_servidor}:{porta_servidor}", VERDE)
    log("CLIENTE", f"Logado como '{nome}'. Digite sua mensagem e pressione Enter.\n", VERDE)

    # Estado do emissor Stop-and-Wait
    seq_num = 0

    while True:
        # ── Camada de Aplicação: lê mensagem do usuário ──
        try:
            texto = input(f"{nome}> ").strip()
        except (EOFError, KeyboardInterrupt):
            log("CLIENTE", "Encerrando...", AMARELO)
            break

        if not texto:
            continue

        payload = {
            "type"     : "CHAT",
            "sender"   : nome,
            "message"  : texto,
            "timestamp": datetime.now().isoformat()
        }

        # ── Camada de Transporte: encapsula no Segmento ──
        seg = Segmento(seq_num=seq_num, is_ack=False, payload=payload)
        seg_bytes = json.dumps(seg.to_dict()).encode("utf-8")

        tentativas = 0

        # ── Loop Stop-and-Wait: fica aqui até confirmar entrega ──
        while True:
            tentativas += 1
            log("TRANSPORTE",
                f"Enviando SEQ={seq_num} | Tentativa #{tentativas}",
                CIANO)

            # ── Camada Física: envia pelo canal ruidoso ──
            enviar_pela_rede_ruidosa(sock, seg_bytes, endereco_servidor)

            # ── Aguarda ACK ──
            try:
                ack_dados, _ = sock.recvfrom(BUFFER_SIZE)
                ack_dict = json.loads(ack_dados.decode("utf-8"))

                if ack_dict.get("is_ack") and ack_dict.get("seq_num") == seq_num:
                    # ACK correto → mensagem confirmada, avança sequência
                    log("TRANSPORTE",
                        f"✓ ACK {seq_num} recebido! Mensagem entregue com sucesso.",
                        VERDE)
                    seq_num = 1 - seq_num  # Alterna: 0→1 ou 1→0
                    break

                else:
                    # ACK com número errado (ex: ACK duplicado de mensagem anterior)
                    log("TRANSPORTE",
                        f"ACK inesperado (seq={ack_dict.get('seq_num')}) → retransmitindo...",
                        AMARELO)

            except socket.timeout:
                log("TRANSPORTE",
                    f"Timeout após {TIMEOUT_SEGUNDOS}s! Retransmitindo SEQ={seq_num}...",
                    AMARELO)

            except (json.JSONDecodeError, UnicodeDecodeError):
                log("TRANSPORTE",
                    "ACK corrompido recebido → retransmitindo...",
                    VERMELHO)

        print()  # Linha em branco para legibilidade


# ══════════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 50)
    print("  Mini-NET — Fase 2: Transporte (Stop-and-Wait)")
    print("=" * 50)

    modo = input("Modo (server / client): ").strip().lower()

    if modo == "server":
        porta = int(input("Porta do servidor: "))
        run_server(porta)

    elif modo == "client":
        ip_serv   = input("IP do servidor [127.0.0.1]: ").strip() or "127.0.0.1"
        porta_serv = int(input("Porta do servidor: "))
        nome      = input("Seu nome: ").strip()
        run_client(ip_serv, porta_serv, nome)

    else:
        print("Modo inválido. Use 'server' ou 'client'.")