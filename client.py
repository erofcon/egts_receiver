import socket

sock = socket.socket()
sock.connect(('localhost', 5162))

while True:
    z = input()

    s = bytes.fromhex(str(z))
    print(s)
    sock.send(s)

# sock.close()
