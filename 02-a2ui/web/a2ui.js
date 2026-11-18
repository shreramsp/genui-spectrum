// A small A2UI v0.9.1 client: keeps each surface's components + data model, and renders them.
//
//   client.process(message)   apply one of the four messages, then re-render
//   onAction(action)          called with the A2UI action message when a Button is clicked
//
// Supports the Basic Catalog components our prompts use, plus our custom HtmlFrame.

import { mountSandbox } from "/shared/sandbox.js";

// ---------- JSON Pointer (RFC 6901) ----------
const FORBIDDEN = new Set(["__proto__", "constructor", "prototype"]);
const tokens = (path) =>
  path === "" || path === "/"
    ? []
    : path
        .replace(/^\//, "")
        .split("/")
        .map((t) => {
          const k = t.replace(/~1/g, "/").replace(/~0/g, "~");
          if (FORBIDDEN.has(k)) throw new Error(`refused pointer token ${k}`);
          return k;
        });

export function pointerGet(doc, path) {
  let node = doc;
  for (const t of tokens(path)) {
    if (node == null || typeof node !== "object") return undefined;
    node = node[t];
  }
  return node;
}

export function pointerSet(doc, path, value) {
  const ts = tokens(path);
  if (ts.length === 0) return value;
  let node = doc;
  for (const t of ts.slice(0, -1)) node = node[t] ??= {};
  node[ts.at(-1)] = value;
  return doc;
}

// ---------- surfaces ----------
class Surface {
  constructor(id, catalogId) {
    this.id = id;
    this.catalogId = catalogId;
    this.components = new Map();
    this.data = {};
  }
  // A path without a leading "/" is relative to the current template item (scope).
  abs(path, scope) {
    return path.startsWith("/") ? path : `${scope || ""}/${path}`;
  }
  resolve(value, scope) {
    if (value && typeof value === "object" && "path" in value) return pointerGet(this.data, this.abs(value.path, scope));
    if (value && typeof value === "object" && "call" in value) return undefined; // functions not implemented here
    return value;
  }
}

const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = String(text);
  return n;
};
const show = (v) => (v == null ? "" : Array.isArray(v) ? v.join(" · ") : String(v));

const ICONS = { calendarToday: "📅", check: "✔️", event: "🗓", favorite: "❤️", home: "🏠", info: "ℹ️", locationOn: "📍", payment: "💳", search: "🔍", star: "⭐", mail: "✉️", add: "➕" };

export class A2uiClient {
  constructor(container, { onAction } = {}) {
    this.container = container;
    this.onAction = onAction;
    this.surfaces = new Map();
  }

  reset() {
    this.surfaces.clear();
    this.render();
  }

  process(message) {
    if (message.createSurface) {
      const { surfaceId, catalogId } = message.createSurface;
      this.surfaces.set(surfaceId, new Surface(surfaceId, catalogId));
    } else if (message.updateComponents) {
      const s = this.surfaces.get(message.updateComponents.surfaceId);
      if (!s) throw new Error("updateComponents for unknown surface");
      for (const c of message.updateComponents.components) s.components.set(c.id, c); // upsert by id
    } else if (message.updateDataModel) {
      const { surfaceId, path = "/", value } = message.updateDataModel;
      const s = this.surfaces.get(surfaceId);
      if (!s) throw new Error("updateDataModel for unknown surface");
      s.data = pointerSet(s.data, path, structuredClone(value));
    } else if (message.deleteSurface) {
      this.surfaces.delete(message.deleteSurface.surfaceId);
    }
    this.render();
  }

  render() {
    this.container.replaceChildren();
    for (const s of this.surfaces.values()) {
      if (!s.components.has("root")) continue; // nothing to draw yet
      const node = this.renderComponent(s, "root", "", new Set());
      if (node) this.container.appendChild(node);
    }
  }

  // Build the child list of a Row/Column/List: fixed ids, or a template repeated per data item.
  renderChildren(s, children, scope, seen) {
    if (Array.isArray(children)) return children.map((id) => this.renderComponent(s, id, scope, seen));
    if (children && children.componentId) {
      const listPath = s.abs(children.path, scope);
      const items = pointerGet(s.data, listPath) || [];
      return items.map((_, i) => this.renderComponent(s, children.componentId, `${listPath}/${i}`, new Set(seen)));
    }
    return [];
  }

