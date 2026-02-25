"""
phase_01.py

Sistema de chat utilizando arquitetura Cliente-Servidor sobre UDP.

Arquitetura:
    Clientes  --->  Servidor  ---> Broadcast para clientes

Execução:
    python phase_01.py server
    python phase_01.py client
"""

import socket
import json
import threading
import sys
from datetime import datetime

SERVER_IP = "127.0.0.1"
SERVER_PORT = 9000


# =====================================================
# ==================== SERVIDOR =======================
# =====================================================
def run_server():
    """
    Servidor UDP central.

    Responsabilidades:
    - Receber mensagens dos clientes
    - Registrar automaticamente novos clientes
    - Exibir mensagens recebidas
    - Reenviar mensagens para todos os demais clientes
      (broadcast)

    Observação:
    UDP é connectionless, portanto o servidor mantém
    manualmente uma lista de clientes ativos.
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))

    print(f"[SERVIDOR] Rodando em {SERVER_IP}:{SERVER_PORT}")

    # Armazena (IP, porta) dos clientes conhecidos
    clientes = set()

    while True:
        # Aguarda datagramas UDP
        data, addr = sock.recvfrom(4096)

        try:
            # Decodifica mensagem da camada de aplicação (JSON)
            msg = json.loads(data.decode())
        except json.JSONDecodeError:
            print("[ERRO] pacote inválido recebido")
            continue

        # Verifica o tipo de mensagem
        msg_type = msg.get("type", "CHAT")

        if msg_type == "JOIN":
            # Mensagem de registro - adiciona cliente
            clientes.add(addr)
            print(
                f"[REGISTRO] {msg['sender']}@{addr[0]}:{addr[1]} "
                f"entrou no chat"
            )
            # Não faz broadcast de mensagens JOIN

        else:
            # Registra cliente (caso ainda não esteja)
            clientes.add(addr)

            # Exibe mensagem no servidor
            print(
                f"[{msg['timestamp']}] "
                f"{msg['sender']}@{addr[0]}:{addr[1]}: "
                f"{msg['message']}"
            )

            # Broadcast: envia para todos exceto remetente
            for cliente in clientes:
                if cliente != addr:
                    sock.sendto(data, cliente)


# =====================================================
# ===================== CLIENTE =======================
# =====================================================
def run_client():
    """
    Cliente do chat.

    Responsabilidades:
    - Capturar entrada do usuário
    - Enviar mensagens ao servidor
    - Receber mensagens broadcastadas
    - Exibir mensagens em tempo real

    Utiliza duas threads:
        1) Thread principal → envio
        2) Thread secundária → recepção
    """

    NAME = input("Seu nome: ")

    # Tenta vincular a porta com retry em caso de erro
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    while True:
        try:
            MY_PORT = int(input("Minha porta local: "))
            sock.bind(("127.0.0.1", MY_PORT))
            print("[CLIENTE] Conectado ao servidor.")
            break  # Sucesso, sai do loop
        except OSError as e:
            if e.errno == 98 or e.errno == 48:  # Address already in use (Linux/Mac)
                print(f"[ERRO] Porta {MY_PORT} já está em uso. Tente outra porta.")
            elif e.errno == 10048:  # Address already in use (Windows)
                print(f"[ERRO] Porta {MY_PORT} já está em uso. Tente outra porta.")
            else:
                print(f"[ERRO] Não foi possível vincular à porta {MY_PORT}: {e}")
        except ValueError:
            print("[ERRO] Por favor, digite um número de porta válido.")

    # -------------------------------------------------
    # THREAD DE RECEPÇÃO
    # -------------------------------------------------
    def listen():
        """
        Escuta continuamente mensagens vindas do servidor.

        Executa em paralelo ao envio para permitir
        comunicação bidirecional em tempo real.
        """
        while True:
            try:
                data, _ = sock.recvfrom(4096)
                msg = json.loads(data.decode())

                print(
                    f"\n[{msg['timestamp']}] "
                    f"{msg['sender']}: {msg['message']}"
                )

            except json.JSONDecodeError:
                print("\n[ERRO] mensagem corrompida")

    # Inicia thread daemon (encerra junto com o programa)
    threading.Thread(target=listen, daemon=True).start()

    # -------------------------------------------------
    # HANDSHAKE: Envia mensagem JOIN para registro
    # -------------------------------------------------
    join_payload = {
        "type": "JOIN",
        "sender": NAME,
        "message": "",
        "timestamp": datetime.now().isoformat()
    }
    sock.sendto(
        json.dumps(join_payload).encode(),
        (SERVER_IP, SERVER_PORT)
    )
    print(f"[SISTEMA] Registrado no servidor como '{NAME}'")

    # -------------------------------------------------
    # LOOP DE ENVIO (THREAD PRINCIPAL)
    # -------------------------------------------------
    while True:
        text = input()

        payload = {
            "type": "CHAT",
            "sender": NAME,
            "message": text,
            "timestamp": datetime.now().isoformat()
        }

        # Envia datagrama UDP ao servidor
        sock.sendto(
            json.dumps(payload).encode(),
            (SERVER_IP, SERVER_PORT)
        )


# =====================================================
# ====================== MAIN =========================
# =====================================================
def print_usage():
    print("Uso:")
    print("  python phase_01.py server")
    print("  python phase_01.py client")


"""
Ponto de entrada do programa.

O modo de operação é definido por argumento
de linha de comando, permitindo que o mesmo
arquivo atue como servidor ou cliente.
"""
if __name__ == "__main__":

    if len(sys.argv) != 2:
        print_usage()
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "server":
        run_server()

    elif mode == "client":
        run_client()

    else:
        print("Modo inválido.\n")
        print_usage()
