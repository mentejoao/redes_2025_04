"""
router.py - Fase 3: Roteador da Camada de Rede

Responsabilidades:
  - Receber Pacotes de qualquer host (clientes ou servidor)
  - Ler o campo dst_vip (endereço virtual de destino)
  - Consultar a Tabela de Roteamento Estática
  - Decrementar o TTL (descartar se TTL <= 0)
  - Encaminhar o Pacote para o IP/Porta real correto

O Roteador é TRANSPARENTE à camada de Transporte:
  ele não lê, não modifica e não gera Segmentos.
  Apenas opera sobre o cabeçalho do Pacote (Camada 3).

Uso:
  python router.py

Dependência: protocol.py (mesma pasta)
"""

import socket
import json
from protocol import enviar_pela_rede_ruidosa

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


def log(camada: str, msg: str, cor: str = ""):
    print(f"{cor}[{camada}] {msg}{RESET}")


# ══════════════════════════════════════════════════════════════════
# TABELA DE ROTEAMENTO ESTÁTICA
# ══════════════════════════════════════════════════════════════════
# Formato: { "VIP_DESTINO": ("ip_real", porta_real) }
# Preenchida dinamicamente na inicialização do roteador.

tabela_roteamento: dict[str, tuple[str, int]] = {}


def configurar_tabela():
    """
    Permite ao operador cadastrar as rotas estáticas no início.
    """
    print(f"\n{AZUL}{'─'*50}")
    print("  Configuração da Tabela de Roteamento Estática")
    print(f"{'─'*50}{RESET}")
    print("Cadastre as rotas no formato:  VIP  IP  PORTA")
    print("Exemplo:  HOST_A 127.0.0.1 5001")
    print("          HOST_B 127.0.0.1 5002")
    print("          SERVIDOR 127.0.0.1 5003")
    print("Digite vazio para encerrar.\n")

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
        print(f"{VERMELHO}Nenhuma rota cadastrada! O roteador não conseguirá encaminhar nada.{RESET}")
    else:
        print(f"\n{AZUL}Tabela de Roteamento:{RESET}")
        for vip, (ip, porta) in tabela_roteamento.items():
            print(f"  {vip:20s} → {ip}:{porta}")
        print()


# ══════════════════════════════════════════════════════════════════
# ROTEADOR
# ══════════════════════════════════════════════════════════════════
def run_router(minha_porta: int):
    """
    Loop principal do Roteador.
    Recebe Pacotes, processa o cabeçalho de rede e encaminha.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", minha_porta))

    log("ROTEADOR", f"Operando na porta {minha_porta}", VERDE)
    log("ROTEADOR", "Aguardando pacotes...\n", VERDE)

    while True:
        try:
            dados_brutos, endereco_origem = sock.recvfrom(BUFFER_SIZE)
        except Exception as e:
            log("ROTEADOR", f"Erro ao receber: {e}", VERMELHO)
            continue

        # ── Camada de Rede: lê cabeçalho do Pacote ──
        try:
            pacote_dict = json.loads(dados_brutos.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            log("REDE", "Pacote ilegível (corrupção grave) → descartado", VERMELHO)
            continue

        src_vip = pacote_dict.get("src_vip", "?")
        dst_vip = pacote_dict.get("dst_vip", "?")
        ttl     = pacote_dict.get("ttl", 0)
        is_ack  = pacote_dict.get("data", {}).get("is_ack", False)

        tipo_str = "ACK" if is_ack else "DATA"

        log("REDE",
            f"Pacote [{tipo_str}] | {src_vip} → {dst_vip} | TTL={ttl} | De: {endereco_origem}",
            MAGENTA)

        # ── Verifica TTL ──
        if ttl <= 0:
            log("REDE",
                f"TTL expirado para pacote {src_vip}→{dst_vip} → descartado",
                VERMELHO)
            continue

        # ── Decrementa TTL ──
        pacote_dict["ttl"] = ttl - 1
        log("REDE", f"TTL decrementado: {ttl} → {ttl - 1}", MAGENTA)

        # ── Consulta tabela de roteamento ──
        if dst_vip not in tabela_roteamento:
            log("REDE",
                f"Destino '{dst_vip}' não encontrado na tabela → pacote descartado",
                VERMELHO)
            continue

        ip_destino, porta_destino = tabela_roteamento[dst_vip]
        log("REDE",
            f"Rota encontrada: {dst_vip} → {ip_destino}:{porta_destino}",
            AZUL)

        # ── Encaminha o Pacote (com TTL atualizado) ──
        pacote_atualizado = json.dumps(pacote_dict).encode("utf-8")

        log("REDE",
            f"Encaminhando para {ip_destino}:{porta_destino}...",
            AZUL)

        enviar_pela_rede_ruidosa(sock, pacote_atualizado, (ip_destino, porta_destino))

        log("REDE", "Pacote encaminhado.\n", VERDE)


# ══════════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 55)
    print("  Mini-NET — Fase 3: Roteador (Camada de Rede)")
    print("=" * 55)

    minha_porta = int(input("Porta do roteador: "))

    configurar_tabela()

    run_router(minha_porta)