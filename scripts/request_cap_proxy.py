"""Forward OpenAI-compatible chat requests to an upstream endpoint with the Agenthon 2026 House route's limits.

The House route admitted at most 25 requests per task, retries included, and refused later ones; the submitted
agent relies on that refusal to stop and submit. It also applied at most 4,000 output tokens per request: an
omitted limit meant 4,000 and a larger one was reduced to 4,000. The submitted agent sends no max_tokens, and
other providers apply their own default, so run this proxy for each task and point MODEL_ENDPOINT at it to
reproduce both limits.

Usage: python3 request_cap_proxy.py --upstream https://api.studio.nebius.com --port 8025 [--cap 25] [--max-tokens 4000] [--host 0.0.0.0]
"""
import argparse
import http.server
import json
import threading
import urllib.error
import urllib.request

COUNT = [0]
LOCK = threading.Lock()


def make_handler(upstream, cap, max_tokens):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            with LOCK:
                COUNT[0] += 1
                n = COUNT[0]
            if n > cap:
                self._send(429, json.dumps({"error": {"message": f"request allowance of {cap} spent", "type": "rate_limit_error"}}).encode())
                return
            try:
                payload = json.loads(body)
                limit = min(int(payload.get("max_tokens") or max_tokens), max_tokens)
                payload.pop("max_completion_tokens", None)
                payload["max_tokens"] = limit
                body = json.dumps(payload).encode()
            except (ValueError, TypeError):
                pass
            path = self.path if self.path.startswith("/v1") else "/v1" + self.path
            req = urllib.request.Request(upstream.rstrip("/") + path, data=body, method="POST", headers={
                "Content-Type": "application/json", "Authorization": self.headers.get("Authorization", "")})
            try:
                with urllib.request.urlopen(req, timeout=900) as resp:
                    self._send(resp.status, resp.read())
            except urllib.error.HTTPError as exc:
                self._send(exc.code, exc.read())
            except Exception as exc:
                self._send(502, json.dumps({"error": {"message": str(exc)}}).encode())

        def _send(self, status, payload):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt, *args):
            print(f"[proxy] request {COUNT[0]}: " + fmt % args, flush=True)

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", required=True)
    ap.add_argument("--port", type=int, default=8025)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--cap", type=int, default=25)
    ap.add_argument("--max-tokens", type=int, default=4000)
    args = ap.parse_args()
    http.server.ThreadingHTTPServer((args.host, args.port), make_handler(args.upstream, args.cap, args.max_tokens)).serve_forever()


if __name__ == "__main__":
    main()
