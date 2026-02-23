import socket
import json
import threading
from datetime import datetime

SERVER_IP = "127.0.0.1"
SERVER_PORT = 9000

MY_PORT = int(input("Minha porta local: "))
NAME = input("Seu nome: ")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("127.0.0.1", MY_PORT))


# ===== RECEBER =====
def listen():
    while True:
        data, addr = sock.recvfrom(4096)

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
