"""
router.py - Atualizado para Fase 4: Roteador com suporte a Quadros (Enlace)

Responsabilidades:
  - Receber Quadros (L2) e verificar CRC — descarta se corrompido
  - Extrair o Pacote (L3), ler dst_vip e decrementar TTL
  - Re-encapsular em novo Quadro com MACs atualizados (roteador → destino)
  - Encaminhar pelo canal ruidoso

O Roteador opera na fronteira L2/L3:
  → Consome o Quadro antigo (verifica CRC)
  → Lê o cabeçalho de Rede (dst_vip, TTL)
  → Gera um novo Quadro para o próximo salto

Uso:
  python router.py

Dependência: protocol.py (mesma pasta)
"""

import socket
import json
from protocol import Quadro, enviar_pela_rede_ruidosa

# ──────────────────────────────────────────────
# CORES ANSI
# ──────────────────────────────────────────────
VERMELHO = "\033[91m"
AMARELO  = "\033[93m"
AZUL     = "\033[94m"
VERDE    = "\033[92m"
MAGENTA  = "\033[95m"
RESET    = "\033[0m"

BUFFER_SIZE = 65535

# MAC do roteador (origem dos quadros que ele gera)
MAC_ROTEADOR = "DD:DD:DD:DD:DD:04"

# Tabela de MACs fictícios dos hosts (para montar dst_mac do novo quadro)
TABELA_MAC = {
    "HOST_A"  : "AA:AA:AA:AA:AA:01",
    "HOST_B"  : "BB:BB:BB:BB:BB:02",
    "SERVIDOR": "CC:CC:CC:CC:CC:03",
}


def log(camada: str, msg: str, cor: str = ""):
    print(f"{cor}[{camada}] {msg}{RESET}")


# ══════════════════════════════════════════════════════════════════
# TABELA DE ROTEAMENTO ESTÁTICA
# ══════════════════════════════════════════════════════════════════
tabela_roteamento: dict[str, tuple[str, int]] = {}


def configurar_tabela():
    print(f"\n{AZUL}{'─'*50}")
    print("  Configuração da Tabela de Roteamento Estática")
    print(f"{'─'*50}{RESET}")
    print("Formato:  VIP  IP  PORTA")
    print("Exemplo:  HOST_A 127.0.0.1 5001")
    print("          HOST_B 127.0.0.1 5002")
    print("          SERVIDOR 127.0.0.1 5003")
    print("Vazio para encerrar.\n")

    while True:
        entrada = input("Rota> ").strip()
        if not entrada:
            break
        partes = entrada.split()
        if len(partes) != 3:
            print("  Formato inválido. Use: VIP IP PORTA")
            continue
        vip, ip, porta = partes
        try:
            tabela_roteamento[vip] = (ip, int(porta))
            log("ROTEADOR", f"Rota adicionada: {vip} → {ip}:{porta}", VERDE)
        except ValueError:
            print("  Porta inválida.")

    if not tabela_roteamento:
        print(f"{VERMELHO}Nenhuma rota cadastrada!{RESET}")
    else:
        print(f"\n{AZUL}Tabela de Roteamento:{RESET}")
        for vip, (ip, porta) in tabela_roteamento.items():
            print(f"  {vip:20s} → {ip}:{porta}")
        print()


# ══════════════════════════════════════════════════════════════════
# ROTEADOR
# ══════════════════════════════════════════════════════════════════
def run_router(minha_porta: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", minha_porta))

    log("ROTEADOR", f"MAC={MAC_ROTEADOR} | Porta={minha_porta}", VERDE)
    log("ROTEADOR", "Aguardando quadros...\n", VERDE)

    while True:
        try:
            dados_brutos, endereco_origem = sock.recvfrom(BUFFER_SIZE)
        except Exception as e:
            log("ROTEADOR", f"Erro ao receber: {e}", VERMELHO)
            continue

        # ── L2: Enlace — desserializa e verifica CRC ──
        quadro_dict, integro = Quadro.deserializar(dados_brutos)

        if quadro_dict is None:
            log("ENLACE", "Quadro destruído (JSON inválido) → descartado", VERMELHO)
            print()
            continue

        if not integro:
            log("ENLACE",
                "Erro de CRC! Quadro corrompido → descartado silenciosamente",
                VERMELHO)
            # Não reenvia nada — o timeout do emissor original tratará isso
            print()
            continue

        log("ENLACE",
            f"CRC OK ✓ | {quadro_dict['src_mac']} → {quadro_dict['dst_mac']} | De: {endereco_origem}",
            AZUL)

        # ── L3: Rede — lê cabeçalho do Pacote ──
        try:
            pacote_dict = quadro_dict["data"]
            src_vip = pacote_dict["src_vip"]
            dst_vip = pacote_dict["dst_vip"]
            ttl     = pacote_dict["ttl"]
        except KeyError:
            log("REDE", "Pacote malformado dentro do quadro → descartado", VERMELHO)
            print()
            continue

        is_ack   = pacote_dict.get("data", {}).get("is_ack", False)
        tipo_str = "ACK" if is_ack else "DATA"

        log("REDE",
            f"Pacote [{tipo_str}] | {src_vip} → {dst_vip} | TTL={ttl}",
            MAGENTA)

        # Verifica TTL
        if ttl <= 0:
            log("REDE", f"TTL expirado → pacote descartado", VERMELHO)
            print()
            continue

        # Decrementa TTL
        pacote_dict["ttl"] = ttl - 1
        log("REDE", f"TTL decrementado: {ttl} → {ttl - 1}", MAGENTA)

        # Consulta tabela de roteamento
        if dst_vip not in tabela_roteamento:
            log("REDE",
                f"Destino '{dst_vip}' não encontrado na tabela → descartado",
                VERMELHO)
            print()
            continue

        ip_destino, porta_destino = tabela_roteamento[dst_vip]
        log("REDE", f"Rota: {dst_vip} → {ip_destino}:{porta_destino}", AZUL)

        # ── L2: Re-encapsula em novo Quadro com MACs do próximo salto ──
        dst_mac  = TABELA_MAC.get(dst_vip, "FF:FF:FF:FF:FF:FF")
        novo_quadro = Quadro(
            src_mac     = MAC_ROTEADOR,
            dst_mac     = dst_mac,
            pacote_dict = pacote_dict
        )
        quadro_bytes = novo_quadro.serializar()  # Recalcula CRC para o novo quadro

        log("ENLACE",
            f"Novo quadro gerado com CRC32 | {MAC_ROTEADOR} → {dst_mac}",
            AZUL)

        # ── L1: Encaminha pelo canal ruidoso ──
        log("REDE", f"Encaminhando para {ip_destino}:{porta_destino}...", AZUL)
        enviar_pela_rede_ruidosa(sock, quadro_bytes, (ip_destino, porta_destino))

        log("REDE", "Quadro encaminhado.\n", VERDE)


# ══════════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 55)
    print("  Mini-NET — Roteador (Fase 4: Enlace + Rede)")
    print("=" * 55)

    minha_porta = int(input("Porta do roteador: "))
    configurar_tabela()
    run_router(minha_porta)
