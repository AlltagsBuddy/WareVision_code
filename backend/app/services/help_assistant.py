"""Hilfe-Wissensbasis und KI-Assistent für funktionale Fragen zu WareVision.

- Wissensbasis: Markdown-Dateien in app/assets/help (ein Kapitel je Datei, Abschnitte mit „## “).
- Ohne API-Key: Stichwortsuche in der Wissensbasis (keine Daten verlassen den Server).
- Mit API-Key: Claude (Anthropic Messages API) beantwortet die Frage ausschließlich auf Basis der
  Wissensbasis. Personenbezogene Muster (E-Mail, IBAN, Telefon, Kennzeichen) werden vorher entfernt.
"""

import json
import logging
import math
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

HELP_DIR = Path(__file__).resolve().parent.parent / "assets" / "help"
# Überschreibbar (z. B. für Tests oder einen Firmen-Proxy)
ANTHROPIC_URL = os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-haiku-5-5"
MAX_ANSWER_TOKENS = 900
REQUEST_TIMEOUT_SECONDS = 30
MAX_HISTORY_TURNS = 6
MAX_QUESTION_CHARS = 1000
SEARCH_RESULTS = 3

# Häufige deutsche Füllwörter, die bei der Suche ignoriert werden
_STOPWORDS = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem", "einer", "und", "oder", "aber",
    "wie", "was", "wo", "wann", "warum", "wieso", "kann", "können", "ich", "du", "wir", "man", "mit", "von",
    "zu", "zum", "zur", "im", "in", "auf", "an", "am", "für", "ist", "sind", "wird", "werden", "bei", "nicht",
    "mein", "meine", "es", "sich", "auch", "noch", "nur", "so", "dass", "da", "hier", "bitte", "gibt", "habe",
    "hat", "welche", "welcher", "welches", "muss", "soll", "will", "mir", "mich", "etwas", "einem",
}

# Muster für personenbezogene Daten, die nicht an die KI gesendet werden
_REDACTIONS = [
    (re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+"), "[E-Mail entfernt]"),
    (re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,3})?\b"), "[IBAN entfernt]"),
    (re.compile(r"(?<!\w)(?:\+49|0049|0)[\d\s/()-]{6,}\d"), "[Telefon entfernt]"),
    (re.compile(r"\b[A-ZÄÖÜ]{1,3}[-\s][A-Z]{1,2}\s?\d{1,4}[EH]?\b"), "[Kennzeichen entfernt]"),
]


@dataclass
class HelpSection:
    """Abschnitt der Hilfe."""

    id: str
    article_id: str
    article_title: str
    heading: str
    text: str
    _tokens: set[str] = field(default_factory=set, repr=False)
    _heading_tokens: set[str] = field(default_factory=set, repr=False)
    _title_tokens: set[str] = field(default_factory=set, repr=False)


@dataclass
class HelpArticle:
    """Kapitel der Hilfe."""

    id: str
    title: str
    sections: list[HelpSection]


def _normalize(word: str) -> str:
    """Wort vereinfachen: klein, Umlaute vereinheitlichen, einfache Endungen kürzen."""
    w = word.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    for suffix in ("ungen", "ung", "en", "er", "es", "e", "n", "s"):
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            return w[: -len(suffix)]
    return w


def _tokens(text: str) -> set[str]:
    """Suchbegriffe aus einem Text."""
    words = re.findall(r"[A-Za-zÄÖÜäöüß0-9]+", text)
    return {_normalize(w) for w in words if w.lower() not in _STOPWORDS and len(w) > 1}


def _slug(text: str) -> str:
    """Kurze ID aus einer Überschrift."""
    s = text.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


