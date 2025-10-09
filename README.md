# 🚀 Multi-Threaded HTTP Server

A robust, production-ready HTTP/1.1 server implementation in pure Python with advanced features like connection pooling, persistent connections, and security hardening.

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![HTTP](https://img.shields.io/badge/HTTP-1.1-green.svg)](https://httpwg.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

### 🔥 Core Capabilities
- **Multi-threaded Architecture**: Concurrent request handling using thread pools
- **HTTP/1.1 Compliant**: Full support for persistent connections (keep-alive)
- **GET & POST Support**: Serve static files and handle JSON data uploads
- **Connection Pooling**: Efficient resource management with configurable thread pools
- **Smart Timeouts**: Automatic connection cleanup after 30 seconds of inactivity

### 🛡️ Security First
- **Path Traversal Protection**: Prevents directory escape attacks (`../`, encoded paths)
- **Host Header Validation**: Protects against DNS rebinding attacks
- **Resource Isolation**: Files served only from designated `resources/` directory
- **Input Sanitization**: URL normalization and malicious pattern detection

### ⚙️ Production Ready
- **Configurable Parameters**: Customize port, host, and thread pool size via CLI
- **Thread-safe Logging**: Synchronized message logging with timestamps
- **Graceful Shutdown**: Clean resource cleanup on Ctrl+C
- **Error Handling**: Comprehensive exception management and error responses

---

## 📦 Quick Start

### Prerequisites
```bash
Python 3.7 or higher
```

### Installation
```bash
# Clone the repository
git clone https://github.com/not-uzual/Multi-Threaded-HTTP-Server.git
cd Multi-Threaded-HTTP-Server

# Create resources directory structure
mkdir -p resources/uploads
```

### Running the Server

**Default Configuration** (localhost:8080, 10 threads):
```bash
python server.py
```

**Custom Configuration**:
```bash
python server.py [PORT] [HOST] [THREADPOOL_SIZE]

# Examples:
python server.py 3000                    # Port 3000
python server.py 8080 127.0.0.1          # Port 8080, localhost
python server.py 8080 127.0.0.1 20       # Port 8080, 20 threads
```

### Access the Server
```
http://localhost:8080
```

---

## 🏗️ Architecture Overview

### Thread Pool Management
```
┌─────────────────────────────────────────┐
│         Main Accept Loop                │
│  (Accepts incoming connections)         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Connection Queue                   │
│  (Thread-safe FIFO buffer)              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   Thread Pool Executor (10 workers)     │
│  ┌──────┐ ┌──────┐       ┌──────┐       │
│  │ T-1  │ │ T-2  │  ...  │ T-10 │       │
│  └──────┘ └──────┘       └──────┘       │
└─────────────────────────────────────────┘
```

### Request Processing Pipeline
```
Client Request → Parse HTTP → Validate Host → Security Check → Serve Response
                     ↓             ↓              ↓                ↓
                Headers       Host Header    Path Traversal    GET/POST Handler
```

---

## 🔧 Major Components

### 1. **Connection Management** (`start_Server`, `handle_Client`)
- **Accept Loop**: Continuously accepts incoming connections
- **Queue System**: Thread-safe FIFO queue for connection distribution
- **Thread Pool**: Pre-spawned worker threads process queued connections
- **Semaphore Control**: Limits concurrent connections to prevent resource exhaustion

**Key Features:**
- Non-blocking socket accept with 1-second timeout
- Graceful shutdown handling (Ctrl+C)
- Automatic thread cleanup on exit

### 2. **Request Handler** (`handle_Request`)
The heart of the server - processes individual client requests:

```python
# Handles up to 100 requests per connection (HTTP keep-alive)
# 30-second timeout for idle connections
```

**Flow:**
1. **Receive Data**: Reads incoming HTTP request (1024 bytes)
2. **Parse Request**: Extracts method, path, headers, and body
3. **Validate Host**: Security check against DNS rebinding
4. **Detect Protocol**: HTTP/1.1 → persistent, HTTP/1.0 → close
5. **Security Scan**: Path traversal detection
6. **Serve Response**: Route to GET/POST handler
7. **Keep-Alive Logic**: Reuse connection or close based on headers

### 3. **HTTP Parser** (`parse_http_request`)
Converts raw socket data into structured request objects:
```python
Input:  b"GET /index.html HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
Output: ("GET /index.html HTTP/1.1", {"host": "localhost:8080"}, "")
```

### 4. **Security Layer**

#### **Path Traversal Prevention** (`is_path_traversal_attack`, `get_safe_file_path`)
Blocks malicious patterns:
- `../` (parent directory escape)
- `//` (double slashes)
- `\` (backslash injection)
- URL-encoded attacks (`%2e%2e`, `%2f`, `%5c`)

#### **Host Header Validation** (`validate_host_header`)
Whitelist-based approach:
```python
Valid hosts: localhost:8080, 127.0.0.1:8080
Invalid: evil.com, 192.168.1.100:8080
```

### 5. **GET Request Handler** (`serveGETRequest`)
Serves static files from `resources/` directory:

**Features:**
- Binary file support (images, PDFs, etc.)
- MIME type detection
- Content-Length calculation
- Keep-Alive header management
- File download support (Content-Disposition)

**Response Example:**
```http
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 1234
Connection: keep-alive
Keep-Alive: timeout=30, max=100
Server: Multi-threaded HTTP Server
```

### 6. **POST Request Handler** (`servePOSTRequest`)
Handles JSON data uploads:

**Workflow:**
1. Validates `Content-Type: application/json`
2. Parses JSON payload
3. Generates unique filename (`upload_20251009_678769.json`)
4. Saves to `resources/uploads/`
5. Returns success response with file path

**Example Request:**
```bash
curl -X POST http://localhost:8080/upload \
  -H "Content-Type: application/json" \
  -d '{"name": "John", "age": 30}'
```

### 7. **Error Handler** (`send_error_response`)
Standardized error pages for:
- `400 Bad Request`: Malformed HTTP
- `403 Forbidden`: Security violation
- `404 Not Found`: Missing file
- `500 Internal Server Error`: Server crash

### 8. **MIME Type Detection** (`get_content_type`)
Supports 11+ file types:
```python
.html → text/html
.png  → image/png
.json → application/json
.*    → application/octet-stream (download)
```

### 9. **Thread-Safe Logging** (`log_message`)
Synchronized console output prevents garbled messages:
```
[2025-10-09 14:32:15] [Thread-3] Connection from 127.0.0.1:54321
[2025-10-09 14:32:15] Request: GET /index.html HTTP/1.1
[2025-10-09 14:32:15] Host validation: localhost:8080 ✓
```

---

## 📁 Project Structure

```
HTTP Server/
├── server.py              # Main server implementation
├── README.md              # This file
└── resources/             # Served files directory
    ├── index.html         # Default homepage
    ├── about.html
    ├── contact.html
    ├── image.png
    ├── logo.png
    ├── text.txt
    └── uploads/           # POST upload destination
        └── upload_20251009_678769.json
```

---

## 🧪 Testing

### Test GET Request
```bash
curl -v http://localhost:8080/index.html
```

### Test POST Request
```bash
curl -X POST http://localhost:8080/upload \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, World!", "timestamp": "2025-10-09"}'
```

### Test Keep-Alive
```bash
curl -v --keepalive-time 60 http://localhost:8080/index.html
```

### Test Path Traversal (Should Fail)
```bash
curl http://localhost:8080/../../../etc/passwd  # Returns 403 Forbidden
```

---

## 🔍 Performance Metrics

| Metric | Value |
|--------|-------|
| **Max Threads** | 10 (configurable) |
| **Requests/Connection** | 100 |
| **Timeout** | 30 seconds |
| **Buffer Size** | 1024 bytes |
| **Backlog** | 50 connections |

---

## 🛠️ Configuration Options

### Environment Variables
```python
_SERVER = '127.0.0.1'              # Bind address
_PORT = 8080                        # Listen port
_THREADPOOL = 10                    # Worker threads
_MAX_REQUESTS_PER_CONNECTION = 100  # Keep-alive limit
_KEEP_ALIVE_TIMEOUT = 30            # Idle timeout (seconds)
```

### Command Line Arguments
```bash
python server.py [PORT] [HOST] [THREADS]
```

---

## 🐛 Error Handling

The server handles these scenarios gracefully:
- **Socket Timeout**: Auto-closes idle connections
- **Connection Reset**: Detects client disconnects
- **Bad Requests**: Returns 400 with error page
- **File Not Found**: Returns 404 with error page
- **Security Violations**: Returns 403 with error page
- **Server Errors**: Returns 500 with error page

---

## 🚦 HTTP/1.1 Keep-Alive

### How It Works
1. Client sends `Connection: keep-alive` header
2. Server responds with same header + timeout parameters
3. Connection stays open for multiple requests
4. Auto-closes after 100 requests OR 30 seconds idle

### Benefits
- **Reduced Latency**: No TCP handshake overhead
- **Lower CPU Usage**: Fewer socket operations
- **Better Throughput**: Pipelined requests

---

## 📊 Logging

### Log Formats
```
[YYYY-MM-DD HH:MM:SS] Message
[Thread-N] Connection from IP:PORT
[TIMEOUT] Connection timed out
[RESET] Connection reset by client
[ERROR] Error details
[SECURITY] Security violation detected
```

---

## 🤝 Contributing

Contributions welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

---

## 📄 License

This project is open source and available under the MIT License.

---

## 👤 Author

**not-uzual**
- GitHub: [@not-uzual](https://github.com/not-uzual)

---

## 🙏 Acknowledgments

Built with ❤️ using Python's standard library:
- `socket` - Low-level networking
- `threading` - Concurrency primitives
- `concurrent.futures` - Thread pool management
- `queue` - Thread-safe data structures

---

**⭐ Star this repo if you find it useful!**
