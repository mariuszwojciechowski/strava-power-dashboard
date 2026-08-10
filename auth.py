import http.server
import json
import urllib.parse
import webbrowser

import requests

import config

REDIRECT_URI = "http://localhost:8321/callback"
AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"

_result = {}


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        if "code" in qs:
            _result["code"] = qs["code"][0]
            self.wfile.write("<h1>Autoryzacja zakończona. Możesz zamknąć tę kartę.</h1>".encode("utf-8"))
        else:
            _result["error"] = qs.get("error", ["unknown"])[0]
            self.wfile.write("<h1>Autoryzacja odrzucona.</h1>".encode("utf-8"))

    def log_message(self, format, *args):
        pass


def main():
    params = {
        "client_id": config.get_client_id(),
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": "activity:read_all,profile:read_all",
    }
    url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    print(f"Otwieram przeglądarkę do autoryzacji Strava:\n{url}\n")
    webbrowser.open(url)

    server = http.server.HTTPServer(("localhost", 8321), _CallbackHandler)
    while "code" not in _result and "error" not in _result:
        server.handle_request()

    if "error" in _result:
        raise SystemExit(f"Autoryzacja nie powiodła się: {_result['error']}")

    resp = requests.post(TOKEN_URL, data={
        "client_id": config.get_client_id(),
        "client_secret": config.get_client_secret(),
        "code": _result["code"],
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    tokens = resp.json()
    with open(config.TOKENS_FILE, "w") as f:
        json.dump(tokens, f)
    print(f"Zapisano tokeny w {config.TOKENS_FILE}")


if __name__ == "__main__":
    main()
