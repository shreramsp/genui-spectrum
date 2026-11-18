// The HOST side of the MCP Apps bridge, in the browser. Same page shell as Parts 01-04.
//
// When the agent run delivers CUSTOM "mcp_app" {tool, arguments, result, resource}:
//   1. mount resource.html in <iframe sandbox="allow-scripts"> with a CSP built from resource.meta.ui.csp
//   2. answer the view's ui/initialize; after ui/notifications/initialized send
//      ui/notifications/tool-input and ui/notifications/tool-result
//   3. serve the view's requests: tools/call (proxied to the MCP server via POST /tool),
//      ui/message (becomes the next chat turn), ui/open-link (logged), size-changed (resize)
// Every bridge message is shown in the event log as VIEW→HOST or HOST→VIEW.

import { runAgent } from "/shared/agui-client.js";
import { createShell } from "/shared/shell.js";

const PROTOCOL_VERSION = "2025-06-18";

/** The restrictive default CSP plus any domains the resource declared in _meta.ui.csp. */
export function cspFor(uiMeta = {}) {
  const csp = uiMeta.csp ?? {};
  const domains = (list) => (Array.isArray(list) ? list.filter((d) => typeof d === "string" && !/[;\s'"]/.test(d)) : []);
  const connect = domains(csp.connectDomains);
  const resources = domains(csp.resourceDomains);
  return [
    "default-src 'none'",
    `script-src 'unsafe-inline' ${resources.join(" ")}`,
    `style-src 'unsafe-inline' ${resources.join(" ")}`,
    `img-src data: ${resources.join(" ")}`,
    `connect-src ${connect.length ? connect.join(" ") : "'none'"}`,
  ].join("; ");
}

function withCsp(html, csp) {
  const meta = `<meta http-equiv="Content-Security-Policy" content="${csp.replaceAll('"', "&quot;")}">`;
  const doctype = /^\s*<!doctype[^>]*>/i.exec(html);
  const at = doctype ? doctype[0].length : 0;
  return html.slice(0, at) + meta + html.slice(at); // the policy comes before any element in the view
}

export function startMcpHost(config) {
  let detach = () => {};

  function mountView(shell, { tool, arguments: args, result, resource }) {
    detach();
    const wrap = document.createElement("div");
    wrap.className = "mcp-host-frame";
    const label = document.createElement("div");
    label.className = "mcp-host-label";
    label.textContent = `MCP App · tool ${tool.name} · view ${resource.uri} · sandboxed by the host`;
    const frame = document.createElement("iframe");
    frame.setAttribute("sandbox", "allow-scripts");
    frame.title = resource.uri;
    frame.style.height = "300px";
    frame.srcdoc = withCsp(resource.html, cspFor(resource.meta?.ui));
    wrap.append(label, frame);
    shell.ui.replaceChildren(wrap);

    const post = (msg) => {
      shell.logEvent({ type: "HOST→VIEW", ...msg });
      frame.contentWindow?.postMessage(msg, "*");
    };
    const reply = (id, payload) => post({ jsonrpc: "2.0", id, ...payload });

    async function onMessage(event) {
      if (event.source !== frame.contentWindow) return; // only THIS view
      const msg = event.data;
      if (!msg || msg.jsonrpc !== "2.0") return;
      shell.logEvent({ type: "VIEW→HOST", ...msg });
      const params = msg.params ?? {};
      try {
        switch (msg.method) {
          case "ui/initialize":
            return reply(msg.id, {
              result: {
                protocolVersion: PROTOCOL_VERSION,
                hostInfo: { name: "genui-spectrum-host", version: "0.1.0" },
                hostCapabilities: { serverTools: {}, message: { text: {} }, openLinks: {} },
                hostContext: { theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light", displayMode: "inline", platform: "web", toolInfo: { tool } },
              },
            });
          case "ui/notifications/initialized":
            post({ jsonrpc: "2.0", method: "ui/notifications/tool-input", params: { arguments: args } });
            post({ jsonrpc: "2.0", method: "ui/notifications/tool-result", params: result });
            return;
          case "ui/notifications/size-changed":
            frame.style.height = `${Math.min(Math.max(params.height ?? 300, 120) + 8, 1400)}px`;
            return;
          case "tools/call": {
            const response = await fetch("/tool", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ name: params.name, arguments: params.arguments ?? {} }),
            });
            const body = await response.json();
            if (!response.ok) return reply(msg.id, { error: { code: -32000, message: body.detail ?? "refused" } });
            return reply(msg.id, { result: body });
          }
          case "ui/message": {
            reply(msg.id, { result: {} });
            const text = params.content?.text ?? "";
            if (text) shell.submit(text); // the view's message becomes the next chat turn
            return;
          }
          case "ui/open-link":
            shell.say(`The view asked to open ${params.url} (a real host would ask you first).`);
            return reply(msg.id, { result: {} });
          default:
            if (msg.id !== undefined && msg.method) reply(msg.id, { error: { code: -32601, message: `${msg.method} not supported` } });
        }
      } catch (err) {
        if (msg.id !== undefined) reply(msg.id, { error: { code: -32000, message: String(err) } });
      }
    }
    window.addEventListener("message", onMessage);
    detach = () => window.removeEventListener("message", onMessage);
  }

  createShell({
    part: "05 · MCP Apps",
    ...config,
    async onSubmit(text, shell) {
      await runAgent("/agent", { text }, (event) => {
        shell.logEvent(event);
        if (event.type === "TEXT_MESSAGE_CONTENT") shell.appendSay(event.delta);
        if (event.type === "CUSTOM" && event.name === "mcp_app" && event.value.resource) mountView(shell, event.value);
        if (event.type === "RUN_ERROR") shell.error(event.message);
      });
    },
  });
}
