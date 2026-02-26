"""
server.py - Servidor da Fase 4: Camada de Enlace

Implementa a pilha completa (L7 -> L2) e recebe mensagens.
"""

import socket
import json
from datetime import datetime
from protocol import Segmento, Pacote, Quadro, enviar_pela_rede_ruidosa

# ──────────────────────────────────────────────
# CONFIGURAÇÕES
# ──────────────────────────────────────────────
TIMEOUT_SEGUNDOS = 3.0
BUFFER_SIZE      = 65535
TTL_INICIAL      = 8

# Tabela de MACs fictícios (ARP simulado — estático)
TABELA_MAC = {
    "HOST_A"  : "AA:AA:AA:AA:AA:01",
    "HOST_B"  : "BB:BB:BB:BB:BB:02",
    "SERVIDOR": "CC:CC:CC:CC:CC:03",
    "ROTEADOR": "DD:DD:DD:DD:DD:04",
}

# ──────────────────────────────────────────────
# CORES ANSI
# ──────────────────────────────────────────────
VERMELHO = "\033[91m"
AMARELO  = "\033[93m"
CIANO    = "\033[96m"
VERDE    = "\033[92m"
MAGENTA  = "\033[95m"
AZUL     = "\033[94m"
RESET    = "\033[0m"


def log(camada: str, msg: str, cor: str = ""):
    print(f"{cor}[{camada}] {msg}{RESET}")


# ══════════════════════════════════════════════════════════════════
# HELPERS DE EMPACOTAMENTO / DESEMPACOTAMENTO
# ══════════════════════════════════════════════════════════════════
def construir_quadro(segmento: Segmento, src_vip: str, dst_vip: str) -> bytes:
    """
    Empilha todas as camadas e serializa com CRC:
      Segmento → Pacote → Quadro.serializar()
    O MAC de destino sempre aponta para o Roteador (próximo salto).
    """
    # Camada 4 → 3: envolve Segmento em Pacote
    pacote = Pacote(
        src_vip       = src_vip,
        dst_vip       = dst_vip,
        ttl           = TTL_INICIAL,
        segmento_dict = segmento.to_dict()
    )

    # Camada 3 → 2: envolve Pacote em Quadro com MACs
    src_mac = TABELA_MAC.get(src_vip, "00:00:00:00:00:00")
    dst_mac = TABELA_MAC.get("ROTEADOR")   # próximo salto é sempre o roteador

    quadro = Quadro(src_mac=src_mac, dst_mac=dst_mac, pacote_dict=pacote.to_dict())

    # serializar() calcula e embute o CRC32 automaticamente
    return quadro.serializar()


def receber_quadro(dados_brutos: bytes, meu_vip: str):
    """
    Desserializa bytes e verifica CRC (Camada de Enlace).
    Retorna (pacote_dict, segmento_dict) ou (None, None) se inválido.
    """
    quadro_dict, integro = Quadro.deserializar(dados_brutos)

    if quadro_dict is None:
        log("ENLACE", "Quadro destruído (JSON inválido) → descartado", VERMELHO)
        return None, None

    if not integro:
        log("ENLACE",
            f"Erro de CRC detectado! Quadro corrompido → descartado silenciosamente",
            VERMELHO)
        return None, None

    log("ENLACE",
        f"CRC OK ✓ | {quadro_dict['src_mac']} → {quadro_dict['dst_mac']}",
        AZUL)

    try:
        pacote_dict   = quadro_dict["data"]
        segmento_dict = pacote_dict["data"]
        return pacote_dict, segmento_dict
    except KeyError:
        log("ENLACE", "Estrutura do quadro inválida → descartado", VERMELHO)
        return None, None


# ══════════════════════════════════════════════════════════════════
# SERVIDOR
# ══════════════════════════════════════════════════════════════════
def run_server(minha_porta: int, meu_vip: str, ip_roteador: str, porta_roteador: int):
    """
    Servidor com pilha completa (L2 → L7).
    Verifica CRC antes de qualquer processamento.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", minha_porta))

    log("SERVIDOR", f"VIP={meu_vip} | MAC={TABELA_MAC.get(meu_vip)} | Porta={minha_porta}", VERDE)
    log("SERVIDOR", f"Roteador em {ip_roteador}:{porta_roteador}", VERDE)
    log("SERVIDOR", "Aguardando mensagens...\n", VERDE)

    seq_esperado: dict[str, int] = {}
    endereco_roteador = (ip_roteador, porta_roteador)

    while True:
        try:
            dados_brutos, _ = sock.recvfrom(BUFFER_SIZE)
        except Exception as e:
            log("SERVIDOR", f"Erro ao receber: {e}", VERMELHO)
            continue

        # ── L2: Enlace — verifica CRC ──
        pacote_dict, seg_dict = receber_quadro(dados_brutos, meu_vip)
        if pacote_dict is None:
            # CRC falhou → descarta. O timeout do cliente retransmitirá.
            print()
            continue

        # ── L3: Rede — verifica endereço e TTL ──
        src_vip = pacote_dict.get("src_vip", "?")
        dst_vip = pacote_dict.get("dst_vip", "?")
        ttl     = pacote_dict.get("ttl", 0)

        log("REDE", f"Pacote | {src_vip} → {dst_vip} | TTL={ttl}", MAGENTA)

        if ttl <= 0:
            log("REDE", "TTL expirado → descartado", VERMELHO)
            continue

        if dst_vip != meu_vip:
            log("REDE", f"Pacote não é para mim ({dst_vip} ≠ {meu_vip}) → ignorado", AMARELO)
            continue

        # ── L4: Transporte — extrai Segmento ──
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
            continue

        log("TRANSPORTE",
            f"Segmento | SEQ={seg.seq_num} | Esperado={seq_esperado.get(src_vip, 0)}",
            CIANO)

        # ── L4: Envia ACK de volta (encapsulado em Quadro) ──
        ack_seg   = Segmento(seq_num=seg.seq_num, is_ack=True, payload=None)
        ack_bytes = construir_quadro(ack_seg, src_vip=meu_vip, dst_vip=src_vip)

        log("TRANSPORTE", f"Enviando ACK {seg.seq_num} → Roteador → {src_vip}", CIANO)
        enviar_pela_rede_ruidosa(sock, ack_bytes, endereco_roteador)

        # ── L7: Aplicação — exibe mensagem (se não for duplicata) ──
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


if __name__ == "__main__":
    print("=" * 60)
    print("  Mini-NET — SERVIDOR")
    print("=" * 60)

    try:
        minha_porta = int(input("Minha porta real: "))
        meu_vip     = input("Meu VIP [SERVIDOR]: ").strip() or "SERVIDOR"
        
        ip_roteador    = input("IP do roteador  [127.0.0.1]: ").strip() or "127.0.0.1"
        porta_roteador = int(input("Porta do roteador: "))
        
        run_server(minha_porta, meu_vip, ip_roteador, porta_roteador)
    except KeyboardInterrupt:
        print("\nEncerrado.")
    except ValueError:
        print("\nValores inválidos.")
