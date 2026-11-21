# genui-spectrum, explained in plain English

A step-by-step guide to what this project is, why it matters, and what every part does.
No coding knowledge needed. Read it top to bottom; each step builds on the one before.

---

## Step 1 · The big idea in one minute

Today, when you ask an AI a question, it answers with **text**.

> "Your Tokyo trip: Day 1, visit Senso-ji temple. Day 2, Shibuya. Budget about $735…"

That's fine, but a **screen** would be better: a card for each day, a chart of the budget, a button that says "Make it cheaper".

**Generative UI** means the AI answers with a **screen you can use**, not just text.
"UI" means *user interface*: buttons, cards, tables, charts, anything you see and click.

This project shows **how to build that**, using **six different technologies**, each in **four different ways**.

---

## Step 2 · Why companies care (the business value)

Think about apps you already use:

- **A travel site** could answer "plan my trip" with an itinerary you can edit, not a wall of text.
- **A bank's assistant** could answer "show my spending" with a real chart.
- **A support chatbot** could show a return form instead of saying "please go to Settings, then Orders, then…".
- **An internal company tool** could build the exact dashboard a manager asks for, on the spot.

The value:

| Benefit | Why it matters |
|---|---|
| **Faster for users** | A chart is understood in 2 seconds; a paragraph of numbers takes 30 |
| **Fewer screens to build** | Developers don't have to design a page for every possible question |
| **Actions, not just answers** | A button can book, save or update right away |
| **Personal** | Each person gets a screen made for *their* question |

But there are real risks, and this project is mostly about handling them:

| Risk | Example |
|---|---|
| **Safety** | AI-written code could try to steal data or do something harmful |
| **Quality** | The AI might produce a broken or ugly screen |
| **Brand consistency** | Every screen should still look like *your* company's app |
| **Cost** | Every AI call costs money |

So the central question of the whole project is:

> **How much should the AI be allowed to decide about the screen?**

---

## Step 3 · The four modes: a spectrum from "safe" to "free"

Every part of the project shows the same four modes. They're the heart of the project, so take your time here.

Think of **decorating a room** with the AI as your decorator.

### Mode 1 · Static: "The furniture is already there"
The developer builds the screens in advance. The AI only **chooses which one** to show and **fills in the information**.
- *Room analogy:* the room is fully furnished; the AI just puts things on the shelves.
- *Good:* safest, always looks right, cheapest.
- *Bad:* the AI can only show what developers built ahead of time.
- *Real-world use:* a weather card, a flight status card, a receipt.

### Mode 2 · Declarative: "Choose from the catalog"
The developer gives the AI a **catalog** of approved building blocks (card, chart, table, button…). The AI **arranges** them into a screen. The system **checks** the AI's design before showing it.
- *Room analogy:* the AI picks furniture from an IKEA catalog and arranges it, but can't build its own.
- *Good:* flexible, still safe, still matches your brand.
- *Bad:* limited to the blocks in the catalog.
- *Real-world use:* custom dashboards, reports, comparison pages.

### Mode 3 · Open-ended: "Build anything, in a sealed room"
No catalog. The AI **writes the whole screen itself**, as real web code. Because nobody can fully check free-written code, it runs inside a **sandbox**: a sealed box with no internet and no access to the rest of the app.
- *Room analogy:* the AI builds custom furniture from scratch, in a separate sealed room.
- *Good:* can make anything: games, calculators, unusual widgets.
- *Bad:* riskier, slower, costs more, may not match your style.
- *Real-world use:* one-off tools, like "make me a tip calculator" or "a quiz about Japan".

### Mode 4 · Mixed: "Catalog furniture plus one custom piece"
Mostly catalog blocks (safe and consistent), plus **one** sandboxed custom piece where it's really needed. And it's **interactive**: when you click a button, the AI updates the screen. Every click is checked against a list of allowed actions (an **allow-list**).
- *Room analogy:* an IKEA room with one handmade art piece, and you can ask the decorator to change things.
- *Good:* the best balance. It's what many experts recommend as the default.
- *Real-world use:* a trip planner with a standard itinerary plus a custom "how packed should each day be?" slider.

### The spectrum at a glance

```
SAFE & CONTROLLED  ◀──────────────────────────────▶  FREE & FLEXIBLE
   Static        Declarative        Mixed        Open-ended
 (pick a card)  (arrange blocks)  (blocks + 1)  (write anything)
```

**One important rule used everywhere in the project:**
> A click is a **request**, not a **permission**.
> When a user clicks a button the AI created, the server double-checks that the button was really offered before doing anything.

---

## Step 4 · The example app: a trip planner

To make comparisons easy, **every demo is the same app**: you type *"Plan 3 days in Tokyo"* and get a trip screen.

Why the same app 24 times? Because then **the only thing that changes is the technology or the mode**, so the differences are easy to see.

Every demo page looks the same:
- **Top:** a box to type your request, and example buttons.
- **Left:** the screen the AI made.
- **Right:** an **event log**, a live list of every step happening behind the scenes. That log is like the "receipt" of what the AI did.

