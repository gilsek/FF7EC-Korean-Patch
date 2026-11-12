"""Diagnostic endpoint for XUnity.AutoTranslator (CustomTranslate).
Logs every text AT could not find in the translation files and returns it unchanged.
usage: python at_capture_server.py OUT.tsv [port=5005]
AT config: [Service] Endpoint=CustomTranslate, [Custom] Url=http://127.0.0.1:5005/"""
import sys, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OUT = sys.argv[1]
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5005


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        text = q.get('text', [''])[0]
        with open(OUT, 'a', encoding='utf-8') as f:
            f.write(text.replace('\\', '\\\\').replace('\r', '\\r').replace('\n', '\\n') + '\n')
        body = text.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
