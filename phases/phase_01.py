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
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))

    print(f"[SERVIDOR] Rodando em {SERVER_IP}:{SERVER_PORT}")

    clientes = set()

    while True:
        data, addr = sock.recvfrom(4096)

        try:
            msg = json.loads(data.decode())
        except:
            print("[ERRO] pacote inválido")
            continue

        clientes.add(addr)

        print(
            f"[{msg['timestamp']}] "
            f"{msg['sender']}@{addr[0]}:{addr[1]}: "
            f"{msg['message']}"
        )

        # broadcast
        for cliente in clientes:
            if cliente != addr:
                sock.sendto(data, cliente)


# =====================================================
# ===================== CLIENTE =======================
# =====================================================
def run_client():
    MY_PORT = int(input("Minha porta local: "))
    NAME = input("Seu nome: ")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", MY_PORT))

    # ===== RECEBER =====
    def listen():
        while True:
            data, _ = sock.recvfrom(4096)

            try:
                msg = json.loads(data.decode())
                print(
                    f"\n[{msg['timestamp']}] "
                    f"{msg['sender']}: {msg['message']}"
                )
            except:
                print("[ERRO] mensagem inválida")

    # ===== ENVIAR =====
    def send_messages():
        while True:
            text = input()

            payload = {
                "type": "CHAT",
                "sender": NAME,
                "message": text,
                "timestamp": datetime.now().isoformat()
            }

            sock.sendto(
                json.dumps(payload).encode(),
                (SERVER_IP, SERVER_PORT)
            )

    threading.Thread(target=listen, daemon=True).start()
    send_messages()


# =====================================================
# ====================== MAIN =========================
# =====================================================
def print_usage():
    print("Uso:")
    print("  python chat.py server")
    print("  python chat.py client")


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
