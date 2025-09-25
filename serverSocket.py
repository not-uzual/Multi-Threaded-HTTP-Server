import sys
import socket
import queue
import concurrent.futures

SERVER = '127.0.0.1'
PORT = 8080
THREADPOOL = 10
FORMAT = 'utf-8'

connection_que = queue.Queue()

for i in range(len(sys.argv)):
    if(i == 1):
        PORT = int(sys.argv[i])
    elif(i == 2):
        SERVER = sys.argv[i]
    elif(i == 3):
        THREADPOOL = int(sys.argv[i])
        
ADDR = (SERVER, PORT)

def handle_Client():
    
    while True:
        clientSocket, clientAddr = connection_que.get(block=True)
    
        print(f"[NEW CONNECTION] {clientAddr} connected")
        
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
    

def start_Server():
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.bind(ADDR)
    
    serverSocket.listen(50)
    print(f'[SERVER LISTENING] on {ADDR}')
    
    with concurrent.futures.ThreadPoolExecutor(max_workers = THREADPOOL) as executor:
        for _ in range(THREADPOOL):
            executor.submit(handle_Client)

        while True:
            clientSocket, clientAddr = serverSocket.accept()
            
            connection_que.put((clientSocket, clientAddr))
            
start_Server()