"""Private bounded HTTP process. No database, evaluator output or host port."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from .restricted import generate as generate_v1
from .restricted_v2 import generate as generate_v2


def generate(request):
    # No optional version/default is inserted into the original v1 request.
    return generate_v2(request) if request.get('law_version') == 'poc-longitudinal-v2' else generate_v1(request)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        if self.path != '/generate' or not 0 < length <= 32768:
            self.send_error(400)
            return
        try:
            result = generate(json.loads(self.rfile.read(length)))
        except (ValueError, TypeError, KeyError):
            self.send_error(422, 'invalid generator request')
            return
        payload = json.dumps(result, separators=(',', ':'), allow_nan=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass


if __name__ == '__main__':
    HTTPServer(('0.0.0.0', 8780), Handler).serve_forever()
