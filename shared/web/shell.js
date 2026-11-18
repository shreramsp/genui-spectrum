// The page layout every demo shares: prompt box, agent text, UI area and a live event log.
// Each demo's app.js only decides what to DO with events - the layout is the same everywhere,
// so in the videos you can compare modes side by side.

const $ = (tag, cls, text) => {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text != null) el.textContent = text;
  return el;
};

export function createShell({ part, mode, title, blurb, examples = [], onSubmit }) {
  document.title = `${part} · ${mode}`;
  const app = document.getElementById("app");

  const header = $("header", "shell-header");
  const tags = $("div", "shell-tags");
  tags.append($("span", "tag", part), $("span", "tag tag-mode", mode));
  header.append(tags, $("h1", null, title), $("p", "shell-blurb", blurb));

  const form = $("form", "shell-form");
  const input = $("input");
  input.placeholder = examples[0] || "Ask the agent…";
  input.value = examples[0] || "";
  const go = $("button", null, "Run");
  go.type = "submit";
  form.append(input, go);
  const chips = $("div", "shell-chips");
  examples.forEach((ex) => {
    const chip = $("button", "chip", ex);
    chip.type = "button";
    chip.onclick = () => {
      input.value = ex;
      form.requestSubmit();
    };
    chips.appendChild(chip);
  });

  const main = $("main", "shell-main");
  const left = $("div", "shell-left");
  const say = $("div", "shell-say");
  const ui = $("div", "shell-ui");
  ui.appendChild($("p", "shell-empty", "The generated UI appears here."));
  left.append(say, ui);

  const right = $("aside", "shell-log");
  const logHead = $("div", "shell-log-head");
  logHead.append($("strong", null, "AG-UI events"), $("span", "shell-count", "0"));
  const log = $("ol", "shell-events");
  right.append(logHead, log);
  main.append(left, right);

  app.append(header, form, chips, main);

  let count = 0;
  const shell = {
    ui,
    say(text) {
      say.textContent = text;
      say.hidden = !text;
    },
    appendSay(delta) {
      say.hidden = false;
      say.textContent += delta;
    },
    clearUI() {
      ui.replaceChildren();
    },
    error(message) {
      ui.replaceChildren($("div", "c-error", message));
    },
    logEvent(event) {
      count += 1;
      logHead.querySelector(".shell-count").textContent = count;
      const item = $("li", `ev ev-${event.type.split("_")[0].toLowerCase()}`);
      const details = $("details");
      const summary = $("summary");
      summary.append($("span", "ev-type", event.type), $("span", "ev-hint", hint(event)));
      details.append(summary, $("pre", null, JSON.stringify(event, null, 2)));
      item.appendChild(details);
      log.appendChild(item);
      log.scrollTop = log.scrollHeight;
    },
    resetLog() {
      count = 0;
      log.replaceChildren();
    },
    setBusy(busy) {
      go.disabled = busy;
      go.textContent = busy ? "Running…" : "Run";
    },
    // Run an action as a new agent turn (used by buttons in the generated UI).
    submit(text) {
      input.value = text;
      form.requestSubmit();
    },
  };

  form.onsubmit = async (e) => {
    e.preventDefault();
    if (!input.value.trim()) return;
    shell.setBusy(true);
    shell.resetLog();
    shell.say("");
    try {
      await onSubmit(input.value.trim(), shell);
    } catch (err) {
      shell.error(String(err));
    } finally {
      shell.setBusy(false);
    }
  };
  return shell;
}

function hint(e) {
  if (e.delta && typeof e.delta === "string") return JSON.stringify(e.delta.slice(0, 40));
  if (e.toolCallName) return e.toolCallName;
  if (e.name) return e.name;
  if (e.type === "STATE_DELTA") return `${e.delta.length} op(s)`;
  if (e.type === "STATE_SNAPSHOT") return Object.keys(e.snapshot || {}).join(", ");
  if (e.message) return e.message;
  return "";
}
