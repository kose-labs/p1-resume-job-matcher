"""Skill extraction (K9): find known skills in a job description or CV.

The vocabulary has two parts:

- **ESCO** (`artifacts/skills-esco.json.gz`, built by `scripts/build_skills_vocab.py`): the EU
  taxonomy's ICT, statistics, mathematics and digital skills, with their alternative labels.
- **Our tech dictionary** (`TECH_SKILLS` below): tools and frameworks job posts name that ESCO
  lacks or files under a broad concept (Docker is an alternative label of "manage ICT
  virtualisation environments"). It comes first, so a match is shown with the name people use.

Matching works on `preprocess.token_spans`, so labels and text are split the same way and
"Node.js", "C#" or "CI/CD" match whole. At each position the longest label wins: "machine
learning engineer" finds "machine learning", and "Spring Boot" isn't also counted as "Spring".

A few rules keep precision up, because a wrong "missing skill" misleads the user (plan:
precision ≥ 0.80). They are general, not tuned on our labels:

- **Case-sensitive words.** Names that are also English words ("Go", "Swift", "Spring", "R")
  only count when written as a name, so "go to market" and "spring release" don't match. One-word
  ESCO labels with a capital letter ("Scratch", "LESS", "Access") follow the same rule.
- **No short ESCO labels.** ESCO labels of 3 characters or fewer are mostly acronyms with other
  meanings ("AR", "POS", "ST"). Short tech names we want are in `TECH_SKILLS` instead.
- **No one-word lowercase ESCO synonyms.** ESCO lists "data" as another name for statistics and
  "computer" for computer equipment; as single words they match almost any job post. Preferred
  labels ("algorithms", "firmware") and multi-word synonyms are kept, except those starting
  with an article ("a computer").
"""

import gzip
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from app.ml.preprocess import clean_text, token_spans, tokenize

ESCO_ARTIFACT = Path(__file__).parent / "artifacts" / "skills-esco.json.gz"


@dataclass(frozen=True)
class Skill:
    """A skill as shown to the user, linked to ESCO when it has an ESCO concept."""

    name: str
    esco_uri: str | None = None


# name -> other spellings. Spellings are matched as tokens, so "node" also needs "node.js".
# Kept to what tech job posts actually ask for: languages, frameworks, data, cloud, DevOps, QA.
TECH_SKILLS: dict[str, list[str]] = {
    # Languages
    "Python": ["python3"],
    "Java": [],
    "JavaScript": ["js", "es6", "ecmascript"],
    "TypeScript": ["ts"],
    "C++": [],
    "C#": [],
    "C": [],
    "Go": ["golang"],
    "Rust": [],
    "Kotlin": [],
    "Swift": [],
    "Scala": [],
    "PHP": [],
    "Ruby": [],
    "R": [],
    "SQL": [],
    "Bash": ["shell scripting", "shell scripts"],
    "HTML": ["html5"],
    "CSS": ["css3"],
    "Dart": [],
    # Web and backend frameworks
    "Django": ["django rest framework", "drf"],
    "Flask": [],
    "FastAPI": [],
    "Spring": [],
    "Spring Boot": [],
    "Hibernate": [],
    "Node.js": [],
    "Express": ["express.js", "expressjs"],
    "NestJS": ["nest.js"],
    "React": ["react native"],
    "Angular": ["angularjs"],
    "Vue.js": ["vue"],
    "Next.js": ["nextjs"],
    "Redux": [],
    ".NET": ["asp.net", ".net core"],
    "Laravel": [],
    "Ruby on Rails": ["Rails"],
    "REST API": ["REST", "restful", "rest apis", "restful api", "restful apis"],
    "GraphQL": [],
    "gRPC": [],
    "Microservices": ["microservice", "microservice architecture"],
    # Data and ML
    "Machine learning": [],
    "Deep learning": [],
    "NLP": ["natural language processing"],
    "Computer vision": [],
    "LLM": ["llms", "large language models", "large language model"],
    "pandas": [],
    "NumPy": [],
    "scikit-learn": ["sklearn"],
    "PyTorch": [],
    "TensorFlow": [],
    "Keras": [],
    "Spark": ["pyspark", "apache spark"],
    "Airflow": ["apache airflow"],
    "Hadoop": [],
    "Tableau": [],
    "Power BI": ["powerbi"],
    "Statistics": [],
    "Data analysis": [],
    "ETL": [],
    "A/B testing": [],
    # Databases and messaging
    "PostgreSQL": [],
    "MySQL": [],
    "MongoDB": ["mongo"],
    "Redis": [],
    "Elasticsearch": ["elastic search"],
    "Oracle": [],
    "SQLite": [],
    "NoSQL": [],
    "Kafka": ["apache kafka"],
    "RabbitMQ": [],
    # Cloud and DevOps
    "AWS": ["amazon web services"],
    "Azure": ["microsoft azure"],
    "GCP": ["google cloud", "google cloud platform"],
    "Docker": [],
    "Kubernetes": [],
    "Terraform": [],
    "Ansible": [],
    "Helm": [],
    "Jenkins": [],
    "GitLab CI": ["gitlab ci/cd"],
    "GitHub Actions": [],
    "CI/CD": ["continuous integration", "continuous delivery", "continuous deployment"],
    "Linux": ["unix"],
    "Nginx": [],
    "Prometheus": [],
    "Grafana": [],
    "Git": ["github", "gitlab", "bitbucket"],
    # Testing and QA
    "Unit testing": ["unit tests", "unit test"],
    "Test automation": ["automated testing", "automation testing", "test automation"],
    "Manual testing": [],
    "Selenium": ["selenium webdriver"],
    "Cypress": [],
    "Playwright": [],
    "pytest": [],
    "JUnit": [],
    "Postman": [],
    "API testing": [],
    "TDD": ["test-driven development"],
    # Ways of working
    "Agile": ["agile development", "agile methodology", "agile methodologies"],
    "Scrum": [],
    "Kanban": [],
    "Jira": [],
    "OOP": ["object-oriented programming"],
    "Design patterns": [],
}

