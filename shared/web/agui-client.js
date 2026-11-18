// A tiny AG-UI client: POST a RunAgentInput, read the SSE reply, call onEvent per event.
// (The official @ag-ui/client does the same job; we use it in the harness part.)

let threadId = "thread_" + Math.random().toString(36).slice(2, 10);

export async function runAgent(url, { text, state = {}, forwardedProps = {} }, onEvent) {
  const input = {
    threadId,
    runId: "run_" + Math.random().toString(36).slice(2, 10),
    state,
    messages: [{ id: "u_" + Date.now(), role: "user", content: text }],
    tools: [],
    context: [],
    forwardedProps,
  };

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text()}`);

  // SSE = blocks separated by a blank line, each line "data: {json}".
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      const data = block
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");
      if (data) onEvent(JSON.parse(data));
    }
  }
}
