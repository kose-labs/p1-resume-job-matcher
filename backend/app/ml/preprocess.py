"""Text preprocessing shared by every matcher, so model comparisons differ only in the model.

Three steps, used in this order:

1. `clean_text` repairs what PDF extraction and job boards leave behind: ligatures, unmapped
   glyphs, soft and end-of-line hyphens, bullet symbols, Markdown emphasis, stray whitespace.
2. `split_sections` and `split_sentences` cut the text into the units the embedding matcher
   compares (JD requirements against CV sentences).
3. `tokenize` lowercases and splits into words while keeping tech names whole. Generic
   tokenizers break exactly the words a CV matcher cares most about: "C++" and "C#" both become
   "c", ".NET" loses its dot and "Go" is dropped as a stop word.
"""

import re
import unicodedata
from dataclasses import dataclass

# Characters that render as nothing but split words for a tokenizer.
_INVISIBLE = dict.fromkeys(map(ord, "­​‌‍⁠﻿"))
# Bullet symbols seen in CVs and job posts; each becomes "- " at the start of the line.
_BULLET = re.compile(r"^[ \t]*(?:[•●▪◦‣∙·○■□➢➤►▸✓✔✗\-–—*]|\d{1,2}[.)])[ \t]+", re.MULTILINE)
# A word broken across a line: "develop-\nment". Only joins when both sides are lowercase
# letters, so "front-\nEnd" and list items starting with "-" stay as they are.
_LINE_HYPHEN = re.compile(r"([a-z])-[ \t]*\n[ \t]*([a-z])")
_MARKDOWN = re.compile(r"\*\*|__|`|^#{1,6}[ \t]+", re.MULTILINE)
# pdfplumber writes glyphs it can't map to text (often bullet symbols) as "(cid:127)" (ADR-0003).
_CID = re.compile(r"\(cid:\d+\)")
_SPACES = re.compile(r"[ \t\f\v  -   　]+")


def clean_text(text: str) -> str:
    """Normalize raw CV or job description text without changing its words."""
    # NFKC turns ligatures ("ﬁ" -> "fi") and full-width characters into plain ones.
    text = unicodedata.normalize("NFKC", text).translate(_INVISIBLE)
    text = _CID.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _SPACES.sub(" ", text)
    text = _LINE_HYPHEN.sub(r"\1\2", text)
    text = _MARKDOWN.sub("", text)
    text = _BULLET.sub("- ", text)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# Heading text (lowercase, without a trailing colon) -> canonical section name.
SECTION_ALIASES: dict[str, str] = {
    **dict.fromkeys(
        ["summary", "profile", "about me", "about", "who am i", "objective"], "summary"
    ),
    **dict.fromkeys(
        ["experience", "work experience", "professional experience", "employment history"],
        "experience",
    ),
    **dict.fromkeys(["education", "academic background"], "education"),
    **dict.fromkeys(
        ["skills", "technical skills", "tech stack", "technologies", "core skills"], "skills"
    ),
    **dict.fromkeys(["projects", "personal projects"], "projects"),
    **dict.fromkeys(["certifications", "certificates", "courses"], "certifications"),
    **dict.fromkeys(
        [
            "requirements",
            "required skills",
            "qualifications",
            "must have",
            "what we expect",
            "what you need",
            "we expect",
            "you have",
        ],
        "requirements",
    ),
    **dict.fromkeys(
        ["nice to have", "would be a plus", "will be a plus", "preferred qualifications", "bonus"],
        "nice_to_have",
    ),
    **dict.fromkeys(
        ["responsibilities", "duties", "what you will do", "what you'll do", "your tasks"],
        "responsibilities",
    ),
    **dict.fromkeys(["we offer", "benefits", "what we offer", "perks"], "benefits"),
    **dict.fromkeys(["about us", "about the company", "company", "about the project"], "company"),
}


@dataclass(frozen=True)
class Section:
    """A titled part of a document. Text before the first heading has the name "body"."""

    name: str
    text: str


def _heading(line: str) -> str | None:
    """Return the canonical section name if the whole line is a known heading."""
    key = line.strip().rstrip(":").strip().lower()
    return SECTION_ALIASES.get(key)


def split_sections(text: str) -> list[Section]:
    """Split cleaned text into sections at known headings; empty sections are dropped."""
    sections: list[Section] = []
    name = "body"
    lines: list[str] = []
    for line in text.split("\n"):
        heading = _heading(line)
        if heading is None:
            lines.append(line)
            continue
        if body := "\n".join(lines).strip():
            sections.append(Section(name, body))
        name, lines = heading, []
    if body := "\n".join(lines).strip():
        sections.append(Section(name, body))
    return sections


# A sentence ends at ".", "!" or "?" followed by a space and an uppercase letter or digit, unless
# the word before the dot is a known abbreviation.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
_ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.", "approx.", "incl.", "esp.", "mr.", "ms.", "dr.")


def split_sentences(text: str) -> list[str]:
    """Split cleaned text into sentences. Every line (bullet or not) is its own sentence."""
    sentences: list[str] = []
    for line in text.split("\n"):
        line = line.removeprefix("- ").strip()
        if not line:
            continue
        parts = _SENTENCE_END.split(line)
        current = parts[0]
        for part in parts[1:]:
            if current.lower().endswith(_ABBREVIATIONS):
                current = f"{current} {part}"
            else:
                sentences.append(current)
                current = part
        sentences.append(current)
    return [s.strip() for s in sentences if any(ch.isalnum() for ch in s)]


# Tech names that the general pattern below would split or drop, matched first.
_TECH = r"c\+\+|c#|f#|\.net|asp\.net|ci/cd|tcp/ip|pl/sql|a/b"
# Words with inner dots, pluses or hyphens stay whole: node.js, vue.js, scikit-learn, gpt-4.
_WORD = r"[a-z0-9]+(?:[.+\-][a-z0-9]+)*\+*"
_TOKEN = re.compile(rf"(?<![a-z0-9])(?:{_TECH})(?![a-z0-9])|{_WORD}")

# Spellings of the same technology, mapped to one token so they match each other.
TECH_ALIASES: dict[str, str] = {
    "nodejs": "node.js",
    "golang": "go",
    "reactjs": "react",
    "react.js": "react",
    "vuejs": "vue.js",
    "dotnet": ".net",
    "cpp": "c++",
    "csharp": "c#",
    "k8s": "kubernetes",
    "postgres": "postgresql",
    "ml": "machine learning",
}


def tokenize(text: str) -> list[str]:
    """Lowercase words and tech names, with spelling variants mapped to one form.

    Keeps one-letter and stop-word-like tech names ("c", "r", "go"): removing stop words is the
    vectorizer's job, with a list that leaves them in.
    """
    tokens: list[str] = []
    for token in _TOKEN.findall(text.lower()):
        tokens.extend(TECH_ALIASES.get(token, token).split())
    return tokens