# Names that are also everyday words: they only match with this exact casing in the text.
CASE_SENSITIVE: frozenset[str] = frozenset(
    {
        "C",
        "Go",
        "R",
        "Rust",
        "Swift",
        "Spring",
        "Dart",
        "Ruby",
        "Express",
        "Flask",
        "Oracle",
        "Helm",
        "REST",
        "Rails",
        "Spark",
    }
)
# "R&D" would otherwise read as the R language.
_RND = re.compile(r"\bR\s*&\s*D\b")
# ESCO labels at least this long are trusted; shorter ones are mostly ambiguous acronyms.
MIN_ESCO_LABEL = 4
_QUALIFIER = re.compile(r"\s*\([^)]*\)\s*$")


def _plain(label: str) -> str:
    """Drop ESCO's trailing qualifier: "Python (computer programming)" -> "Python"."""
    return _QUALIFIER.sub("", label).strip()


class SkillExtractor:
    """Longest-match lookup of skill labels over the tokens of a text."""

    name = "esco-dictionary"
    version = "0.1.0"

    def __init__(
        self, labels: Iterable[tuple[str, Skill]], case_sensitive: Iterable[str] = CASE_SENSITIVE
    ) -> None:
        """Index labels (surface text -> skill); the first skill given for a label wins.

        Labels in `case_sensitive` only match text written with exactly that casing.
        """
        cased_labels = frozenset(case_sensitive)
        self._index: dict[tuple[str, ...], Skill] = {}
        self._cased: dict[tuple[str, ...], str] = {}
        for text, skill in labels:
            key = tuple(tokenize(text))
            if key and key not in self._index:
                self._index[key] = skill
                if text in cased_labels:
                    self._cased[key] = text
        self._longest = max((len(k) for k in self._index), default=0)

    @classmethod
    def load(cls, path: Path = ESCO_ARTIFACT) -> "SkillExtractor":
        """Build the extractor from our dictionary first, then the ESCO artefact."""
        with gzip.open(path, "rt", encoding="utf-8") as f:
            esco = json.load(f)["skills"]
        uri_of: dict[str, str] = {}
        for entry in esco:  # preferred labels first: "Python" links to Python, not a parent
            uri_of.setdefault(_plain(entry["label"]).lower(), entry["uri"])
        for entry in esco:
            for alt in entry["alt"]:
                uri_of.setdefault(_plain(alt).lower(), entry["uri"])

        labels: list[tuple[str, Skill]] = []
        for name, spellings in TECH_SKILLS.items():
            skill = Skill(name, uri_of.get(name.lower()))
            labels += [(name, skill)] + [(s, skill) for s in spellings]
        # Preferred labels before alternatives, so a label that is one skill's name and
        # another's synonym points to the skill it names.
        esco_labels = [(_plain(e["label"]), e, False) for e in esco]
        esco_labels += [(_plain(alt), e, True) for e in esco for alt in e["alt"]]
        cased = set(CASE_SENSITIVE)
        for text, entry, is_alt in esco_labels:
            one_word = len(tokenize(text)) == 1
            generic = is_alt and (
                (one_word and text.islower()) or text.lower().startswith(("a ", "an ", "the "))
            )
            if len(text) < MIN_ESCO_LABEL or generic:
                continue
            if one_word and not text.islower():
                cased.add(text)
            labels.append((text, Skill(_plain(entry["label"]), entry["uri"])))
        return cls(labels, cased)

    def extract(self, text: str) -> list[Skill]:
        """Skills mentioned in the text, each once, in order of first mention."""
        spans = token_spans(_RND.sub("research and development", clean_text(text)))
        tokens = [token for token, _ in spans]
        found: list[Skill] = []
        i = 0
        while i < len(tokens):
            for size in range(min(self._longest, len(tokens) - i), 0, -1):
                key = tuple(tokens[i : i + size])
                skill = self._index.get(key)
                if skill is None:
                    continue
                cased = self._cased.get(key)
                source = " ".join(s for _, s in spans[i : i + size])
                # Spelling variants ("golang" for Go) are unambiguous: only the name itself
                # has to be written with its casing.
                if cased is not None and source != cased and source.lower() == cased.lower():
                    continue
                if skill not in found:
                    found.append(skill)
                i += size
                break
            else:
                i += 1
        return found
