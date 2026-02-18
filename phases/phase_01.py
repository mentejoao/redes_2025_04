import socket
import json
import threading
from datetime import datetime

# ===== CONFIGURAÇÃO =====
MY_IP = "127.0.0.1"
MY_PORT = int(input("Minha porta: "))

PEERS = []  # lista de (ip, porta)

print("Informe peers no formato ip:porta (vazio para terminar)")
while True:
    p = input("> ")
    if not p:
        break
    ip, port = p.split(":")
    PEERS.append((ip, int(port)))

NAME = input("Seu nome: ")

# ===== SOCKET UDP =====
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((MY_IP, MY_PORT))


# ===== RECEBER MENSAGENS =====
def listen():
    while True:
        data, addr = sock.recvfrom(4096)
        try:
            msg = json.loads(data.decode())
            print(
                f"\n[{msg['timestamp']}] "
                f"{msg['sender']}@{addr[0]}:{addr[1]}: "
                f"{msg['message']}"
            )
        except json.JSONDecodeError:
            print(f"[ERRO] Mensagem inválida de {addr}")


# ===== ENVIAR MENSAGENS =====
def send_messages():
    while True:
        text = input()
        payload = {
            "type": "CHAT",
            "sender": NAME,
            "message": text,
            "timestamp": datetime.now().isoformat()
        }

        data = json.dumps(payload).encode()

        for peer in PEERS:
            sock.sendto(data, peer)


# ===== START =====
threading.Thread(target=listen, daemon=True).start()
send_messages()
