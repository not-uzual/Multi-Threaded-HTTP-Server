import sys
import socket

SERVER = '127.0.0.1'
PORT = 8080
THREADPOOL = 10
FORMAT = 'utf-8'

for i in range(len(sys.argv)):
    if(i == 1):
        PORT = int(sys.argv[i])
    elif(i == 2):
        SERVER = sys.argv[i]
    elif(i == 3):
        THREADPOOL = int(sys.argv[i])
        
ADDR = (SERVER, PORT)

serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSocket.bind(ADDR)

serverSocket.listen(50)
print(f'Server is listening on {ADDR}')

while True:
    clientSocket, addr = serverSocket.accept()
    print(f'Client accepted on {addr}')
    
    msg = clientSocket.recv(1024)
    
    with open('index.html', 'r') as file:
        http_content = file.read()
    
    http_header = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html\r\n"
        f"Content-Length: {len(http_content)}\r\n"
        "\r\n"
    )
    
    http_response = http_header + http_content
    
    clientSocket.send(http_response.encode(FORMAT))
    clientSocket.close()
    
    print("Client socket closed")
    
    
    
