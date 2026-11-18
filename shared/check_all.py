"""Check that EVERY demo still works: run all tests, then open each demo in a headless browser.

    python shared/check_all.py

Run this before recording videos. It is offline (no API key, no cost) and does not touch
the committed screenshots: the browser check saves its pictures to a temporary folder.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    print("== tests")
    if subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT).returncode:
        sys.exit("tests failed")

    demos = sorted(p.parent for p in ROOT.glob("0*-*/*-*/server.py"))
    failed = []
    with tempfile.TemporaryDirectory() as tmp:
        for demo in demos:
            name = demo.relative_to(ROOT)
            out = Path(tmp) / f"{str(name).replace('/', '_')}.png"
            result = subprocess.run(
                [sys.executable, str(ROOT / "shared/screenshot.py"), str(name), "--out", str(out)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            ok = result.returncode == 0
            print(f"{'OK  ' if ok else 'FAIL'}  {name}")
            if not ok:
                failed.append(name)
                print(result.stdout + result.stderr)

    print(f"\n{len(demos) - len(failed)}/{len(demos)} demos render in the browser without errors")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
