"""Start ALL 24 demos at once, plus a hub page that links to them.

    python shared/run_all.py            then open http://localhost:8000
    (Ctrl+C stops everything)

Ports: part P, mode M  ->  8000 + 10*P + M     e.g. Part 03 declarative = 8032
"""

import os
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PARTS = [
    ("01-ag-ui", "AG-UI", "The pipe: how the agent's work reaches the page"),
    ("02-a2ui", "A2UI", "Google's format: screen structure and data sent separately"),
    ("03-openui", "OpenUI", "A short UI language that draws while it streams"),
    ("04-json-render", "json-render", "One screen built from small patches, shown on web and terminal"),
    ("05-mcp-apps", "MCP Apps", "Your screen shown inside another app (a host)"),
    ("06-harness-integration", "Harness", "An agent that reads files first, then draws a screen"),
]
MODES = [("1-static", "Static"), ("2-declarative", "Declarative"), ("3-open-ended", "Open-ended"), ("4-mixed", "Mixed")]


def port(p, m):
    return 8000 + 10 * (p + 1) + (m + 1)


def hub_html():
    rows = ""
    for p, (_, name, role) in enumerate(PARTS):
        links = "".join(f'<a href="http://localhost:{port(p, m)}/">{label}</a>' for m, (_, label) in enumerate(MODES))
        rows += f'<section><div><b>{p + 1:02d} · {name}</b><span>{role}</span></div><nav>{links}</nav></section>'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>genui-spectrum demos</title><style>
:root {{ --bg:#f6f7f9; --panel:#fff; --ink:#1b1f24; --muted:#5d6673; --line:#e2e5ea; --accent:#2f6fde; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0f1216; --panel:#171b21; --ink:#e7eaee; --muted:#98a2ae; --line:#2a3039; --accent:#6a9cff; }} }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.5 system-ui,-apple-system,sans-serif; }}
main {{ max-width:1000px; margin:0 auto; padding:32px 16px; }}
h1 {{ margin:0 0 4px; font-size:28px; }} p {{ margin:0 0 24px; color:var(--muted); }}
section {{ display:flex; flex-wrap:wrap; gap:12px; justify-content:space-between; align-items:center; background:var(--panel);
  border:1px solid var(--line); border-radius:12px; padding:14px 16px; margin-bottom:10px; }}
section b {{ display:block; font-size:18px; }} section span {{ color:var(--muted); font-size:14px; }}
nav {{ display:flex; flex-wrap:wrap; gap:6px; }}
nav a {{ text-decoration:none; color:var(--accent); border:1px solid var(--accent); border-radius:99px; padding:5px 12px; font-size:14px; font-weight:600; }}
nav a:hover {{ background:var(--accent); color:var(--panel); }}
</style></head><body><main><h1>genui-spectrum</h1>
<p>Generative UI: one trip-planner app, 6 technologies × 4 modes. Pick a demo.</p>{rows}</main></body></html>"""


class Hub(BaseHTTPRequestHandler):
    def do_GET(self):
        body = hub_html().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    procs = []
    for p, (folder, _, _) in enumerate(PARTS):
        for m, (mode, _) in enumerate(MODES):
            env = {**os.environ, "PORT": str(port(p, m))}
            procs.append(subprocess.Popen([sys.executable, str(ROOT / folder / mode / "server.py")], env=env, cwd=ROOT, stdout=subprocess.DEVNULL))
    hub = ThreadingHTTPServer(("127.0.0.1", 8000), Hub)
    print(f"Started {len(procs)} demos. Hub: http://localhost:8000   (Ctrl+C stops everything)", flush=True)
    try:
        hub.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for proc in procs:
            proc.terminate()
        time.sleep(0.5)


if __name__ == "__main__":
    main()
