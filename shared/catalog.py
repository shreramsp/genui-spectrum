"""The component catalog: the list of UI parts the model is ALLOWED to use.

The same catalog does three jobs:
  1. prompt     -> catalog_prompt() tells the model which parts exist
  2. validator  -> validate_spec() rejects anything else before it reaches the page
  3. registry   -> shared/web/render.js has one drawing function per name

A UI "spec" is a FLAT map of elements. Children are referenced by id:

    {
      "root": "page",
      "elements": {
        "page":   {"type": "Card",   "props": {"title": "Tokyo"}, "children": ["cost"]},
        "cost":   {"type": "Metric", "props": {"label": "Budget", "value": "$900"}}
      }
    }

A flat map (instead of deeply nested JSON) is easy to validate, easy to patch one
element at a time, and still makes sense while it is only half streamed in.
"""

# prop type codes:  str, num, str[], num[], rows (list of lists).  A trailing "?" = optional.
CATALOG = {
    "Card": {"props": {"title": "str?"}, "children": True, "doc": "A titled box that groups children vertically."},
    "Row": {"props": {}, "children": True, "doc": "Places children side by side."},
    "Text": {"props": {"text": "str"}, "children": False, "doc": "A paragraph of plain text."},
    "Metric": {"props": {"label": "str", "value": "str", "hint": "str?"}, "children": False, "doc": "One big number with a label."},
    "Table": {"props": {"columns": "str[]", "rows": "rows"}, "children": False, "doc": "A table; each row is a list of cell values."},
    "BarChart": {"props": {"title": "str", "labels": "str[]", "values": "num[]"}, "children": False, "doc": "Horizontal bar chart; labels and values have equal length."},
    "Button": {"props": {"label": "str", "action": "str"}, "children": False, "doc": "A button. Clicking it sends `action` back to the agent."},
    # The escape hatch: model-written HTML, drawn inside a sandboxed iframe.
    "HtmlFrame": {
        "props": {"html": "str", "height": "num?", "actions": "str[]?"},
        "children": False,
        "doc": "Custom HTML/CSS/JS in a sandbox. Inline everything; no external URLs. Inside, call sendAction('name') for each name listed in `actions`.",
        "open_ended": True,
    },
}


def _type_ok(value, code):
    code = code.rstrip("?")
    if code == "str":
        return isinstance(value, str)
    if code == "num":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if code == "str[]":
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if code == "num[]":
        return isinstance(value, list) and all(_type_ok(v, "num") for v in value)
    if code == "rows":
        return isinstance(value, list) and all(isinstance(r, list) for r in value)
    return False


def validate_spec(spec, allow_html=False):
    """Return a list of human-readable errors. An empty list means the spec is safe to render."""
    if not isinstance(spec, dict) or not isinstance(spec.get("elements"), dict):
        return ['spec must be an object with "root" and "elements"']
    elements = spec["elements"]
    errors = []
    if spec.get("root") not in elements:
        errors.append(f'root "{spec.get("root")}" is not an element id')

    for el_id, el in elements.items():
        kind = el.get("type") if isinstance(el, dict) else None
        entry = CATALOG.get(kind)
        if entry is None:
            errors.append(f'{el_id}: unknown component "{kind}"')
            continue
        if entry.get("open_ended") and not allow_html:
            errors.append(f"{el_id}: {kind} is not allowed in this mode")
        props = el.get("props", {})
        for name, code in entry["props"].items():
            if name not in props:
                if not code.endswith("?"):
                    errors.append(f'{el_id}: {kind} needs prop "{name}"')
            elif not _type_ok(props[name], code):
                errors.append(f'{el_id}: prop "{name}" should be {code.rstrip("?")}')
        for name in props:
            if name not in entry["props"]:
                errors.append(f'{el_id}: {kind} has no prop "{name}"')
        children = el.get("children", [])
        if children and not entry["children"]:
            errors.append(f"{el_id}: {kind} cannot have children")
        for child in children:
            if child not in elements:
                errors.append(f'{el_id}: child "{child}" does not exist')
        if kind == "BarChart" and _type_ok(props.get("labels"), "str[]") and _type_ok(props.get("values"), "num[]"):
            if len(props["labels"]) != len(props["values"]):
                errors.append(f"{el_id}: labels and values must have the same length")
    return errors


def actions_in(spec):
    """Every action name the spec offers the user (Buttons + HtmlFrame `actions`).

    The server uses this as an allow-list: a click is a REQUEST, not a permission.
    """
    names = set()
    for el in spec.get("elements", {}).values():
        props = el.get("props", {})
        if el.get("type") == "Button":
            names.add(props.get("action"))
        if el.get("type") == "HtmlFrame":
            names.update(props.get("actions", []))
    return names


def catalog_prompt(allow_html=False):
    """The catalog written out for the model's system prompt."""
    lines = []
    for name, entry in CATALOG.items():
        if entry.get("open_ended") and not allow_html:
            continue
        props = ", ".join(f"{p}: {t}" for p, t in entry["props"].items()) or "none"
        kids = " (has children)" if entry["children"] else ""
        lines.append(f"- {name}{kids}  props: {props}. {entry['doc']}")
    return "\n".join(lines)
