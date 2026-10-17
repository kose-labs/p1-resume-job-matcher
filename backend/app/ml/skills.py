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
- **Capitals that prove nothing.** A sentence's first word is capitalised anyway, so "Access to a
  company laptop" or "Express delivery" isn't evidence of a name. There, a case-sensitive name
  counts only if it stands alone as a list item ("- Go", "Go, Rust"), the sentence names another
  skill ("Go and Rust") or calls it a language ("R programming"). The same goes for one-letter
  names anywhere ("Series C", "Plan A, B and C"). Either way, the skill still counts when the text
  names it clearly somewhere else. Our dictionary decides which of its names are ambiguous, so
  "Java" or "Python" at the start of a sentence always count.
- **No short ESCO labels.** ESCO labels of 3 characters or fewer are mostly acronyms with other
  meanings ("AR", "POS", "ST"). Short tech names we want are in `TECH_SKILLS` instead.
- **No one-word lowercase ESCO synonyms.** ESCO lists "data" as another name for statistics and
  "computer" for computer equipment; as single words they match almost any job post. Preferred
  labels ("algorithms", "firmware") and multi-word synonyms are kept, except those starting
  with an article ("a computer").
- **Fields of study aren't skills.** "Computer science", "mathematics" and "statistics" are skipped
  next to a degree word ("BSc in Computer Science", "Computer Science degree"):
  there they name a degree, which the labelling guide doesn't count. Elsewhere ("statistics and
  probability", "computer science fundamentals") they still count.
