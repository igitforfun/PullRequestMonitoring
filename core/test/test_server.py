import http.server
import socketserver
import threading

PORT = 8000
DIRECTORY = "./core/test/jenkins_log/"

class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == '/shutdown':
            print("Shutting down server.")
            def shutdown_server():
                self.server.shutdown()
            threading.Thread(target=shutdown_server).start()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Server is shutting down.")
        else:
            super().do_GET()

class test_server:
    def __init__(self):
        self.httpd = socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler)

    def run_server(self):
        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer is shutting down.")
            self.httpd.server_close()

    def close_server(self):
        import requests
        try:
            requests.get('http://localhost:8000/shutdown')
        except requests.exceptions.RequestException as e:
            print(f"Error shutting down server: {e}")
        self.httpd.server_close()

if __name__ == "__main__":
    ts = test_server()
    ts.run_server()
    ts.close_server()
