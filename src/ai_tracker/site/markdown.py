"""A small Markdown-to-HTML renderer for the monthly letters (ai_tracker.letter). No external dependency.

Covers what the letter generator writes: headings (#..####), paragraphs, block quotes (>), lists (- , nested with
two spaces), pipe tables, **bold**, *italic*, `code` and [text](url) links (http(s) or relative only). Every piece of
text is HTML-escaped first, so nothing in a letter can inject markup. Each level-2 section is wrapped in
<section>; `section_ids` maps a heading text to the section's id (the withheld list gets id="withheld").
"""

from __future__ import annotations

import html
import re

_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def inline(text: str) -> str:
    codes: list[str] = []

    def keep(m: re.Match) -> str:
        codes.append(f"<code>{m.group(1)}</code>")
        return f"\x00{len(codes) - 1}\x00"

    s = html.escape(text, quote=True)
    s = _CODE.sub(keep, s)

    def link(m: re.Match) -> str:
        url = html.unescape(m.group(2))
        if not (url.startswith(("https://", "http://")) or not re.match(r"^[a-z][a-z0-9+.-]*:", url, re.I)):
            return m.group(0)
        return f'<a href="{html.escape(url, quote=True)}">{m.group(1)}</a>'

    s = _LINK.sub(link, s)
    s = _BOLD.sub(r"<strong>\1</strong>", s)
    s = _ITALIC.sub(r"<em>\1</em>", s)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], s)


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9åäö]+", "-", text.lower()).strip("-")


def render(md: str, section_ids: dict[str, str] | None = None) -> str:
    section_ids = section_ids or {}
    lines = md.splitlines()
    out: list[str] = []
    in_section = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            level, text = len(m.group(1)), m.group(2).strip()
            if level == 2:
                if in_section:
                    out.append("</section>")
                sid = section_ids.get(text, _slug(text))
                out.append(f'<section id="{html.escape(sid, quote=True)}">')
                in_section = True
            out.append(f"<h{level}>{inline(text)}</h{level}>")
            i += 1
            continue
        if line.startswith(">"):
            block = []
            while i < len(lines) and lines[i].startswith(">"):
                block.append(lines[i][1:].strip())
                i += 1
            out.append(f'<blockquote class="banner recon"><p>{inline(" ".join(block))}</p></blockquote>')
            continue
        if line.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            head = _cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>')
            continue
        if re.match(r"^\s*- ", line):
            items: list[tuple[int, str]] = []
            while i < len(lines) and (re.match(r"^\s*- ", lines[i]) or (lines[i].strip() == "" and i + 1 < len(lines)
                                                                         and re.match(r"^\s+- ", lines[i + 1]))):
                if lines[i].strip():
                    indent = len(lines[i]) - len(lines[i].lstrip())
                    items.append((1 if indent >= 2 else 0, lines[i].strip()[2:]))
                i += 1
            html_items, open_sub = [], False
            for depth, text in items:
                if depth and not open_sub:
                    html_items.append("<ul>")
                    open_sub = True
                elif not depth and open_sub:
                    html_items.append("</ul></li>")
                    open_sub = False
                elif not depth and html_items:
                    html_items.append("</li>")
                html_items.append(f"<li>{inline(text)}" + ("</li>" if depth else ""))
            html_items.append("</ul></li>" if open_sub else "</li>")
            out.append("<ul>" + "".join(html_items) + "</ul>")
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,4}\s|>|\s*- |\s*\|)", lines[i]):
            para.append(lines[i].strip())
            i += 1
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
        else:  # a line no rule takes (e.g. a stray pipe): show it as text
            out.append(f"<p>{inline(line.strip())}</p>")
            i += 1
    if in_section:
        out.append("</section>")
    return "\n".join(out)
