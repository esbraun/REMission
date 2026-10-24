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
        if self.path == '/generate/breadth':
            self.breadth_POST()
            return
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

    def breadth_POST(self):
        # Explicit new-version transport; the historical path/cap is untouched.
        text = self.headers.get('Content-Length', '')
        if type(text) is not str or not text.isascii() or not text.isdecimal() or len(text)>6 or not 0<int(text)<=262144:
            self.send_error(400)
            return
        def unique(pairs):
            result={}
            for key,value in pairs:
                if key in result:raise ValueError('duplicate field')
                result[key]=value
            return result
        def finite(_):raise ValueError('nonfinite JSON')
        try:
            raw=self.rfile.read(int(text))
            if len(raw)!=int(text):raise ValueError('short request')
            value=json.loads(raw,object_pairs_hook=unique,parse_constant=finite)
            if type(value) is not dict or value.get('law_version')!='poc-breadth-longitudinal-v3':raise ValueError('exact breadth profile required')
            from .breadth import generate as generate_breadth
            result=generate_breadth(value)
        except (ValueError,TypeError,KeyError):
            self.send_error(422,'invalid breadth generator request')
            return
        payload=json.dumps(result,separators=(',',':'),allow_nan=False).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass


if __name__ == '__main__':
    HTTPServer(('0.0.0.0', 8780), Handler).serve_forever()
