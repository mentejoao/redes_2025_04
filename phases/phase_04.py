"""
phase_04.py - Fase 4: Camada de Enlace

Implementa (sobre a Fase 3):
  - Endereços MAC fictícios para cada host
  - Encapsulamento completo: Quadro → Pacote → Segmento → JSON
  - CRC32 (FCS) calculado e anexado pelo emissor (via Quadro.serializar())
  - Verificação de CRC no receptor (via Quadro.deserializar())
  - Quadro corrompido → descartado silenciosamente na Camada de Enlace
  - Camada de Transporte recupera a perda via timeout + retransmissão

Fluxo completo:
  Cliente → [Quadro(Pacote(Segmento(JSON)))] → Roteador → Servidor
  Servidor → [Quadro(Pacote(ACK))]           → Roteador → Cliente

Endereços MAC fictícios utilizados:
  HOST_A   → AA:AA:AA:AA:AA:01
  HOST_B   → BB:BB:BB:BB:BB:02
  SERVIDOR → CC:CC:CC:CC:CC:03
  ROTEADOR → DD:DD:DD:DD:DD:04  (usado pelo router.py)

Uso:
  python phase_04.py  →  escolha server ou client

Dependências: protocol.py e router.py (mesma pasta, router atualizado para Fase 4)
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
    Cliente com pilha completa (L7 → L2).
    Encapsula cada mensagem em Quadro com CRC antes de enviar.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", minha_porta))
    sock.settimeout(TIMEOUT_SEGUNDOS)

    endereco_roteador = (ip_roteador, porta_roteador)

    log("CLIENTE", f"VIP={meu_vip} | MAC={TABELA_MAC.get(meu_vip)} | Porta={minha_porta}", VERDE)
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

        # ── L7: Aplicação ──
        payload = {
            "type"     : "CHAT",
            "sender"   : nome,
            "message"  : texto,
            "timestamp": datetime.now().isoformat()
        }

        # ── L4 → L2: empilha camadas e calcula CRC ──
        seg       = Segmento(seq_num=seq_num, is_ack=False, payload=payload)
        quadro_bytes = construir_quadro(seg, src_vip=meu_vip, dst_vip=dst_vip)

        log("ENLACE",
            f"Quadro criado com CRC32 | MAC {TABELA_MAC.get(meu_vip)} → {TABELA_MAC.get('ROTEADOR')}",
            AZUL)
        log("REDE",   f"Pacote | {meu_vip} → {dst_vip} | TTL={TTL_INICIAL}", MAGENTA)
        log("TRANSPORTE", f"Segmento | SEQ={seq_num}", CIANO)

        tentativas = 0

        # ── Stop-and-Wait ──
        while True:
            tentativas += 1
            log("TRANSPORTE",
                f"Enviando SEQ={seq_num} via Roteador | Tentativa #{tentativas}",
                CIANO)

            enviar_pela_rede_ruidosa(sock, quadro_bytes, endereco_roteador)

            try:
                ack_bruto, _ = sock.recvfrom(BUFFER_SIZE)

                # ── L2: verifica CRC do ACK recebido ──
                ack_pkt_dict, ack_seg_dict = receber_quadro(ack_bruto, meu_vip)

                if ack_pkt_dict is None:
                    log("TRANSPORTE", "ACK com CRC inválido → retransmitindo...", VERMELHO)
                    continue

                # ── L3: confere destino ──
                if ack_pkt_dict.get("dst_vip") != meu_vip:
                    log("REDE", "ACK não endereçado a mim → ignorando", AMARELO)
                    continue

                # ── L4: confere número de sequência ──
                if ack_seg_dict.get("is_ack") and ack_seg_dict.get("seq_num") == seq_num:
                    log("TRANSPORTE",
                        f"✓ ACK {seq_num} recebido e íntegro! Mensagem entregue.",
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
    print("=" * 60)
    print("  Mini-NET — Fase 4: Enlace (MAC + CRC32)")
    print("  Pilha completa: Quadro → Pacote → Segmento → JSON")
    print("=" * 60)

    modo = input("Modo (server / client): ").strip().lower()

    ip_roteador    = input("IP do roteador  [127.0.0.1]: ").strip() or "127.0.0.1"
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