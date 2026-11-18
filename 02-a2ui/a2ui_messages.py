"""A2UI v0.9.1 for this part: build the four messages and validate them against the official schema.

A2UI (Agent-to-UI, by Google) describes a UI as MESSAGES with two separate halves:

    createSurface     {surfaceId, catalogId}          "a new screen, using this catalog"
    updateComponents  {surfaceId, components: [...]}  STRUCTURE: a flat list joined by ids
    updateDataModel   {surfaceId, path, value}        DATA: a JSON document, addressed by JSON Pointer
    deleteSurface     {surfaceId}

Components show data by BINDING to it: {"text": {"path": "/trip/title"}}. So the agent can
change the data without resending the structure, and vice versa.

The schema files in ../schema are the official v0.9.1 ones (Apache-2.0, from the A2UI
project as bundled by the a2ui-agent-sdk). See schema/NOTICE.md.
"""

import json
from functools import lru_cache
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"
VERSION = "v0.9.1"
BASIC_CATALOG_ID = "https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json"
# Our own catalog id = the Basic Catalog + one custom component, HtmlFrame (used in modes 3 and 4).
TRIP_CATALOG_ID = "https://github.com/shreramsp/genui-spectrum/catalogs/basic_plus_htmlframe.json"

# ------------------------------------------------------------ the four messages


def create_surface(surface_id, catalog_id=BASIC_CATALOG_ID):
    return {"version": VERSION, "createSurface": {"surfaceId": surface_id, "catalogId": catalog_id}}


def update_components(surface_id, components):
    return {"version": VERSION, "updateComponents": {"surfaceId": surface_id, "components": list(components)}}


def update_data_model(surface_id, value, path="/"):
    return {"version": VERSION, "updateDataModel": {"surfaceId": surface_id, "path": path, "value": value}}


def delete_surface(surface_id):
    return {"version": VERSION, "deleteSurface": {"surfaceId": surface_id}}


# ------------------------------------------------------------ official schema validation


@lru_cache(maxsize=1)
def _validators():
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource

    load = lambda name: json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))  # noqa: E731
    envelope, common, catalog = load("server_to_client.json"), load("common_types.json"), load("catalog.json")
    # server_to_client.json refers to "catalog.json" next to itself: plug the Basic Catalog in there.
    placeholder = envelope["$id"].rsplit("/", 1)[0] + "/catalog.json"
    registry = Registry().with_resources(
        [(s["$id"], Resource.from_contents(s)) for s in (envelope, common, catalog)]
        + [(placeholder, Resource.from_contents(catalog))]
    )
    return Draft202012Validator(envelope, registry=registry), registry, catalog


def _component_errors(component):
    """Check one component against its own catalog entry, for a readable error."""
    from jsonschema import Draft202012Validator

    _, registry, catalog = _validators()
    name = component.get("component")
    if name not in catalog["components"]:
        return [f'{component.get("id")}: "{name}" is not in the catalog']
    validator = Draft202012Validator({"$ref": f"{catalog['$id']}#/components/{name}"}, registry=registry)
    return [f'{component.get("id")} ({name}) {"/".join(map(str, e.absolute_path))}: {e.message[:160]}' for e in validator.iter_errors(component)][:3]


HTMLFRAME_KEYS = {"id", "component", "html", "height", "actions", "weight"}


def _htmlframe_errors(component, allow_html):
    if not allow_html:
        return [f'{component.get("id")}: HtmlFrame is not allowed in this mode']
    errors = [f'{component.get("id")}: HtmlFrame has no property "{k}"' for k in component if k not in HTMLFRAME_KEYS]
    if not isinstance(component.get("html"), str):
        errors.append(f'{component.get("id")}: HtmlFrame needs an "html" string')
    if "actions" in component and not all(isinstance(a, str) for a in component["actions"]):
        errors.append(f'{component.get("id")}: HtmlFrame "actions" must be a list of strings')
    return errors


