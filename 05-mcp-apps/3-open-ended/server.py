"""05 MCP Apps · 3 · OPEN-ENDED — run the host for this mode: the model is offered only `build_trip_widget`.

The MCP server (../trip_server.py) and the host (../mcp_host.py) are shared by all four modes;
see ../README.md for what each mode's tool and view do.

Run:  python 05-mcp-apps/3-open-ended/server.py   then open http://localhost:8000
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

from mcp_host import create_host  # noqa: E402
from shared.agui import serve  # noqa: E402

app = create_host("open-ended", HERE)

if __name__ == "__main__":
    serve(app)
