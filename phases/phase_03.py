"""
phase_03.py - Fase 3: Camada de Rede

Implementa (sobre a Fase 2):
  - Endereçamento virtual (VIP): HOST_A, HOST_B, SERVIDOR
  - Encapsulamento: Pacote envolve Segmento (Stop-and-Wait preservado)
  - Campo TTL (Time To Live): pacote descartado se TTL chegar a 0
  - Roteamento: cliente envia ao Roteador, nunca direto ao servidor
  - ACK também retorna pelo Roteador (caminho completo pelas camadas)

Fluxo completo:
  Cliente → [Segmento → Pacote] → Roteador → [Pacote] → Servidor
  Servidor → [ACK em Pacote]   → Roteador → [Pacote] → Cliente

Uso:
  Modo servidor  →  python phase_03.py server
  Modo cliente   →  python phase_03.py client

Dependência: protocol.py e router.py (mesma pasta)
"""

import socket
import json
import sys
from datetime import datetime
from protocol import Segmento, Pacote, enviar_pela_rede_ruidosa

# ──────────────────────────────────────────────
# CONFIGURAÇÕES
# ──────────────────────────────────────────────
TIMEOUT_SEGUNDOS = 3.0
BUFFER_SIZE      = 65535
TTL_INICIAL      = 8

# ──────────────────────────────────────────────
# CORES ANSI
# ──────────────────────────────────────────────
VERMELHO = "\033[91m"
AMARELO  = "\033[93m"
CIANO    = "\033[96m"
VERDE    = "\033[92m"
MAGENTA  = "\033[95m"
RESET    = "\033[0m"


def log(camada: str, msg: str, cor: str = ""):
    print(f"{cor}[{camada}] {msg}{RESET}")


# ══════════════════════════════════════════════════════════════════
# SERIALIZAÇÃO DE PACOTE
# ══════════════════════════════════════════════════════════════════
def empacotar(segmento: Segmento, src_vip: str, dst_vip: str) -> bytes:
    """Encapsula Segmento dentro de um Pacote e serializa para bytes."""
    pacote = Pacote(
        src_vip      = src_vip,
        dst_vip      = dst_vip,
        ttl          = TTL_INICIAL,
        segmento_dict = segmento.to_dict()
    )
    return json.dumps(pacote.to_dict()).encode("utf-8")


def desempacotar(dados_brutos: bytes):
    """
    Desserializa bytes para dicionário de Pacote.
    Retorna (pacote_dict, segmento_dict) ou (None, None) se corrompido.
    """
    try:
        pacote_dict = json.loads(dados_brutos.decode("utf-8"))
        segmento_dict = pacote_dict["data"]
        return pacote_dict, segmento_dict
    except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
        return None, None