@lru_cache(maxsize=1)
def load_articles() -> tuple[HelpArticle, ...]:
    """Alle Hilfekapitel aus den Markdown-Dateien laden (einmalig, danach zwischengespeichert)."""
    articles: list[HelpArticle] = []
    for path in sorted(HELP_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        title_match = re.search(r"^# (.+)$", raw, re.M)
        title = title_match.group(1).strip() if title_match else path.stem
        article_id = re.sub(r"^\d+_", "", path.stem)
        sections: list[HelpSection] = []
        for block in re.split(r"^## ", raw, flags=re.M)[1:]:
            heading, _, body = block.partition("\n")
            heading = heading.strip()
            body = body.strip()
            sec = HelpSection(
                id=f"{article_id}--{_slug(heading)}",
                article_id=article_id,
                article_title=title,
                heading=heading,
                text=body,
            )
            sec._heading_tokens = _tokens(heading)
            sec._title_tokens = _tokens(title)
            sec._tokens = _tokens(body) | sec._heading_tokens | sec._title_tokens
            sections.append(sec)
        articles.append(HelpArticle(id=article_id, title=title, sections=sections))
    return tuple(articles)


def all_sections() -> list[HelpSection]:
    """Alle Abschnitte aller Kapitel."""
    return [s for a in load_articles() for s in a.sections]


def search(query: str, limit: int = SEARCH_RESULTS) -> list[HelpSection]:
    """Stichwortsuche: Abschnitte nach Übereinstimmung mit der Frage sortieren."""
    q = _tokens(query)
    if not q:
        return []
    scored: list[tuple[float, HelpSection]] = []

    sections = all_sections()
    total = len(sections)

    def weight(term: str) -> float:
        """Seltene Begriffe zählen mehr als häufige (z. B. „aufbewahren“ mehr als „Rechnung“)."""
        df = sum(1 for sec in sections if term in sec._tokens) or 1
        return 1.0 + math.log(total / df)

    def prefix_hit(term: str, tokens: set[str]) -> bool:
        """Teilwort-Treffer, z. B. „aufbewahr“ ~ „aufbewahrungsfrist“."""
        return len(term) >= 5 and any(len(tok) >= 5 and (tok.startswith(term) or term.startswith(tok)) for tok in tokens)

    weights = {t: weight(t) for t in q}
    for sec in sections:
        hits = 0.0
        for t in q:
            w = weights[t]
            if t in sec._heading_tokens:
                hits += 3 * w      # Treffer in der Abschnittsüberschrift zählen am meisten
            elif prefix_hit(t, sec._heading_tokens):
                hits += 2 * w
            elif t in sec._tokens:
                hits += (0.75 if t in sec._title_tokens else 1) * w
            elif prefix_hit(t, sec._tokens):
                hits += 0.5 * w
        if hits:
            scored.append((hits, sec))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:limit]]


def redact(text: str) -> tuple[str, bool]:
    """Personenbezogene Muster entfernen. Gibt (Text, wurde_etwas_entfernt) zurück."""
    changed = False
    for pattern, replacement in _REDACTIONS:
        text, n = pattern.subn(replacement, text)
        changed = changed or n > 0
    return text, changed


def _knowledge_text() -> str:
    """Komplette Wissensbasis als Text für den Systemprompt."""
    parts = []
    for a in load_articles():
        parts.append(f"# {a.title}")
        for s in a.sections:
            parts.append(f"## {s.heading} [Quelle: {s.id}]\n{s.text}")
    return "\n\n".join(parts)


def _system_prompt() -> str:
    """Anweisungen für den KI-Assistenten."""
    return (
        "Du bist der Hilfe-Assistent der Software WareVision, eines Warenwirtschafts- und Werkstattsystems "
        "für eine Quad- und Motorradwerkstatt in Deutschland. Beantworte Fragen zur Bedienung und zu den "
        "Funktionen von WareVision.\n"
        "Regeln:\n"
        "- Antworte auf Deutsch, kurz und Schritt für Schritt, mit den Button- und Menünamen aus der Anleitung.\n"
        "- Stütze dich ausschließlich auf die Anleitung unten. Steht etwas nicht darin, sage ehrlich, dass "
        "du es nicht sicher weißt, und erfinde keine Funktionen.\n"
        "- Du hast keinen Zugriff auf Kunden-, Rechnungs- oder Lagerdaten und kannst nichts in WareVision ändern.\n"
        "- Bei Rechts- und Steuerfragen nur allgemeine Hinweise aus der Anleitung geben und auf den "
        "Steuerberater verweisen.\n"
        "- Beende die Antwort mit einer Zeile 'Quellen:' und den verwendeten [Quelle: ...]-Kennungen.\n\n"
        "=== ANLEITUNG ===\n" + _knowledge_text()
    )


class AssistantError(Exception):
    """Fehler beim Aufruf der KI (Meldung ist für den Nutzer gedacht)."""


