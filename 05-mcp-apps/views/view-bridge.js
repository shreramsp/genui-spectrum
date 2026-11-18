// The VIEW side of the MCP Apps bridge: JSON-RPC 2.0 over postMessage to the host (window.parent).
// No SDK: request() expects an answer, notify() does not.
const pending = new Map();
let nextId = 1;
const resultHandlers = [];

function request(method, params) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    window.parent.postMessage({ jsonrpc: "2.0", id, method, params }, "*");
  });
}
function notify(method, params) {
  window.parent.postMessage({ jsonrpc: "2.0", method, params }, "*");
}

window.addEventListener("message", (event) => {
  if (event.source !== window.parent) return; // only the host talks to this view
  const msg = event.data;
  if (!msg || msg.jsonrpc !== "2.0") return;
  if (msg.method === "ui/notifications/tool-input") document.getElementById("status").textContent = "The host called the tool, waiting for the result…";
  if (msg.method === "ui/notifications/tool-result") resultHandlers.forEach((fn) => fn(msg.params));
  if (msg.method === "ui/resource-teardown") window.parent.postMessage({ jsonrpc: "2.0", id: msg.id, result: {} }, "*");
  if (!msg.method && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
  }
});

const mcpApp = { request, notify, onResult: (fn) => resultHandlers.push(fn) };

// Lifecycle: ui/initialize -> ui/notifications/initialized -> (host sends tool-input, tool-result).
(async () => {
  await request("ui/initialize", {
    appInfo: { name: "genui-trip-view", version: "0.1.0" },
    appCapabilities: { availableDisplayModes: ["inline"] },
    protocolVersion: "2025-06-18",
  });
  notify("ui/notifications/initialized", {});
  new ResizeObserver(() => notify("ui/notifications/size-changed", { height: document.documentElement.scrollHeight })).observe(document.body);
})();