# ══════════════════════════════════════════════════════════════════
# SERVIDOR
# ══════════════════════════════════════════════════════════════════
def run_server(minha_porta: int, meu_vip: str, ip_roteador: str, porta_roteador: int):
    """
    Servidor de chat com suporte a múltiplos clientes via Roteador.
    Recebe Pacotes, extrai Segmentos, envia ACK de volta pelo Roteador.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", minha_porta))

    log("SERVIDOR", f"VIP={meu_vip} | Porta real={minha_porta}", VERDE)
    log("SERVIDOR", f"Roteador em {ip_roteador}:{porta_roteador}", VERDE)
    log("SERVIDOR", "Aguardando mensagens...\n", VERDE)

    # Stop-and-Wait: sequência esperada por VIP de origem
    seq_esperado: dict[str, int] = {}

    while True:
        try:
            dados_brutos, _ = sock.recvfrom(BUFFER_SIZE)
        except Exception as e:
            log("SERVIDOR", f"Erro ao receber: {e}", VERMELHO)
            continue

        # ── Camada de Rede: desempacota Pacote ──
        pacote_dict, seg_dict = desempacotar(dados_brutos)

        if pacote_dict is None:
            log("REDE", "Pacote corrompido → descartado", VERMELHO)
            continue

        src_vip = pacote_dict.get("src_vip", "DESCONHECIDO")
        dst_vip = pacote_dict.get("dst_vip", "")
        ttl     = pacote_dict.get("ttl", 0)

        log("REDE",
            f"Pacote recebido | {src_vip} → {dst_vip} | TTL={ttl}",
            MAGENTA)

        # Verifica TTL
        if ttl <= 0:
            log("REDE", "TTL expirado → pacote descartado", VERMELHO)
            continue

        # Verifica se é para este servidor
        if dst_vip != meu_vip:
            log("REDE", f"Pacote não é para mim ({dst_vip} ≠ {meu_vip}) → ignorado", AMARELO)
            continue

        # ── Camada de Transporte: extrai Segmento ──
        try:
            seg = Segmento(
                seq_num = seg_dict["seq_num"],
                is_ack  = seg_dict["is_ack"],
                payload = seg_dict["payload"]
            )
        except (KeyError, TypeError):
            log("TRANSPORTE", "Segmento malformado → descartado", VERMELHO)
            continue

        if seg.is_ack:
            continue  # Servidor não processa ACKs recebidos

        log("TRANSPORTE",
            f"Segmento | SEQ={seg.seq_num} | Esperado={seq_esperado.get(src_vip, 0)}",
            CIANO)

        # ── Envia ACK pelo Roteador ──
        ack_seg    = Segmento(seq_num=seg.seq_num, is_ack=True, payload=None)
        ack_bytes  = empacotar(ack_seg, src_vip=meu_vip, dst_vip=src_vip)
        endereco_roteador = (ip_roteador, porta_roteador)

        log("TRANSPORTE", f"Enviando ACK {seg.seq_num} → Roteador → {src_vip}", CIANO)
        enviar_pela_rede_ruidosa(sock, ack_bytes, endereco_roteador)

        # ── Verifica duplicata ──
        esperado = seq_esperado.get(src_vip, 0)

        if seg.seq_num == esperado:
            payload   = seg.payload
            remetente = payload.get("sender", src_vip)
            mensagem  = payload.get("message", "")
            ts        = payload.get("timestamp", "")[:19]

            log("APLICAÇÃO", f"[{ts}] {remetente}: {mensagem}", VERDE)

            seq_esperado[src_vip] = 1 - esperado
        else:
            log("TRANSPORTE",
                f"Duplicata de {src_vip} (SEQ={seg.seq_num}) → descartada",
                AMARELO)

        print()


# ══════════════════════════════════════════════════════════════════
# CLIENTE
# ══════════════════════════════════════════════════════════════════
def run_client(
    minha_porta: int,
    meu_vip: str,
    ip_roteador: str,
    porta_roteador: int,
    dst_vip: str,
    nome: str
):
    """
    Cliente de chat. Envia Pacotes para o Roteador (nunca direto ao servidor).
    Aguarda ACK (que também volta pelo Roteador). Stop-and-Wait preservado.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", minha_porta))
    sock.settimeout(TIMEOUT_SEGUNDOS)

    endereco_roteador = (ip_roteador, porta_roteador)

    log("CLIENTE", f"VIP={meu_vip} | Porta real={minha_porta}", VERDE)
    log("CLIENTE", f"Destino={dst_vip} via Roteador {ip_roteador}:{porta_roteador}", VERDE)
    log("CLIENTE", f"Logado como '{nome}'. Digite sua mensagem.\n", VERDE)

    seq_num = 0

    while True:
        try:
            texto = input(f"{nome}> ").strip()
        except (EOFError, KeyboardInterrupt):
            log("CLIENTE", "Encerrando...", AMARELO)
            break

        if not texto:
            continue

        # ── Camada de Aplicação: monta payload ──
        payload = {
            "type"     : "CHAT",
            "sender"   : nome,
            "message"  : texto,
            "timestamp": datetime.now().isoformat()
        }

        # ── Camada de Transporte: cria Segmento ──
        seg = Segmento(seq_num=seq_num, is_ack=False, payload=payload)

        # ── Camada de Rede: encapsula em Pacote ──
        pkt_bytes = empacotar(seg, src_vip=meu_vip, dst_vip=dst_vip)

        log("REDE",
            f"Pacote criado | {meu_vip} → {dst_vip} | TTL={TTL_INICIAL} | SEQ={seq_num}",
            MAGENTA)

        tentativas = 0

        # ── Stop-and-Wait ──
        while True:
            tentativas += 1
            log("TRANSPORTE",
                f"Enviando SEQ={seq_num} via Roteador | Tentativa #{tentativas}",
                CIANO)

            enviar_pela_rede_ruidosa(sock, pkt_bytes, endereco_roteador)

            # Aguarda ACK (que volta como Pacote pelo Roteador)
            try:
                ack_bruto, _ = sock.recvfrom(BUFFER_SIZE)
                ack_pkt_dict, ack_seg_dict = desempacotar(ack_bruto)

                if ack_pkt_dict is None:
                    log("TRANSPORTE", "ACK corrompido → retransmitindo...", VERMELHO)
                    continue

                ack_dst = ack_pkt_dict.get("dst_vip", "")
                if ack_dst != meu_vip:
                    log("REDE", f"Pacote não é para mim ({ack_dst}) → ignorando", AMARELO)
                    continue

                if (ack_seg_dict.get("is_ack") and
                        ack_seg_dict.get("seq_num") == seq_num):
                    log("TRANSPORTE",
                        f"✓ ACK {seq_num} recebido! Mensagem entregue.",
                        VERDE)
                    seq_num = 1 - seq_num
                    break
                else:
                    log("TRANSPORTE",
                        f"ACK inesperado (seq={ack_seg_dict.get('seq_num')}) → retransmitindo...",
                        AMARELO)

            except socket.timeout:
                log("TRANSPORTE",
                    f"Timeout após {TIMEOUT_SEGUNDOS}s → retransmitindo SEQ={seq_num}...",
                    AMARELO)

            except (json.JSONDecodeError, UnicodeDecodeError):
                log("TRANSPORTE", "ACK ilegível → retransmitindo...", VERMELHO)

        print()


# ══════════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 55)
    print("  Mini-NET — Fase 3: Rede (Endereçamento + Roteamento)")
    print("=" * 55)

    modo = input("Modo (server / client): ").strip().lower()

    ip_roteador   = input("IP do roteador  [127.0.0.1]: ").strip() or "127.0.0.1"
    porta_roteador = int(input("Porta do roteador: "))

    if modo == "server":
        minha_porta = int(input("Minha porta real: "))
        meu_vip     = input("Meu VIP [SERVIDOR]: ").strip() or "SERVIDOR"
        run_server(minha_porta, meu_vip, ip_roteador, porta_roteador)

    elif modo == "client":
        minha_porta = int(input("Minha porta real: "))
        meu_vip     = input("Meu VIP (ex: HOST_A): ").strip()
        dst_vip     = input("VIP destino [SERVIDOR]: ").strip() or "SERVIDOR"
        nome        = input("Seu nome: ").strip()
        run_client(minha_porta, meu_vip, ip_roteador, porta_roteador, dst_vip, nome)

    else:
        print("Modo inválido. Use 'server' ou 'client'.")
