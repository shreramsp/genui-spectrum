// The sandbox for model-written HTML (open-ended mode and the HtmlFrame escape hatch).
//
// Three layers of protection:
//   1. <iframe sandbox="allow-scripts">  - no allow-same-origin, so the HTML cannot read
//      our cookies, storage or DOM. It runs as an anonymous origin.
//   2. A Content-Security-Policy        - no network: no fetch, no external scripts/images.
//   3. One narrow message channel       - the HTML may only call sendAction(name, payload),
//      and the parent only accepts names on an allow-list.
// A sandbox reduces what the code can do; it does not make arbitrary output "safe".

const CSP =
  "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src data:";

const BRIDGE = `<script>
  window.sendAction = function (name, payload) {
    parent.postMessage({ kind: "genui-action", name: String(name), payload: payload ?? null }, "*");
  };
<\/script>`;

export function mountSandbox(container, html, { height = 420, allowedActions = [], onAction } = {}) {
  const frame = document.createElement("iframe");
  frame.className = "sandbox";
  frame.setAttribute("sandbox", "allow-scripts");
  frame.style.height = `${height}px`;
  frame.title = "Generated UI (sandboxed)";
  frame.srcdoc = `<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${CSP}">${BRIDGE}</head>
<body>${html}</body></html>`;

  function listener(event) {
    if (event.source !== frame.contentWindow) return; // only messages from THIS frame
    const msg = event.data;
    if (!msg || msg.kind !== "genui-action") return;
    if (!allowedActions.includes(msg.name)) {
      console.warn("blocked action from sandbox:", msg.name);
      return;
    }
    onAction?.(msg.name, msg.payload);
  }
  window.addEventListener("message", listener);
  container.appendChild(frame);
  return () => window.removeEventListener("message", listener);
}
