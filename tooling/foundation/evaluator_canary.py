"""Private foundation canary fixture, not a longitudinal generator/evaluator."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument("mode",choices=["prepare","read","serve"]);args=parser.parse_args()
    if args.mode=="prepare":
        Path("/truth/canary.json").write_text(json.dumps({"kind":"private_foundation_canary","value":"evaluator-only-foundation-fixture"}))
        Path("/staging/history.json").write_text(json.dumps({"schema_version":"1.0.0","synthetic":True,"kind":"observed_history","patient_id":"SYN-02","records":[]}))
        print(json.dumps({"status":"private_canary_and_hand_authored_observed_fixture_prepared","generator":"not_implemented"}))
    elif args.mode=="read":
        canary=json.loads(Path("/truth/canary.json").read_text());assert canary["kind"]=="private_foundation_canary"
        print(json.dumps({"status":"positive_evaluator_canary_read","private_fixture_exists":True}))
    else:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200);self.end_headers();self.wfile.write(b'private foundation evaluator fixture')
            def log_message(self,*_):pass
        HTTPServer(("0.0.0.0",8766),Handler).serve_forever()


if __name__=="__main__":main()
