"""06 Harness · 2 · DECLARATIVE — the bounded agent loop (../harness.py) with the `declarative` render tool.

Web:       python 06-harness-integration/2-declarative/server.py      then open http://localhost:8000
Terminal:  python 06-harness-integration/harness.py --mode declarative "Summarize my trip spending"
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import harness  # noqa: E402,F401
import harness_app  # noqa: E402
from shared.agui import serve  # noqa: E402

app = harness_app.create_harness_app("declarative", HERE)

if __name__ == "__main__":
    serve(app)
