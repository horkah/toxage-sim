"""Model parameters: defaults from the repository, changes of the user.

The defaults are the JSON files of the engine and the risk model. The user
can change single values in the app; only the changed values are stored, as
{path: value} per file. A path is the keys from the top of the file, joined
by "/". Removing a stored value brings the default back.
"""
import copy
import json
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from .models import Setting

REPO = Path(settings.REPO_DIR)
SEP = "/"
# Titles of top-level groups whose key is an abbreviation.
GROUP_TITLES = {"ild": "Lung toxicity (ILD)", "severe_toxicity_90d": "Severe toxicity, 90 days",
                "cardiovascular": "Cardiovascular events"}
# Keys whose text explains a value. They are shown, not edited.
NOTES = ("basis", "description", "source", "comment")


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    path: str
    root: str = ""       # key of the file under which the parameters lie
    intro: str = ""

    def default(self):
        with open(REPO / self.path, encoding="utf-8") as f:
            data = json.load(f)
        return data[self.root] if self.root else data


SOURCES = {s.key: s for s in (
    Source("regimens", "Regimens", "engine/config/regimens.json", "regimens",
           "Reference values of the regimens from the trials: event rates, treatment duration, survival."),
    Source("parameters", "Simulation", "engine/config/parameters.json", "",
           "Population, hazards of adverse events, actions, survival, measurements and calibration of the engine."),
    Source("interventions", "Interventions", "engine/config/interventions.json", "",
           "Participation, detection, early treatment, consequences, costs, quality of life and the scenarios."),
    Source("risk", "Risk models", "risk-model/config/models.json", "",
           "Coefficients, reference rates and risk categories of the risk models shown in the explorer."),
)}
ENGINE = ("regimens", "parameters", "interventions")


def is_leaf(value):
    return not isinstance(value, dict)


def leaves(data, prefix=()):
    """All values of a nested dictionary as (path tuple, value), in file order."""
    for key, value in data.items():
        if is_leaf(value):
            yield prefix + (key,), value
        else:
            yield from leaves(value, prefix + (key,))


def is_note(path):
    return path[-1] in NOTES


def anchor(path):
    """Id of the row of a parameter on the parameters page."""
    return "param-" + path.replace(SEP, "--")


def changes(key):
    setting = Setting.objects.filter(pk=key).first()
    return dict(setting.value) if setting else {}


def all_changes():
    """{source key: {path: value}} of everything that differs from the defaults."""
    stored = {s.key: s.value for s in Setting.objects.all()}
    return {key: dict(stored[key]) for key in SOURCES if stored.get(key)}


def apply(data, changed):
    """A copy of data with the changed values set."""
    data = copy.deepcopy(data)
    for path, value in changed.items():
        node = data
        *parents, last = path.split(SEP)
        try:
            for part in parents:
                node = node[part]
            if last in node:
                node[last] = value
        except (KeyError, TypeError):
            continue    # the path no longer exists in the defaults
    return data


def effective(key, changed=None):
    """Parameters of one source with the changes of the user."""
    return apply(SOURCES[key].default(), changes(key) if changed is None else changed)


def parse(text, default):
    """Turn the text of a form field into a value of the type of the default.
    Raises ValueError with a readable message."""
    text = text.strip()
    if isinstance(default, bool):
        if text not in ("true", "false"):
            raise ValueError("must be true or false")
        return text == "true"
    if isinstance(default, (int, float)):
        try:
            value = float(text)
        except ValueError:
            raise ValueError("must be a number") from None
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("must be a finite number")
        return int(value) if value == int(value) and isinstance(default, int) else value
    if isinstance(default, str):
        return text
    try:
        value = json.loads(text)
    except ValueError:
        raise ValueError("must be valid JSON, e.g. [1, 2] or null") from None
    if isinstance(default, list) and not isinstance(value, list):
        raise ValueError("must be a list, e.g. [1, 2]")
    return value


def show(value):
    """Text of a value in a form field."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, str)):
        return str(value)
    return json.dumps(value)


def save(key, posted):
    """Store the posted values {path: text} of one source. Values equal to
    the default are not stored. Returns {path: error message}."""
    default = dict((SEP.join(p), v) for p, v in leaves(SOURCES[key].default()) if not is_note(p))
    changed, errors = changes(key), {}
    for path, text in posted.items():
        if path not in default:
            continue
        try:
            value = parse(text, default[path])
        except ValueError as error:
            errors[path] = str(error)
            continue
        if value == default[path]:
            changed.pop(path, None)
        else:
            changed[path] = value
    _store(key, changed)
    return errors


def reset(key=None, path=None):
    """Bring defaults back: one value, one source, or everything."""
    if key is None:
        Setting.objects.filter(pk__in=SOURCES).delete()
    elif path is None:
        Setting.objects.filter(pk=key).delete()
    else:
        changed = changes(key)
        changed.pop(path, None)
        _store(key, changed)


def _store(key, changed):
    if changed:
        Setting.objects.update_or_create(pk=key, defaults={"value": changed})
    else:
        Setting.objects.filter(pk=key).delete()


def form(key, posted=None, errors=None):
    """Groups of one source for the form: [{"title", "rows": [row], "changed": n}].
    A row has path, label, default, value, changed, note, error, kind."""
    default = SOURCES[key].default()
    changed = changes(key)
    notes = {SEP.join(p[:-1]): v for p, v in leaves(default) if is_note(p) and isinstance(v, str)}
    groups = {}
    for path, value in leaves(default):
        if is_note(path):
            continue
        name = SEP.join(path)
        current = changed.get(name, value)
        group = groups.setdefault(path[0], {"title": GROUP_TITLES.get(path[0], path[0].replace("_", " ").capitalize()),
                                            "anchor": f"group-{path[0]}",
                                            "rows": [], "changed": 0,
                                            "note": notes.get(path[0], "")})
        group["changed"] += name in changed
        group["rows"].append({
            "path": name,
            "anchor": anchor(name),
            "label": " › ".join(part.replace("_", " ") for part in path[1:]) or path[0].replace("_", " "),
            "default": show(value),
            "value": (posted or {}).get(name, show(current)),
            "changed": name in changed,
            "note": notes.get(SEP.join(path[:-1]), "") if len(path) > 2 else "",
            "error": (errors or {}).get(name, ""),
            "kind": "bool" if isinstance(value, bool) else "number" if isinstance(value, (int, float)) else "text",
        })
    return list(groups.values())


def engine_config(changed=None):
    """Configuration for the engine with the changes of the user. changed is
    {source key: {path: value}}; the default is what is stored."""
    from engine import generate
    changed = all_changes() if changed is None else changed
    return {
        "regimens": apply(SOURCES["regimens"].default(), changed.get("regimens", {})),
        "parameters": apply(SOURCES["parameters"].default(), changed.get("parameters", {})),
        "interventions": apply(SOURCES["interventions"].default(), changed.get("interventions", {})),
        "calibration": generate.load_calibration(),
    }


def needs_calibration(changed):
    """True if changes touch what the calibration of the event rates depends on."""
    return any(changed.get(key) for key in ("regimens", "parameters"))
