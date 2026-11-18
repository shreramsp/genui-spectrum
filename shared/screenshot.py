"""Open a demo in a headless browser, run the first example, and save screenshot.png.

    python shared/screenshot.py 01-ag-ui/1-static
    python shared/screenshot.py 01-ag-ui/4-mixed --click "Make it cheaper"

Runs OFFLINE by default (saved replies, no cost). Pass --live to use the real model.
Fails if the page logs a JavaScript error or the run does not finish.
"""

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_run(page, timeout=90_000, pattern="RUN_(FINISHED|ERROR)"):
    """Wait until the event log shows `pattern` (a finished AG-UI run by default)."""
    page.wait_for_function(
        "(p) => [...document.querySelectorAll('.ev')].some(e => new RegExp(p).test(e.textContent))",
        arg=pattern,
        timeout=timeout,
    )
    page.wait_for_timeout(800)  # let iframes paint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("demo")
    parser.add_argument("--click", action="append", default=[], help="button text to click after the first run")
    parser.add_argument("--frame-click", action="append", default=[], help="button text to click inside the sandbox")
    parser.add_argument("--view-click", action="append", default=[], help="MCP Apps: button text inside the host's view iframe")
    parser.add_argument("--view-frame-click", action="append", default=[], help="MCP Apps: button text inside the view's nested sandbox")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--out", default="screenshot.png")
    args = parser.parse_args()

    demo = ROOT / args.demo
    port = free_port()
    env = {**os.environ, "PORT": str(port)}
    if not args.live:
        env["OFFLINE"] = "1"
    server = subprocess.Popen([sys.executable, str(demo / "server.py")], env=env, cwd=ROOT)
    errors = []
    try:
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.2)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
            page.on("console", lambda m: m.type == "error" and errors.append(m.text))
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{port}/")
            page.click(".shell-form button")
            wait_for_run(page)
            shots = [demo / args.out]
            page.screenshot(path=shots[0], full_page=True)

            view = page.frame_locator(".mcp-host-frame iframe")
            steps = [("frame", x) for x in args.frame_click] + [("page", x) for x in args.click]
            steps += [("nested", x) for x in args.view_frame_click] + [("view", x) for x in args.view_click]
            for i, (where, label) in enumerate(steps, start=1):
                page.evaluate("document.querySelector('.shell-events').replaceChildren()")
                if where == "frame":
                    page.frame_locator("iframe.sandbox").get_by_text(label).click()
                elif where == "page":
                    page.get_by_role("button", name=label).click()
                elif where == "view":
                    view.get_by_role("button", name=label).click()
                else:
                    view.frame_locator("iframe.sandbox").get_by_text(label).click()
                # MCP view clicks call tools through the host (no AG-UI run): wait for the bridge reply.
                wait_for_run(page, pattern="RUN_(FINISHED|ERROR)" if where in ("frame", "page") else "response #\\d+")
                shot = demo / args.out.replace(".png", f"_after_{i}.png")
                page.screenshot(path=shot, full_page=True)
                shots.append(shot)
            log = page.inner_text(".shell-events")
            browser.close()
    finally:
        server.terminate()

    if errors:
        sys.exit("JavaScript errors:\n" + "\n".join(errors))
    if "RUN_ERROR" in log:
        sys.exit("run ended with RUN_ERROR:\n" + log)
    for shot in shots:
        print("saved", shot.relative_to(ROOT) if shot.is_relative_to(ROOT) else shot)


if __name__ == "__main__":
    main()
