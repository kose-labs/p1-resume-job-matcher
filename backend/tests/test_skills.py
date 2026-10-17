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
        "Grab a pug-shaped mug, gulp your coffee and soap up; an elk walked by.",
    ],
)
def test_everyday_words_are_not_skills(extractor: SkillExtractor, text: str) -> None:
    assert extractor.extract(text) == []


@pytest.mark.parametrize(
    "text",
    [
        "Access to a company laptop and paid gym.",
        "Express delivery of features.",
        "Swift decisions, short meetings.",
        "We raised our Series C last year.",
        "Plan A, B and C.",
        "Experience with C",
    ],
)
def test_capitals_that_prove_nothing_are_not_skills(extractor: SkillExtractor, text: str) -> None:
    # A sentence's first word is capitalised anyway, and one letter alone is rarely a language.
    assert extractor.extract(text) == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("- Go\n- Rust\n- C", ["Go", "Rust", "C"]),
        ("Go, Rust or C (C11).", ["Go", "Rust", "C"]),
        ("Go and Rust experience", ["Go", "Rust"]),
        ("Strong C/C++ skills", ["C", "C++"]),
        ("Go developer wanted. Our stack: Python, Go.", ["Go", "Python"]),
    ],
)
def test_names_in_lists_or_next_to_other_skills_still_count(
    extractor: SkillExtractor, text: str, expected: list[str]
) -> None:
    assert names(extractor, text) == expected


def test_related_but_different_tools_stay_apart(extractor: SkillExtractor) -> None:
    assert names(extractor, "React Native, React, Unix and Linux") == [
        "React Native",
        "React",
        "Unix",
        "Linux",
    ]


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


def test_dictionary_names_match_in_any_casing(extractor: SkillExtractor) -> None:
    # ESCO also has "TypeScript" or "Java" as capitalised one-word labels; that mustn't make our
    # unambiguous names case-sensitive.
    assert names(extractor, "Typescript, Javascript and MySql. Java 11 experience a plus.") == [
        "TypeScript",
        "JavaScript",
        "MySQL",
        "Java",
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("DevOps experience;", ["DevOps"]),
        ("- Experience with R programming language", ["R"]),
        ("Spring Framework (DI, MVC)", ["Spring"]),
    ],
)
def test_clear_names_at_the_start_of_a_sentence(
    extractor: SkillExtractor, text: str, expected: list[str]
) -> None:
    assert names(extractor, text) == expected


def test_tools_added_from_the_dev_misses(extractor: SkillExtractor) -> None:
    text = (
        "AWS (EC2, ECS, EKS, RDS) managed with infrastructure-as-code; Webpack, Gulp and SCSS; "
        "TestRail for test documentation; ELK and Kibana; object-oriented design."
    )
    assert names(extractor, text) == [
        "AWS",
        "EC2",
        "ECS",
        "EKS",
        "RDS",
        "Infrastructure as Code",
        "Webpack",
        "Gulp",
        "SCSS",
        "TestRail",
        "Test documentation",
        "ELK stack",
        "Kibana",
        "OOP",
    ]
