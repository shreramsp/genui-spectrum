# Tests always run OFFLINE: the model is replaced by each demo's saved offline reply,
# so they are free, fast and repeatable. Live runs happen when you start a server.
import os
import sys
from pathlib import Path

os.environ["OFFLINE"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent))
