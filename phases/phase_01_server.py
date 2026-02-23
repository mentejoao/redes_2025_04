import socket
import json
from datetime import datetime

SERVER_IP = "127.0.0.1"
SERVER_PORT = 9000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((SERVER_IP, SERVER_PORT))

print(f"[SERVIDOR] Rodando em {SERVER_IP}:{SERVER_PORT}")

clientes = set()  # (ip, porta)


while True:
    data, addr = sock.recvfrom(4096)

    try:
        msg = json.loads(data.decode())
    except:
        print("[ERRO] pacote inválido")
        continue

    # registra cliente automaticamente
    clientes.add(addr)

    print(
        f"[{msg['timestamp']}] "
        f"{msg['sender']}@{addr}: {msg['message']}"
    )

    # broadcast para todos exceto quem enviou
    for cliente in clientes:
        if cliente != addr:
            sock.sendto(data, cliente)