"""

import gzip
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from app.ml.preprocess import clean_text, split_sentences, token_spans, tokenize

ESCO_ARTIFACT = Path(__file__).parent / "artifacts" / "skills-esco.json.gz"


@dataclass(frozen=True)
class Skill:
    """A skill as shown to the user, linked to ESCO when it has an ESCO concept."""

    name: str
    esco_uri: str | None = None


# name -> other spellings. Spellings are matched as tokens, so "node" also needs "node.js".
# Kept to what tech job posts actually ask for: languages, frameworks, data, cloud, DevOps, QA.
# 0.3.0 adds the named tools and methods the extractor missed on the 8 dev JDs of the K9 labels
# (none from the 12 test JDs), checked on 1,500 other Djinni JDs for wrong matches.
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
    "SCSS": ["sass"],
    "Dart": [],
    # Web and backend frameworks
    "Django": ["django rest framework", "drf"],
    "Flask": [],
    "FastAPI": [],
    "Spring": ["spring framework"],
    "Spring Boot": [],
    "Hibernate": [],
    "Node.js": [],
    "Express": ["express.js", "expressjs"],
    "NestJS": ["nest.js"],
    "React": [],
    "React Native": [],
    "Angular": ["angularjs"],
    "Vue.js": ["vue"],
    "Next.js": ["nextjs"],
    "Redux": [],
    "Webpack": [],
    "Gulp": [],
    "Pug": [],
    ".NET": ["asp.net", ".net core"],
    "Laravel": [],
    "Ruby on Rails": ["Rails"],
    "REST API": ["REST", "restful", "rest apis", "restful api", "restful apis"],
    "GraphQL": [],
    "SOAP": [],
    "API design": [],
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
    "Theano": [],
    "Caffe": [],
    "Matplotlib": [],
    "Spark": ["pyspark", "apache spark"],
    "Airflow": ["apache airflow"],
    "Hadoop": [],
    "Tableau": [],
    "Power BI": ["powerbi"],
    "Statistics": [],
    "Calculus": [],
    "Linear algebra": [],
    "Big data": ["bigdata"],
    "Data mining": [],
    "Data modelling": ["data modeling"],
    "Data architecture": [],
    "Data visualisation": ["data visualization", "visualize data", "visualise data"],
    "Predictive modelling": ["predictive modeling", "predictive models", "predictive model"],
    "Data structures": [],
    "Text processing": [],
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
    "Time-series databases": [
        "time-series database",
        "time series database",
        "time series databases",
    ],
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
    "Infrastructure as Code": ["iac", "infrastructure-as-code"],
    "Configuration management": [],
    "GitOps": [],
    "EC2": [],
    "ECS": [],
    "EKS": [],
    "RDS": [],
    "Istio": [],
    "Anthos Service Mesh": [],
    "Google Config Connector": [],
    "Helm": [],
    "Jenkins": [],
    "GitLab CI": ["gitlab ci/cd"],
    "GitHub Actions": [],
    "CI/CD": ["continuous integration", "continuous delivery", "continuous deployment"],
    "Linux": [],
    "Unix": [],
    "Nginx": [],
    "Prometheus": [],
    "Grafana": [],
    "Stackdriver": ["stack driver"],
    "ELK stack": ["ELK"],
    "Kibana": [],
    "TCP/IP": [],
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
    "TDD": ["test-driven development", "test driven development"],
    "TestRail": ["test rail"],
    "Test documentation": ["tests documentation"],
    "Acceptance criteria": [],
    # Ways of working
    "Agile": ["agile development", "agile methodology", "agile methodologies"],
    "Scrum": [],
    "Kanban": [],
    "Jira": [],
    "OOP": ["object-oriented programming", "object-oriented", "object oriented"],
    "Design patterns": [],
    "Functional programming": [],
    "SDLC": ["software development lifecycle", "software development life cycle"],
    "Markdown": [],
    "AsciiDoc": ["ascii doc"],
    # Security
    "OAuth": ["oauth2"],
    "OpenID Connect": [],
    "SAML": [],
    "Burp Suite": [],
    "Qualys": [],
    "Rapid7": [],
    "F-Secure": [],
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
        "Gulp",
        "Pug",
        "SOAP",
        "ELK",
    }
)
# "R&D" would otherwise read as the R language.
_RND = re.compile(r"\bR\s*&\s*D\b")
# Skills that are also fields of study, and the words that mark a degree ("BSc", "student").
ACADEMIC_FIELDS = frozenset({"computer science", "mathematics", "statistics"})
DEGREE_WORDS = frozenset(
    {
        "degree",
        "degrees",
        "bachelor",
        "bachelors",
        "masters",
        "bsc",
        "msc",
        "b.sc",
        "m.sc",
        "phd",
        "ph.d",
        "diploma",
        "graduate",
        "undergraduate",
        "student",
        "students",
        "studying",
        "majoring",
    }
)
# Degree words that are also everyday words or other names ("MS Excel", "a major part", "master
# SQL"): they only count when a degree follows ("MS in", "Master's", "BS/MS", "major in").
AMBIGUOUS_DEGREE_WORDS = frozenset({"ba", "bs", "ma", "ms", "master", "major"})
_DEGREE_FOLLOWERS = frozenset({"s", "in", "of", "degree", "degrees"})
# A field of study names a degree up to 8 tokens after a degree word ("BSc in Computer Science,
# Mathematics") or 2 before one ("Computer Science degree", "Computer Science B.Sc.").
DEGREE_REACH_AFTER, DEGREE_REACH_BEFORE = 8, 2
# ESCO labels at least this long are trusted; shorter ones are mostly ambiguous acronyms.
MIN_ESCO_LABEL = 4
_QUALIFIER = re.compile(r"\s*\([^)]*\)\s*$")


def _plain(label: str) -> str:
    """Drop ESCO's trailing qualifier: "Python (computer programming)" -> "Python"."""
    return _QUALIFIER.sub("", label).strip()