  renderComponent(s, id, scope, seen) {
    const c = s.components.get(id);
    if (!c) return el("span", "a2-missing", "…"); // not streamed in yet
    if (seen.has(id)) return null; // cycle guard
    seen = new Set(seen).add(id);
    const r = (v) => s.resolve(v, scope);
    const bind = (v, value) => {
      if (v && typeof v === "object" && "path" in v) {
        s.data = pointerSet(s.data, s.abs(v.path, scope), value);
        this.render();
      }
    };
    const kids = (list) => this.renderChildren(s, list, scope, seen).filter(Boolean);

    switch (c.component) {
      case "Text": {
        const tag = { h1: "h2", h2: "h2", h3: "h3", h4: "h4", h5: "h5", caption: "small" }[c.variant] || "p";
        return el(tag, `a2-text a2-${c.variant || "body"}`, show(r(c.text)).replace(/^#+\s*/, ""));
      }
      case "Row":
      case "Column":
      case "List": {
        const box = el("div", `a2-${c.component.toLowerCase()} a2-justify-${c.justify || "start"} a2-align-${c.align || "stretch"}`);
        box.append(...kids(c.children));
        return box;
      }
      case "Card": {
        const card = el("section", "c-card");
        const child = this.renderComponent(s, c.child, scope, seen);
        if (child) card.appendChild(child);
        return card;
      }
      case "Divider":
        return el("hr", "a2-divider");
      case "Icon":
        return el("span", "a2-icon", ICONS[r(c.name)] || "•");
      case "Image":
      case "Video":
      case "AudioPlayer":
        return el("div", "a2-media", `[${c.component} not loaded: demos have no network]`);
      case "Button": {
        const b = el("button", `c-button a2-btn-${c.variant || "default"}`);
        b.type = "button";
        const label = this.renderComponent(s, c.child, scope, seen);
        b.textContent = label ? label.textContent : "Button";
        b.onclick = () => {
          const event = c.action?.event;
          if (!event) return;
          const context = {};
          for (const [k, v] of Object.entries(event.context || {})) context[k] = r(v) ?? null; // resolved at click time
          this.onAction?.({ name: event.name, surfaceId: s.id, sourceComponentId: c.id, timestamp: new Date().toISOString(), context });
        };
        return b;
      }
      case "TextField": {
        const wrap = el("label", "a2-field");
        wrap.appendChild(el("span", "a2-label", r(c.label)));
        const input = el("input");
        input.value = show(r(c.value));
        input.onchange = () => bind(c.value, input.value);
        wrap.appendChild(input);
        return wrap;
      }
      case "CheckBox": {
        const wrap = el("label", "a2-check");
        const box = el("input");
        box.type = "checkbox";
        box.checked = !!r(c.value);
        box.onchange = () => bind(c.value, box.checked);
        wrap.append(box, ` ${show(r(c.label))}`);
        return wrap;
      }
      case "Slider": {
        const wrap = el("label", "a2-field");
        const value = Number(r(c.value) ?? c.min ?? 0);
        const head = el("span", "a2-label", `${show(r(c.label))}: ${value}`);
        const input = el("input");
        Object.assign(input, { type: "range", min: c.min ?? 0, max: c.max, value });
        input.oninput = () => (head.textContent = `${show(r(c.label))}: ${input.value}`);
        input.onchange = () => bind(c.value, Number(input.value));
        wrap.append(head, input);
        return wrap;
      }
      case "ChoicePicker": {
        const wrap = el("div", "a2-field");
        wrap.appendChild(el("span", "a2-label", show(r(c.label))));
        const selected = new Set(r(c.value) || []);
        const chips = el("div", "a2-chips");
        for (const opt of c.options || []) {
          const chip = el("button", `chip${selected.has(opt.value) ? " a2-on" : ""}`, show(r(opt.label)));
          chip.type = "button";
          chip.onclick = () => {
            const next = c.variant === "multipleSelection" ? new Set(selected) : new Set();
            next.has(opt.value) ? next.delete(opt.value) : next.add(opt.value);
            bind(c.value, [...next]);
          };
          chips.appendChild(chip);
        }
        wrap.appendChild(chips);
        return wrap;
      }
      case "Tabs": {
        const wrap = el("div", "a2-tabs");
        const bar = el("div", "a2-chips");
        const body = el("div");
        (c.tabs || []).forEach((tab, i) => {
          const b = el("button", "chip", show(r(tab.title)));
          b.type = "button";
          b.onclick = () => {
            bar.querySelectorAll(".chip").forEach((x) => x.classList.remove("a2-on"));
            b.classList.add("a2-on");
            body.replaceChildren(this.renderComponent(s, tab.child, scope, seen) || "");
          };
          bar.appendChild(b);
          if (i === 0) queueMicrotask(() => b.click());
        });
        wrap.append(bar, body);
        return wrap;
      }
      case "HtmlFrame": {
        // Our custom component (catalog TRIP_CATALOG_ID): model-written HTML in the sandbox.
        const box = el("div", "c-htmlframe");
        box.appendChild(el("div", "c-htmlframe-tag", "AI-generated region · sandboxed"));
        mountSandbox(box, c.html, {
          height: c.height || 360,
          allowedActions: c.actions || [],
          onAction: (name, payload) =>
            this.onAction?.({ name, surfaceId: s.id, sourceComponentId: c.id, timestamp: new Date().toISOString(), context: payload || {} }),
        });
        return box;
      }
      default:
        return el("div", "c-error", `Unknown component: ${c.component}`);
    }
  }
}