---

## Step 5 · Words you'll hear (mini glossary)

| Word | Plain meaning |
|---|---|
| **AI model** | The "brain" that writes answers. Here: Google's **Gemini** |
| **Agent** | An AI that can take steps and use tools, not just chat |
| **Tool** | A function the AI is allowed to call, like "show a card" or "read a file" |
| **Catalog** | The approved list of building blocks |
| **Spec** | The AI's *description* of a screen ("a card, inside it a chart…"). The app then draws it |
| **Validation** | Checking the AI's spec follows the rules before showing it |
| **Sandbox** | A sealed box where untrusted code runs safely |
| **Streaming** | Sending the answer piece by piece, so the screen can appear gradually |
| **Action** | What happens when a user clicks something the AI made |
| **Allow-list** | The list of actions that are permitted; everything else is blocked |
| **Host** | An app that displays someone else's screen (like a chat app) |
| **Server** | The program in the background that talks to the AI |
| **Offline mode** | Runs without the AI, replaying saved answers, free for testing |

---

## Step 6 · The six parts, one by one

Each part answers a **different question**. They are not "bigger versions" of each other. They're different tools that solve different problems.

### Part 01 · AG-UI: *"How does the AI's work reach the screen?"*

**What it is:** a standard way to send the AI's progress to a web page, step by step, as small labeled messages ("started", "here's some text", "I'm calling a tool", "here's the screen", "finished").
**Analogy:** a **waiter** carrying dishes from the kitchen (the AI) to your table (the web page), one at a time, each labeled.
**Why it matters:** without a standard, every company invents its own messy connection. AG-UI is shared by many tools, so parts work together.
**Its four modes:**
- **Static:** the page has 3 ready-made cards; the AI picks one by "calling a tool".
- **Declarative:** the AI designs a screen from the catalog; it's sent as the page's "shared state".
- **Open-ended:** the AI's own web code is sent as a special message and run in a sandbox.
- **Mixed:** catalog + one sandbox piece; after a click, only the **changes** are sent (like sending "move the sofa" instead of redelivering the whole room).

### Part 02 · A2UI: *"Can the layout and the information travel separately?"*

**What it is:** Google's open format for describing screens. Its big idea: the **layout** ("a title goes here, a list goes there") and the **information** ("the title is Tokyo") are sent **separately**.
**Analogy:** a **form with blanks**. First you send the empty form; later you fill in the blanks, and you can update just one blank without resending the whole form.
**Why it matters:** updates are small and fast, and the layout can be trusted while only the data changes.
**Its four modes:**
- **Static:** my hand-made empty screen appears instantly; the AI only supplies the information.
- **Declarative:** the AI writes the layout too, and it's checked against Google's official rules.
- **Open-ended:** A2UI deliberately has no "run any code" block, so I added a custom one (HtmlFrame). That shows how you *extend* a format safely.
- **Mixed:** after a click, the AI resends **only the parts that changed**.

### Part 03 · OpenUI: *"Can the screen draw while the AI is still writing?"*

**What it is:** a very **short language** for describing screens, one line per piece, like a shopping list.
**Analogy:** **live subtitles**. You see the screen appear line by line while the AI is still "talking", instead of waiting for the whole thing.
**Why it matters:** **speed**. Users see something useful immediately, and shorter descriptions also mean lower AI cost.
**Its four modes:**
- **Static:** a hand-written screen in this language; the AI just provides the data.
- **Declarative:** the AI writes the language itself, and you watch the screen grow.
- **Open-ended:** the AI's web code streams inside one line, then runs in the sandbox.
- **Mixed:** after a click, the AI resends only the changed lines.

### Part 04 · json-render: *"Can one screen description work in different places?"*

**What it is:** a way to build a screen description in **small steps** (tiny edits, one per line). The same description can be drawn on a **web page** and also as **text in a terminal**.
**Analogy:** **sheet music**. The same score can be played on a piano or a guitar. Here, the same screen description can be "played" in a browser or a terminal.
**Why it matters:** write once, show anywhere: web, mobile, terminal, chat. Also, the list of allowed actions lives inside the catalog itself, so the AI is told exactly what it may do.
**Its four modes:**
- **Static:** my fixed screen; the AI fills in the data, which streams in one day at a time.
- **Declarative:** the AI builds the screen as a stream of tiny edits.
- **Open-ended:** a sandbox block; the terminal version can only say "open the web page", which shows the limit of free-form code.
- **Mixed:** buttons use actions declared in the catalog; clicks lead to small edits only.

### Part 05 · MCP Apps: *"Can my screen appear inside someone else's app?"*

**What it is:** **MCP** (Model Context Protocol) is a standard way to give AI apps new tools. **MCP Apps** adds screens to those tools, so a chat app (like Claude Desktop) can show **your** screen inside **its** chat.
**Analogy:** an **app store for chat**. Instead of building a whole website, you ship a small "app" that runs inside a popular chat app.
**Why it matters:** **distribution**. Millions of people already use chat apps; your company's screen can appear right there. The chat app (the "host") stays in control of safety.
**Its four modes:**
- **Static:** a hand-made screen shipped inside the MCP server; the chat app's AI supplies the data.
- **Declarative:** *two* AIs work together. The host's AI picks the tool, and my server's AI designs the screen.
- **Open-ended:** the AI's code runs **two sandboxes deep** (the host's box, plus my box inside it).
- **Mixed:** the screen can ask the host to call a tool; both the host and my server check the request.

