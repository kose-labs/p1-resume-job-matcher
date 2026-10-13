import gzip
import json

import pytest

from app.ml.preprocess import token_spans, tokenize
from app.ml.skills import ESCO_ARTIFACT, TECH_SKILLS, Skill, SkillExtractor

PYTHON_URI = "http://data.europa.eu/esco/skill/ccd0a1d9-afda-43d9-b901-96344886e14d"


@pytest.fixture(scope="module")
def extractor() -> SkillExtractor:
    return SkillExtractor.load()


def names(extractor: SkillExtractor, text: str) -> list[str]:
    return [skill.name for skill in extractor.extract(text)]


def test_finds_tech_names_whole_in_order_of_first_mention(extractor: SkillExtractor) -> None:
    text = "We use Node.js, C# and C++. Python too; also CI/CD with GitLab CI. Python again."
    assert names(extractor, text) == ["Node.js", "C#", "C++", "Python", "CI/CD", "GitLab CI"]


def test_spelling_variants_map_to_one_skill(extractor: SkillExtractor) -> None:
    assert names(extractor, "golang, k8s, Postgres, NodeJS, sklearn") == [
        "Go",
        "Kubernetes",
        "PostgreSQL",
        "Node.js",
        "scikit-learn",
    ]


def test_longest_label_wins(extractor: SkillExtractor) -> None:
    assert names(extractor, "Spring Boot and Ruby on Rails") == ["Spring Boot", "Ruby on Rails"]


@pytest.mark.parametrize(
    "text",
    [
        "We go to market fast and swift decisions matter.",
        "The rest of the team works in R&D.",
        "Start from scratch, with less overhead and access to data on a computer.",
        "A spring release; our rust-free process.",
    ],
)
def test_everyday_words_are_not_skills(extractor: SkillExtractor, text: str) -> None:
    assert extractor.extract(text) == []


def test_case_sensitive_names_match_when_written_as_names(extractor: SkillExtractor) -> None:
    text = "Go, Rust, Swift, Spring, R and REST services; built with Scratch and LESS."
    assert names(extractor, text) == [
        "Go",
        "Rust",
        "Swift",
        "Spring",
        "R",
        "REST API",
        "Scratch",
        "LESS",
    ]


def test_dictionary_skills_link_to_esco_when_esco_has_them(extractor: SkillExtractor) -> None:
    python, docker = extractor.extract("Python and Docker")
    assert python == Skill("Python", PYTHON_URI)
    assert docker.name == "Docker"


def test_esco_labels_lose_their_qualifier(extractor: SkillExtractor) -> None:
    # ESCO's preferred label is "Groovy (computer programming)" or similar; we show "Groovy".
    assert "Groovy" in names(extractor, "Scripts in Groovy")


def test_esco_multiword_synonyms_still_match(extractor: SkillExtractor) -> None:
    assert "cloud technologies" in names(extractor, "Experience with cloud computing")


def test_every_dictionary_spelling_reaches_its_skill(extractor: SkillExtractor) -> None:
    for name, spellings in TECH_SKILLS.items():
        for text in [name, *spellings]:
            assert names(extractor, text) == [name], text


def test_token_spans_keep_the_original_text() -> None:
    assert token_spans("Go to ML") == [
        ("go", "Go"),
        ("to", "to"),
        ("machine", "ML"),
        ("learning", "ML"),
    ]
    assert [t for t, _ in token_spans("Go to ML")] == tokenize("Go to ML")


def test_esco_artefact_has_provenance_and_only_labels() -> None:
    with gzip.open(ESCO_ARTIFACT, "rt", encoding="utf-8") as f:
        data = json.load(f)
    assert data["source"].startswith("ESCO v1.2.0")
    assert "2011/833/EU" in data["licence"]
    assert len(data["skills"]) > 900
    assert all(set(entry) == {"uri", "label", "alt"} for entry in data["skills"])
