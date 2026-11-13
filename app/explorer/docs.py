"""Documents of the repository, shown in the app.

The documents are Markdown files. render() turns the subset of Markdown that
they use into HTML: headings, paragraphs, lists, tables, code blocks, and
inline code, bold, italic and links. Everything else is shown as text.
"""
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path

from django.conf import settings

REPO = Path(settings.REPO_DIR)


@dataclass(frozen=True)
class Document:
    key: str
    title: str
    group: str
    path: str

    def text(self):
        return (REPO / self.path).read_text(encoding="utf-8")


DOCUMENTS = {d.key: d for d in (
    Document("project", "Project overview", "Project", "README.md"),
    Document("report", "Toxicity report", "Scientific background", "background/toxicity-report.md"),
    Document("references", "References", "Scientific background", "background/references.md"),
    Document("interventions", "Intervention model", "Scientific background", "background/intervention-model.md"),
    Document("schema", "Data schema", "Components", "schema/README.md"),
    Document("engine", "Data engine", "Components", "engine/README.md"),
    Document("risk-model", "Risk models", "Components", "risk-model/README.md"),
    Document("risk-extensions", "Risk models: possible extensions", "Components", "risk-model/EXTENSIONS.md"),
    Document("app", "App", "Components", "app/README.md"),
    Document("internal", "Internal documentation", "Project", "project/internal-documentation.md"),
    Document("prompts", "Prompt log", "Project", "project/prompting.log"),
)}


def groups():
    """Documents by group, in order: [(group, [Document])]."""
    found = {}
    for d in DOCUMENTS.values():
        found.setdefault(d.group, []).append(d)
    return list(found.items())


def _link(target, base):
    """Address of a link target: a document of the app, an anchor or a web
    address. Other targets, such as files of the repository, give None."""
    if target.startswith(("http://", "https://", "#")):
        return target
    path, _, anchor = target.partition("#")
    resolved = (REPO / base).parent.joinpath(path).resolve()
    for d in DOCUMENTS.values():
        if resolved in ((REPO / d.path).resolve(), (REPO / d.path).resolve().parent) and (
                resolved.is_file() or (REPO / d.path).name == "README.md"):
            return f"../{d.key}/" + (f"#{anchor}" if anchor else "")
    return None


def inline(text, base=""):
    """Inline Markdown of one piece of text as HTML."""
    parts = re.split(r"(`[^`]+`)", text)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) > 2:
            out.append(f"<code>{escape(part[1:-1])}</code>")
            continue
        html = escape(part, quote=False)

        def link(match):
            address = _link(match.group(2), base)
            label = match.group(1)
            return f'<a href="{escape(address)}">{label}</a>' if address else label
        html = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, html)
        html = re.sub(r"&lt;(https?://[^\s&]+)&gt;", r'<a href="\1">\1</a>', html)
        html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])", r"<em>\1</em>", html)
        out.append(html)
    return "".join(out)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def render(text, base=""):
    """Markdown as HTML. Returns (html, [(level, title, anchor)] of the headings)."""
    lines = text.splitlines()
    out, headings, paragraph, i = [], [], [], 0

    def flush():
        if paragraph:
            out.append(f"<p>{inline(' '.join(paragraph), base)}</p>")
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            out.append(f"<pre>{escape(chr(10).join(block))}</pre>")
        elif re.match(r"#{1,6} ", stripped):
            flush()
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped[level:].strip()
            anchor = slug(title)
            headings.append((level, title, anchor))
            out.append(f'<h{level} id="{anchor}">{inline(title, base)}</h{level}>')
        elif stripped.startswith("|") and i + 1 < len(lines) and re.match(r"\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            flush()
            head = "".join(f"<th>{inline(c, base)}</th>" for c in _cells(line))
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append("<tr>" + "".join(f"<td>{inline(c, base)}</td>" for c in _cells(lines[i])) + "</tr>")
                i += 1
            out.append(f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
                       f'<tbody>{"".join(rows)}</tbody></table></div>')
            continue
        elif re.match(r"(\s*)([-*]|\d+\.) ", line):
            flush()
            ordered = bool(re.match(r"\s*\d+\. ", line))
            items = []
            while i < len(lines) and (re.match(r"\s*([-*]|\d+\.) ", lines[i]) or (
                    lines[i].startswith("  ") and lines[i].strip() and items)):
                match = re.match(r"(\s*)([-*]|\d+\.) (.*)", lines[i])
                if match:
                    items.append([len(match.group(1)), match.group(3)])
                else:
                    items[-1][1] += " " + lines[i].strip()
                i += 1
            tag = "ol" if ordered else "ul"
            html, depth = f"<{tag}>", 0
            for n, (indent, content) in enumerate(items):
                level = 1 if indent >= 2 else 0
                if level > depth:
                    html += "<ul>"
                elif level < depth:
                    html += "</li></ul></li>"
                elif n:
                    html += "</li>"
                depth = level
                html += f"<li>{inline(content, base)}"
            html += "</li></ul></li>" if depth else "</li>"
            out.append(html + f"</{tag}>")
            continue
        elif not stripped or re.match(r"=+$|-{3,}$", stripped):
            flush()
        else:
            paragraph.append(stripped)
        i += 1
    flush()
    return "\n".join(out), headings


def page(document):
    """(html, headings) of a document. Plain text files are shown as they are."""
    text = document.text()
    if not document.path.endswith(".md"):
        return f"<pre>{escape(text)}</pre>", []
    return render(text, document.path)
