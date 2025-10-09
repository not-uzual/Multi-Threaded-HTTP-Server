import sys
import socket
import queue
import threading
import concurrent.futures
import os
import json
from datetime import datetime, timezone
import random
import time

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
        self._RESOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
        self._MAX_REQUESTS_PER_CONNECTION = 100
        self._KEEP_ALIVE_TIMEOUT = 30    
        
    def log_message(self, message):
        with self._print_lock:
            print(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {message}")
            print()
                
    def parse_http_request(self, req_data):
        if not req_data:
            return None, {}, None
        
        lines = req_data.decode(self._FORMAT).split("\r\n")
        if not lines:
            return None, {}, None
        
        req_line = lines[0]
        headers = {}
        
        for line in lines:
            if not line:
                break
            if ':' in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        
        payload = req_data.decode(self._FORMAT).split("\r\n\r\n")[1]
        
        return req_line, headers, payload
    
    
    def create_Response(self, clientSocket, req_method, headers, persistent, file_path, res_Data):
        if req_method == 'GET':
            return self.serveGETRequest(clientSocket, persistent, file_path)
        elif req_method == 'POST':
            return self.servePOSTRequest(headers, res_Data)
    
    
    def handle_Request(self, clientSocket, clientAddr):         
        self.log_message(f"[Thread-{self._THREADPOOL - self._thread_semaphore._value}] Connection from {clientAddr[0]}:{clientAddr[1]}")
        
        requests_count = 0
        try:
            clientSocket.settimeout(self._KEEP_ALIVE_TIMEOUT)
            
            while requests_count < self._MAX_REQUESTS_PER_CONNECTION:
                requests_count += 1
                
                request_data = clientSocket.recv(1024)
                if not request_data:
                    break
        
                req_line, headers, payload = self.parse_http_request(request_data)
                if not req_line:
                    self.send_error_response(clientSocket, 400, "Bad Request")
                    break
                
                host_valid, status_code, status_message = self.validate_host_header(headers, clientAddr)
                if not host_valid:
                    self.send_error_response(clientSocket, status_code, status_message)
                    break
                
                method, path, http_version = req_line.split(" ")
            
                if http_version.upper() == "HTTP/1.1":
                    persistent = True  
                else:
                    persistent = False 
                
                connection_header = headers.get('connection', '').lower()
                if 'keep-alive' in connection_header:
                    persistent = True
                elif 'close' in connection_header:
                    persistent = False    
                
                self.log_message(f"Request: {req_line}")
                self.log_message(f"Host validation: {headers.get('host', '').lower()} ✓")

                self.log_message(f"Connection: {connection_header}")
                
                file_path, status_code, status_message = self.get_safe_file_path(path)
                
                if status_code != 200:
                    self.send_error_response(clientSocket, status_code, status_message)
                    if not persistent:
                        break
                    continue
                
                content_type = self.get_content_type(file_path)
                
                http_response = self.create_Response(clientSocket, method, headers, persistent, file_path, payload)
                
                clientSocket.send(http_response)
                
                if not persistent or requests_count >= self._MAX_REQUESTS_PER_CONNECTION:
                    break
                    
                clientSocket.settimeout(self._KEEP_ALIVE_TIMEOUT)
            
        except socket.timeout:
            self.log_message(f"[TIMEOUT] Connection with {clientAddr} timed out after {self._KEEP_ALIVE_TIMEOUT}s")
        except ConnectionResetError:
            self.log_message(f"[RESET] Connection with {clientAddr} was reset by client")
        except Exception as e:
            self.log_message(f"[ERROR] Problem with client {clientAddr}: {e}")
        finally:
            clientSocket.close()
            
            
    def handle_Client(self):
        while True:
            try:
                client_data = self._connection_que.get(block=False)
                
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
            except queue.Empty:
                time.sleep(0.1)
            except Exception as e:                
                if 'available' in locals() and available:
                    self._thread_semaphore.release()
                    
    def start_Server(self):
        try:
            serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            serverSocket.bind(self._ADDR)
            
            serverSocket.settimeout(1.0)
            
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
                        try:
                            clientSocket, clientAddr = serverSocket.accept()
                        
                            self._connection_que.put((clientSocket, clientAddr))
                        except socket.timeout:
                            continue                           
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
                
                
    def serveGETRequest(self, clientSocket, persistent, file_path):
        try:
            with open(file_path, 'rb') as file:
                http_content = file.read()
        except FileNotFoundError:
            self.send_error_response(clientSocket, 500, "Internal Server Error")
            
        if persistent:
                connection_header = f"Connection: keep-alive\r\nKeep-Alive: timeout={self._KEEP_ALIVE_TIMEOUT}, max={self._MAX_REQUESTS_PER_CONNECTION}\r\n"
        else:
            connection_header = "Connection: close\r\n"
            
        content_type = self.get_content_type(file_path)
        
        http_header = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(http_content)}\r\n"
            f"Content-Disposition: {'attachment; filename=' + file_path if content_type == 'application/octet-stream' else 'inline'}\r\n"
            f"Date: {datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
            "Server: Multi-threaded HTTP Server\r\n"
            f"{connection_header}"
            "\r\n"
        )
        
        http_response = http_header.encode(self._FORMAT) + http_content
        return http_response
        
        
    def servePOSTRequest(self, headers, res_Data):
        contentType = headers.get('content-type', '')
        
        if contentType != 'application/json':
            pass
        
        res_Data = json.loads(res_Data)
        
        if type(res_Data) != type({}):
            print(type(res_Data))
            pass
        
        file_path = os.path.join('.','resources', 'uploads', f'upload_{datetime.now().strftime("%Y%m%d")}_{random.randint(100000, 999999)}.json')
        
        with open(file_path, "w") as file:
            json.dump(res_Data, file, indent=4) 
        
        http_content = str({
             "status": "success",
            "message": "File created successfully",
            "filepath": file_path
        })
        
        http_header = (
            "HTTP/1.1 201 Created\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {len(http_content)}\r\n"
                f"Date: {datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
                "Server: Multi-threaded HTTP Server\r\n"
                "Connection: keep-alive\r\n"
                "\r\n"
        )
        
        http_response = http_header + http_content
        return http_response.encode(self._FORMAT)
    
    
    def send_error_response(self, clientSocket, status_code, status_message):
        error_content = f"""
        <html>
            <head><title>{status_code} {status_message}</title></head>
            <body>
                <h1>{status_code} {status_message}</h1>
                    <p>The server cannot process your request.</p>
                <hr>
                <address>Simple HTTP Server</address>
            </body>
        </html>
        """.strip().encode(self._FORMAT)
        
        response = (
            f"HTTP/1.1 {status_code} {status_message}\r\n"
            f"Content-Type: text/html\r\n"
            f"Content-Length: {len(error_content)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode(self._FORMAT) + error_content
        
        try:
            clientSocket.send(response)
        except Exception as e:
            self.log_message(f"[ERROR] Failed to send error response: {e}")
    
    def get_content_type(self, file_path):
        extension = os.path.splitext(file_path)[1].lower()
        
        content_types = {
            '.html': 'text/html',
            '.htm': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.ico': 'image/x-icon',
            '.txt': 'text/plain',
            '.json': 'application/json',
        }
    
        return content_types.get(extension, 'application/octet-stream')
    
    def validate_host_header(self, headers, client_addr):
        if 'host' not in headers:
            self.log_message(f"[SECURITY] Missing Host header from {client_addr}")
            return False, 400, "Bad Request"
        
        host = headers['host']
        
        valid_hosts = [
            f"localhost:{self._PORT}",
            f"127.0.0.1:{self._PORT}",
            f"{self._SERVER}:{self._PORT}"
        ]
        
        if host not in valid_hosts:
            self.log_message(f"[SECURITY] Invalid Host header: {host} from {client_addr}")
            return False, 403, "Forbidden"
        
        return True, 200, "OK"
    
    def get_safe_file_path(self, path):
        if path == '/' or not path:
            path = '/index.html'
        
        if path.startswith('/'):
            path = path[1:]
        
        if self.is_path_traversal_attack(path):
            return None, 403, "Forbidden"
        
        file_path = os.path.normpath(os.path.join(self._RESOURCES_DIR, path))
        
        if not file_path.startswith(self._RESOURCES_DIR):
            return None, 403, "Forbidden"
        
        if not os.path.isfile(file_path):
            return None, 404, "Not Found"
        
        return file_path, 200, "OK"
    
    def is_path_traversal_attack(self, path):
        if '..' in path or '//' in path or '\\' in path:
            return True
        
        if path.startswith('/') or path.startswith('\\'):
            if path == '/' or path == '/index.html':
                return False
            return True
        
        if '%2e' in path.lower() or '%2f' in path.lower() or '%5c' in path.lower():
            return True
        
        return False
            
server = server()
server.start_Server()