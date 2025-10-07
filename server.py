import sys
import socket
import queue
import threading
import concurrent.futures

class server:
    _SERVER = '127.0.0.1'
    _PORT = 8080
    _THREADPOOL = 10
    _FORMAT = 'utf-8'
    
    def __init__(self):
        try:
            if len(sys.argv) > 1:
                self._PORT = int(sys.argv[1])
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
            print(message)
            
            
    def parse_http_request(self, data):
    
        if not data:
            return None, {}
        
        lines = data.decode(self._FORMAT).split("\r\n")
        
        req_method = lines[0]
        
        headers = {}
        
        for line in lines:
            if not line:
                continue
            if ':' in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        
        return req_method, headers
            

    def handle_Client(self):
        while True:
            try:
                client_data = self._connection_que.get(block=True)
                
                if client_data is None:
                    break
                
                clientSocket, clientAddr = client_data
        
                self.log_message(f"[NEW CONNECTION] Client {clientAddr} connected.")
                
                available = self._thread_semaphore.acquire(blocking=False)
                
                if not available:
                    self._log_message("[WARNING] Thread pool full but connection was dequeued!")
                    self._thread_semaphore.acquire()
                
                if self._thread_semaphore._value == 0:  # No more available slots
                    self._log_message(f"[POOL STATUS] Thread pool is now FULL! (0/{self._THREADPOOL} available)")
                    
                try:
                    try:
                        request_data = clientSocket.recv(1024)
                    
                        req, header = self.parse_http_request(request_data)
                        
                        try:
                            with open('./resources/index.html', 'r') as file:
                                http_content = file.read()
                        except FileNotFoundError:
                            http_content = "<html><body><p>File not found</p></body></html>"
                            self.log_message("[ERROR] file not found!")
                            
                        http_header = (
                            "HTTP/1.1 200 OK\r\n"
                            "Content-Type: text/html\r\n"
                            f"Content-Length: {len(http_content)}\r\n"
                            "\r\n"
                        )
                        
                        http_response = http_header + http_content
                        
                        clientSocket.send(http_response.encode(self._FORMAT))

                    except Exception as e:
                        self.log_message(f"[ERROR] Problem with client {clientAddr}: {e}")
                    finally:
                        clientSocket.close()
                        self.log_message(f"[CLOSED] Connection with {clientAddr} closed")
                finally:
                    self._thread_semaphore.release()
                    self.log_message(f"[POOL STATUS] Thread pool now has availability (1/{self._THREADPOOL} available")  
            except Exception as e:
                self.log_message(f"[ERROR] Worker thread error: {e}")
                
                if 'available' in locals() and available:
                    self._thread_semaphore.release()
                    
    def start_Server(self):
        try:
            serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            serverSocket.bind(self._ADDR)
            
            serverSocket.listen(50)
            print(f"[LISTENING] Server is listening on {self._SERVER}:{self._PORT}")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers = self._THREADPOOL) as executor:
                for _ in range(self._THREADPOOL):
                    executor.submit(self.handle_Client)

                try:
                    while True:
                        clientSocket, clientAddr = serverSocket.accept()
                        
                        self._connection_que.put((clientSocket, clientAddr))
                        self.log_message(f"[QUEUED] New client {clientAddr} added to queue")
                        
                except KeyboardInterrupt:
                    self.log_message("[STOPPING] Received shutdown signal")
                finally:
                    for _ in range(self._THREADPOOL):
                        self._connection_que.put(None)
                        
        except Exception as e:
            self.log_message(f"[CRITICAL ERROR] Server couldn't start: {e}")
            
        finally:
            if 'serverSocket' in locals():
                serverSocket.close()
            
server = server()
server.start_Server()