### Part 06 · Harness: *"Can an AI agent research first, then show a screen?"*

**What it is:** an **agent loop**, the same idea behind coding assistants. The AI can take several steps: look at files, read them, think, and finally draw a screen with what it found.
**Analogy:** a **research assistant**: they go to the filing cabinet, read the documents, and then hand you a one-page summary with charts.
**Why it matters:** real business screens need **real data** (your expenses, your bookings), not made-up examples. Here the AI reads actual trip files and shows the true total ($1,433).
**Safety:** it can only read **one small folder**, at most **6 steps**, small files only, and every call goes through the **spending limit**.
**Its four modes:**
- **Static:** after reading files, it picks a ready-made budget or bookings view.
- **Declarative:** it designs its own screen. If the design is wrong, the error comes back to it and it fixes itself.
- **Open-ended:** it writes a custom "what if I cut my spending?" widget from the real numbers.
- **Mixed:** a click continues the same conversation; the agent can read *another* file before updating the screen.

---

## Step 7 · How the six parts fit together

They're layers of the same system, not competitors:

```
   WHO DECIDES THE SCREEN?        → the 4 modes (static … open-ended)
   HOW IS THE SCREEN DESCRIBED?   → A2UI, OpenUI, json-render (Parts 02–04)
   HOW DOES IT TRAVEL?            → AG-UI (Part 01)
   WHERE IS IT SHOWN?             → your own page, or someone else's app (Part 05)
   WHERE DOES THE DATA COME FROM? → an agent that researches first (Part 06)
```

A real product might combine them. For example: an agent (06) that reads your data, describes the screen in A2UI (02), sends it through AG-UI (01) to your website, *and* ships the same thing as an MCP App (05) for chat users.

---

## Step 8 · How the project keeps things safe and cheap

| Protection | What it does |
|---|---|
| **Catalog + validation** | The AI can only use approved blocks; broken designs are sent back to be fixed |
| **Sandbox** | Free-written code runs sealed off, with no internet and no access to the rest of the app |
| **Allow-list** | Clicks are checked; anything not offered is blocked |
| **Agent limits** | One folder, 6 steps, small files |
| **Spending cap** | Every AI call is blocked if it *could* push the total past **$0.20** |
| **Offline mode + tests** | 70 automatic tests check everything without spending a cent |

Cost reality: building and testing all six parts with the real AI cost about **one cent**. Each demo run costs about **a tenth of a cent**.

---

## Step 9 · What I built (the deliverables)

- **24 working demos**: 6 technologies × 4 modes, all the same trip-planner app.
- **A hub page** that links to all 24 (`python shared/run_all.py` → localhost:8000).
- **A README in every part** explaining the code, with screenshots.
- **70 automatic tests**, plus a checker that opens every demo in a real browser.
- **Shared building blocks** written once and reused: the AI connection, the catalog, the sandbox, the spending cap.
- **A safety-first design**: validation, sandboxing, allow-lists, limits, cost cap.

---

## Step 10 · Explain it in 30 seconds (your elevator pitch)

> "AI usually answers with text. My project shows how an AI can answer with an interactive screen instead, using one trip-planner app built six ways, with AG-UI, A2UI, OpenUI, json-render, MCP Apps and an agent harness. Each one has four modes, from safe (the AI fills in a ready-made card) to free (the AI writes its own code in a sandbox), plus a mixed mode with clickable actions. The main lesson: give the AI as much freedom as you need, but always validate, sandbox and check every click."

---

## Step 11 · Quick self-quiz

1. **What's the difference between static and declarative?**
   Static: the AI picks a ready-made screen. Declarative: the AI arranges approved blocks into a new screen.
2. **Why does open-ended mode need a sandbox?**
   Because AI-written code can't be fully checked, so it must run where it can't do harm.
3. **Why is mixed mode often the best choice?**
   Mostly safe, consistent blocks, plus freedom exactly where it's needed, and it supports clicks.
4. **What does "a click is a request, not a permission" mean?**
   The server double-checks every click against what it actually offered.
5. **Which part is about the AI's messages reaching the page?** Part 01, AG-UI.
6. **Which part sends layout and information separately?** Part 02, A2UI.
7. **Which part draws while the AI is still writing?** Part 03, OpenUI.
8. **Which part shows one screen on both the web and a terminal?** Part 04, json-render.
9. **Which part puts your screen inside someone else's chat app?** Part 05, MCP Apps.
10. **Which part reads real files before drawing?** Part 06, Harness.

---

*Next: open the hub (`python shared/run_all.py` → http://localhost:8000) and click through one part's four modes. Watch the event log on the right; it's the clearest way to see each difference.*