class SkillExtractor:
    """Longest-match lookup of skill labels over the tokens of a text."""

    name = "esco-dictionary"
    version = "0.3.2"

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
        # Our dictionary decides which of its names are ambiguous: ESCO's "Java" or "Python" are
        # capitalised one-word labels too, but nobody writes "python" meaning a snake in a JD.
        ours = {text.lower() for text, _ in labels}
        for text, entry, is_alt in esco_labels:
            one_word = len(tokenize(text)) == 1
            generic = is_alt and (
                (one_word and text.islower()) or text.lower().startswith(("a ", "an ", "the "))
            )
            if len(text) < MIN_ESCO_LABEL or generic:
                continue
            if one_word and not text.islower() and text.lower() not in ours:
                cased.add(text)
            labels.append((text, Skill(_plain(entry["label"]), entry["uri"])))
        return cls(labels, cased)

    def extract(self, text: str) -> list[Skill]:
        """Skills mentioned in the text, each once, in order of first mention."""
        cleaned = _RND.sub("research and development", clean_text(text))
        mentions: list[tuple[Skill, bool]] = []  # (skill, clear evidence), in text order
        for sentence in split_sentences(cleaned):
            found = self._matches(sentence)
            skills = {skill for skill, _, _ in found}
            tokens = [token for token, _ in token_spans(sentence)]
            for skill, start, cased in found:
                if _names_a_degree(skill, tokens, start):
                    continue
                alone = start == 0 and _stands_alone(sentence, cased or "")
                named = cased is not None and _named_as_language(sentence, cased)
                ambiguous = (
                    cased is not None
                    and _like_a_word(cased)
                    and not (alone or named)
                    and (start == 0 or len(cased) == 1)
                )
                mentions.append((skill, not ambiguous or len(skills) > 1))
        clear = {skill for skill, ok in mentions if ok}
        return list(dict.fromkeys(skill for skill, _ in mentions if skill in clear))

    def _matches(self, sentence: str) -> list[tuple[Skill, int, str | None]]:
        """Longest matches in one sentence: (skill, token index, the name if case-sensitive)."""
        spans = token_spans(sentence)
        tokens = [token for token, _ in spans]
        found: list[tuple[Skill, int, str | None]] = []
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
                if cased is not None and source.lower() == cased.lower():
                    if source != cased:
                        continue
                    found.append((skill, i, cased))
                else:
                    found.append((skill, i, None))
                i += size
                break
            else:
                i += 1
        return found


def _names_a_degree(skill: Skill, tokens: list[str], start: int) -> bool:
    """True for a field of study written next to a degree word: "BSc in Computer Science",
    "Computer Science degree"."""
    if skill.name.lower() not in ACADEMIC_FIELDS:
        return False
    end = start + len(skill.name.split())
    near = [
        *range(max(0, start - DEGREE_REACH_AFTER), start),
        *range(end, end + DEGREE_REACH_BEFORE),
    ]
    return any(_marks_a_degree(tokens, i) for i in near if i < len(tokens))


def _marks_a_degree(tokens: list[str], i: int) -> bool:
    """True if token i is a degree word; an ambiguous one also needs a degree after it."""
    if tokens[i] in DEGREE_WORDS:
        return True
    after = tokens[i + 1] if i + 1 < len(tokens) else ""
    return tokens[i] in AMBIGUOUS_DEGREE_WORDS and (
        after in _DEGREE_FOLLOWERS or after in DEGREE_WORDS or after in AMBIGUOUS_DEGREE_WORDS
    )


def _stands_alone(sentence: str, name: str) -> bool:
    """True if the sentence starts with the name as a list item: "Go", "Go, Rust", "Spring
    Framework". A lowercase word or a number after it reads as prose: "Access to", "Spring 2025"."""
    rest = sentence[sentence.find(name) + len(name) :]
    return not rest or rest[0] != " " or not (rest[1:2].islower() or rest[1:2].isdigit())


def _like_a_word(name: str) -> bool:
    """True for names spelled like an English word ("Go", "Access", "C"), so a capital at the start
    of a sentence proves nothing. "DevOps" or "LESS" can't be a normal word written there."""
    return name[1:].islower() or len(name) == 1


def _named_as_language(sentence: str, name: str) -> bool:
    """True if the text calls the name a language: "R programming", "C language"."""
    return (
        re.search(rf"(?<![\w+#]){re.escape(name)} (?:programming|language)\b", sentence) is not None
    )