def _call_anthropic(api_key: str, model: str, messages: list[dict]) -> str:
    """Anthropic Messages API aufrufen und den Antworttext zurückgeben."""
    payload = json.dumps({
        "model": model,
        "max_tokens": MAX_ANSWER_TOKENS,
        "system": _system_prompt(),
        "messages": messages,
    }).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=payload,
        method="POST",
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        status = exc.code
        logger.warning("KI-Hilfe: HTTP %s von Anthropic", status)
        if status in (401, 403):
            raise AssistantError("Der API-Key für die KI-Hilfe ist ungültig. Bitte in den Einstellungen prüfen.") from exc
        if status == 429:
            raise AssistantError("Die KI-Hilfe ist gerade ausgelastet. Bitte gleich noch einmal versuchen.") from exc
        raise AssistantError(f"Die KI-Hilfe ist momentan nicht erreichbar (Fehler {status}).") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("KI-Hilfe nicht erreichbar: %s", exc)
        raise AssistantError("Die KI-Hilfe ist momentan nicht erreichbar.") from exc
    text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text").strip()
    if not text:
        raise AssistantError("Die KI-Hilfe hat keine Antwort geliefert.")
    return text


def _search_answer(question: str) -> tuple[str, list[HelpSection]]:
    """Antwort aus der Stichwortsuche zusammenstellen."""
    hits = search(question)
    if not hits:
        return (
            "Dazu habe ich in der Anleitung nichts gefunden. Formuliere die Frage bitte anders "
            "(z. B. mit dem Namen des Bereichs wie „Rechnungen“ oder „Inventur“) oder sieh im Inhaltsverzeichnis nach.",
            [],
        )
    parts = ["Das habe ich in der Anleitung gefunden:"]
    for s in hits:
        parts.append(f"**{s.article_title} – {s.heading}**\n{s.text}")
    return "\n\n".join(parts), hits


def _sources_from_answer(answer: str) -> list[HelpSection]:
    """[Quelle: id]-Kennungen aus der KI-Antwort auflösen."""
    by_id = {s.id: s for s in all_sections()}
    seen: list[HelpSection] = []
    for sid in re.findall(r"\[?Quelle:\s*([a-z0-9-]+)\]?", answer) + re.findall(r"([a-z0-9_]+--[a-z0-9-]+)", answer):
        sec = by_id.get(sid)
        if sec and sec not in seen:
            seen.append(sec)
    return seen


def _clean_answer(answer: str) -> str:
    """Technische Quellen-Kennungen aus dem Text entfernen (werden separat angezeigt)."""
    answer = re.sub(r"\s*\[Quelle:[^\]]*\]", "", answer)
    answer = re.sub(r"\n+Quellen?:.*$", "", answer, flags=re.S | re.I)
    return answer.strip()


def ask(question: str, history: list[dict] | None, api_key: str | None, model: str | None) -> dict:
    """Frage beantworten: mit KI (falls API-Key vorhanden), sonst per Stichwortsuche."""
    question = (question or "").strip()[:MAX_QUESTION_CHARS]
    safe_question, redacted = redact(question)
    notice = (
        "Hinweis: Personenbezogene Angaben (z. B. E-Mail, Telefon, IBAN, Kennzeichen) wurden aus deiner Frage "
        "entfernt, bevor sie verarbeitet wurde."
        if redacted else None
    )

    if api_key:
        messages: list[dict] = []
        for turn in (history or [])[-MAX_HISTORY_TURNS:]:
            role = turn.get("role")
            content = redact(str(turn.get("content", ""))[:MAX_QUESTION_CHARS * 2])[0]
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        # Anthropic verlangt, dass der Verlauf mit „user“ beginnt und sich abwechselt
        while messages and messages[0]["role"] != "user":
            messages.pop(0)
        cleaned: list[dict] = []
        for m in messages:
            if cleaned and cleaned[-1]["role"] == m["role"]:
                cleaned[-1] = m
            else:
                cleaned.append(m)
        if cleaned and cleaned[-1]["role"] == "user":
            cleaned.pop()
        cleaned.append({"role": "user", "content": safe_question})
        try:
            raw = _call_anthropic(api_key, model or DEFAULT_MODEL, cleaned)
            sources = _sources_from_answer(raw)
            return {
                "answer": _clean_answer(raw),
                "mode": "ai",
                "sources": [{"id": s.id, "article_id": s.article_id, "title": f"{s.article_title} – {s.heading}"} for s in sources],
                "notice": notice,
            }
        except AssistantError as exc:
            answer, hits = _search_answer(safe_question)
            return {
                "answer": answer,
                "mode": "search",
                "sources": [{"id": s.id, "article_id": s.article_id, "title": f"{s.article_title} – {s.heading}"} for s in hits],
                "notice": " ".join(filter(None, [str(exc) + " Ersatzweise Ergebnisse der Stichwortsuche:", notice])),
            }

    answer, hits = _search_answer(safe_question)
    return {
        "answer": answer,
        "mode": "search",
        "sources": [{"id": s.id, "article_id": s.article_id, "title": f"{s.article_title} – {s.heading}"} for s in hits],
        "notice": notice,
    }
