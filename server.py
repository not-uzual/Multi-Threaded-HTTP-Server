import sys
import socket
import queue
import threading
import concurrent.futures
import os
from datetime import datetime, timezone

class server:
    _SERVER = '127.0.0.1'
    _PORT = 8080
    _THREADPOOL = 10
    _FORMAT = 'utf-8'
    
    def __init__(self):
        try:
            if len(sys.argv) > 1:
                self._PORT = int(sys.argv[1]) #who knows if it is something else
            if len(sys.argv) > 2:
                self._SERVER = sys.argv[2]
            if len(sys.argv) > 3:
                self._THREADPOOL = int(sys.argv[3])
        except  ValueError as e:
            print(f"Oops! Something went wrong with your arguments: {e}")
            sys.exit(1)
        
        self._ADDR = (self._SERVER, self._PORT)
        
        self._connection_que = queue.Queue()
        self._thread_semaphore = threading.Semaphore(self._THREADPOOL)
        self._print_lock = threading.Lock()    
    
    def log_message(self, message):
        with self._print_lock:
            print(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {message}")
            print()
            
            
    def create_Response(self, req_method, resource_path):
        if req_method == 'GET':
            if resource_path == '/' or resource_path.split('.')[1] == 'html':
                resource_path = 'index.html'
                
                path = os.path.join('.', 'resources' ,resource_path)
                self.log_message(f'path i got::: {path}')
                
                try:
                    with open(path, 'r') as file:
                        http_content = file.read()
                except FileNotFoundError:
                    http_content = "<html><body><p>File not found</p></body></html>"
                    self.log_message("[ERROR] file not found!")
                    
                http_header = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html\r\n"
                    f"Content-Length: {len(http_content)}\r\n"
                    "charset=utf-8\r\n"
                    "\r\n"
                )
                
                http_response = http_header + http_content
                return http_response.encode(self._FORMAT)
            
            elif resource_path.split('.')[1] in ['png', 'jpg', 'txt']:
                path = os.path.join('.', 'resources', resource_path)
                try:
                    if resource_path.split('.')[1] == 'txt':
                        with open(path, 'r') as file:
                            http_content = file.read()
                            http_content = http_content.encode(self._FORMAT) 
                    else:
                        with open(path, 'rb') as file:
                            http_content = file.read()
                except FileNotFoundError:
                    http_content = "<html><body><p>File not found</p></body></html>"
                    self.log_message("[ERROR] file not found!")
                
                http_header = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/octet-stream\r\n"
                    f"Content-Length: {len(http_content)}\r\n"
                    f"Content-Disposition: attachment; filename={resource_path}\r\n"
                    f"Date: {datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
                    "Server: Multi-threaded HTTP Server\r\n"
                    "Connection: keep-alive\r\n"
                    "\r\n"
                )
                
                http_response = http_header.encode(self._FORMAT) + http_content
                return http_response    
                
                
            
    def parse_http_request(self, req_data):
    
        if not req_data:
            return None, {}
        
        lines = req_data.decode(self._FORMAT).split("\r\n")
        
        if not lines:
            return None, {}
        
        req_line = lines[0]
        headers = {}
        
        for line in lines:
            if not line:
                continue #to get params
            if ':' in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        
        return req_line, headers
    
    def handle_Request(self, clientSocket, clientAddr):
                            
        self.log_message(f"[Thread-{self._THREADPOOL - self._thread_semaphore._value}] Connection from {clientAddr[0]}:{clientAddr[1]}")
        try:
            request_data = clientSocket.recv(1024)
        
            req_line, headers = self.parse_http_request(request_data)
            
            connection_type = headers.get('connection', '').lower()
            persistent = 'keep-alive' in connection_type
            
            self.log_message(f"Request: {req_line}")
            self.log_message(f"Host validation: {headers.get('host', '').lower()} ✓")

            self.log_message(f"Connection: {connection_type}")
            
            req_line = req_line.split(" ")
            method = req_line[0]
            req_file = req_line[1]
            
            if req_file != '/':
                req_file = req_line[1].split('/')[1]
            
            http_response = self.create_Response(method, req_file)
            
            clientSocket.send(http_response)
            
        except Exception as e:
            self.log_message(f"[ERROR] Problem with client {clientAddr}: {e}")
        finally:
            clientSocket.close()
            

    def handle_Client(self):
        while True:
            try:
                client_data = self._connection_que.get(block=True)
                
                if client_data is None:
                    break
                
                clientSocket, clientAddr = client_data
                self.log_message(f"Connection dequeued, assigned to Thread-{self._THREADPOOL - self._thread_semaphore._value + 1}")
                
                available = self._thread_semaphore.acquire(blocking=False)
                
                if not available:
                    self._thread_semaphore.acquire()
                
                if self._thread_semaphore._value == 0: 
                    self._log_message(f"Warning: Thread pool saturated, queuing connection")
                    
                try:
                    self.handle_Request(clientSocket, clientAddr)
                finally:
                    self._thread_semaphore.release()
                    self.log_message(f"Thread pool status: [{self._thread_semaphore._value}/{self._THREADPOOL}] available")  
            except Exception as e:                
                if 'available' in locals() and available:
                    self._thread_semaphore.release()
                    
    def start_Server(self):
        try:
            serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            serverSocket.bind(self._ADDR)
            
            serverSocket.listen(50)
            self.log_message(f"HTTP Server started on http://{self._SERVER}:{self._PORT}")
            self.log_message(f"Thread pool size: {self._THREADPOOL}")
            self.log_message(f"Serving files from 'resources' directory")
            
            self.log_message(f"Press Ctrl+C to stop the server")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers = self._THREADPOOL) as executor:
                for _ in range(self._THREADPOOL):
                    executor.submit(self.handle_Client)

                try:
                    while True:
                        clientSocket, clientAddr = serverSocket.accept()
                        
                        self._connection_que.put((clientSocket, clientAddr))
                                                
                except KeyboardInterrupt:
                    self.log_message("Received shutdown signal")
                finally:
                    for _ in range(self._THREADPOOL):
                        self._connection_que.put(None)
                        
        except Exception as e:
            self.log_message(f"Server couldn't start: {e}")
            
        finally:
            if 'serverSocket' in locals():
                serverSocket.close()
                
            
server = server()
server.start_Server()