def validate(message, allow_html=False):
    """All errors in one message (empty list = valid).

    Basic Catalog components are checked against the official schema. HtmlFrame, our
    custom component, is checked by _htmlframe_errors because the official schema
    (correctly) does not know it.
    """
    envelope, _, _ = _validators()
    errors = []
    body = message.get("updateComponents")
    if isinstance(body, dict) and isinstance(body.get("components"), list):
        envelope_view = []
        for c in body["components"]:
            if isinstance(c, dict) and c.get("component") == "HtmlFrame":
                errors += _htmlframe_errors(c, allow_html)
                # The official envelope schema does not know HtmlFrame: show it a harmless stand-in.
                envelope_view.append({"id": str(c.get("id")), "component": "Divider"})
            else:
                envelope_view.append(c)
                if isinstance(c, dict):
                    errors += _component_errors(c)
        message = {**message, "updateComponents": {**body, "components": envelope_view}}
    if not errors:
        from jsonschema.exceptions import best_match

        error = best_match(envelope.iter_errors(message))
        if error is not None:
            errors.append(f'{"/".join(map(str, error.absolute_path))}: {error.message[:200]}')
    return errors


# ------------------------------------------------------------ structure checks


def child_ids(component):
    """Every component id this component refers to."""
    ids = []
    for key in ("child", "trigger", "content"):
        if isinstance(component.get(key), str):
            ids.append(component[key])
    children = component.get("children")
    if isinstance(children, list):
        ids += [c for c in children if isinstance(c, str)]
    elif isinstance(children, dict) and "componentId" in children:  # a template
        ids.append(children["componentId"])
    for tab in component.get("tabs", []) or []:
        if isinstance(tab, dict) and isinstance(tab.get("child"), str):
            ids.append(tab["child"])
    return ids


def tree_errors(components):
    """A component list must have a 'root' and every referenced id must exist."""
    by_id = {c.get("id"): c for c in components if isinstance(c, dict)}
    errors = [] if "root" in by_id else ['no component has id "root"']
    for c in by_id.values():
        errors += [f'{c["id"]}: refers to missing id "{ref}"' for ref in child_ids(c) if ref not in by_id]
    return errors


def actions_in(components):
    """Action names the screen offers: Button events + HtmlFrame `actions`. The server's allow-list."""
    names = set()
    for c in components:
        event = (c.get("action") or {}).get("event") if c.get("component") == "Button" else None
        if event and event.get("name"):
            names.add(event["name"])
        if c.get("component") == "HtmlFrame":
            names.update(c.get("actions", []))
    return names


# ------------------------------------------------------------ the catalog, for the prompt

CATALOG_PROMPT = """Components (A2UI v0.9.1 Basic Catalog). Each is a flat object with "id" and "component":
- Text: text, variant? (h1|h2|h3|h4|h5|caption|body)
- Row / Column: children (list of ids), justify? (start|center|end|spaceBetween|spaceAround), align? (start|center|end|stretch)
- List: children (list of ids, or a template {"componentId": "<id>", "path": "/some/list"})
- Card: child (ONE id; wrap several things in a Column)
- Divider: (no props)
- Icon: name (e.g. calendarToday, check, event, favorite, home, info, locationOn, payment, search, star)
- Button: child (id of a Text), variant? (primary|borderless), action {"event": {"name": "<snake_case>", "context": {"<key>": <value or {"path": ...}>}}}
- TextField: label, value {"path": ...}
- CheckBox: label, value {"path": ...}
- Slider: label, min, max, value {"path": ...}
- ChoicePicker: label, options [{"label": "...", "value": "..."}], value {"path": ...} (a list of strings), variant? (mutuallyExclusive|multipleSelection)
- Tabs: tabs [{"title": "...", "child": "<id>"}]

Values: a literal, or {"path": "/json/pointer"} to bind to the data model.
Inside a List template, use RELATIVE paths ({"path": "name"}) to read the current item."""


# ------------------------------------------------------------ transport


def as_agui(messages):
    """A2UI is transport-agnostic. Here each A2UI message rides in an AG-UI CUSTOM event named "a2ui"."""
    from shared.agui import custom

    return [custom("a2ui", m) for m in messages]


def action_from(run_input):
    """The A2UI action message the page put in forwardedProps (or None for a typed request)."""
    return (run_input.forwarded_props or {}).get("a2uiAction")
