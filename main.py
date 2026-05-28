from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import mimetypes
from pathlib import Path
import json
import logging
import socket
from threading import Thread
from datetime import datetime

BASE_DIR = Path()
BUFFER_SIZE = 1024
HTTP_PORT = 3000
HTTP_HOST = '0.0.0.0'
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000

def ensure_storage():
    storage_dir = Path("storage")
    data_file = storage_dir / "data.json"
    storage_dir.mkdir(exist_ok=True)
    if not data_file.exists():
        data_file.write_text(json.dumps({}))

ensure_storage()

class WebProject(BaseHTTPRequestHandler):

    def do_GET(self):
        base_url = urllib.parse.urlparse(self.path)

        if base_url.path == '/':
                self.send_html('index.html')
        elif base_url.path == '/message':
                self.send_html('message.html')
        else:
            file = BASE_DIR.joinpath(base_url.path[1:])
            if file.exists():
                self.send_static(file)
            else:
                self.send_html('error.html', 404)
    
    def do_POST(self):
        size = self.headers.get('Content-Length')
        data = self.rfile.read(int(size))

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))
        client_socket.close()

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()      

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        with open(filename, 'rb') as file:
            self.wfile.write(file.read())
    
    def send_static(self, filename, status_code=200):
        self.send_response(status_code)

        mime_type, *_ = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header('Content-type', mime_type)
        else:
            self.send_header('Content-type', 'text/plain')
        self.end_headers()

        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

def save_data_from_form(data):


    parse_data = urllib.parse.unquote_plus(data.decode())

    try:
        parse_dict = {key: value for key, value in [el.split('=') for el in parse_data.split('&')]}

        file_path = Path('storage/data.json')
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as file:
                all_data = json.load(file)
        else:
            all_data = {}
        
        key = str(datetime.now())
        all_data[key] = parse_dict

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(all_data, file, ensure_ascii=False, indent=4)
    except ValueError as err:
        logging.error(err)
    except OSError as err:
        logging.error(err)
    
def run_socket_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    logging.info(f'Starting socket server...')

    try:
        while True:
            message, address = server_socket.recvfrom(BUFFER_SIZE)
            logging.info(f'Socked received {address}: {message}')
            save_data_from_form(message)
    except KeyboardInterrupt:
        pass
    finally:
        server_socket.close()

def run_http_server(host, port):
    address = (host, port)
    server = HTTPServer(address, WebProject)
    logging.info('Starting http server...')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(threadName)s %(message)s')

    http_server = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    http_server.start()

    socket_server = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    socket_server.start()