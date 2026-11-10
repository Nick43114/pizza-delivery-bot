from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import threading


class SimpleHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK! Bot is running.")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()


def run_server():
    # Render передает свой порт через переменную окружения PORT (обычно 10000)
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()


def keep_alive():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
