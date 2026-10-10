import pytest

from app.ml.preprocess import Section, clean_text, split_sections, split_sentences, tokenize


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("C++ and C#", ["c++", "and", "c#"]),
        ("Senior C++/Qt developer", ["senior", "c++", "qt", "developer"]),
        ("We use Go.", ["we", "use", "go"]),
        ("Golang microservices", ["go", "microservices"]),
        ("Node.js, NodeJS and Vue.js", ["node.js", "node.js", "and", "vue.js"]),
        (".NET 8 and ASP.NET Core", [".net", "8", "and", "asp.net", "core"]),
        ("F# or C", ["f#", "or", "c"]),
        ("CI/CD with K8s", ["ci/cd", "with", "kubernetes"]),
        ("scikit-learn, GPT-4", ["scikit-learn", "gpt-4"]),
        ("Python 3.12.", ["python", "3.12"]),
    ],
)
def test_tokenize_keeps_tech_names_whole(text: str, expected: list[str]) -> None:
    assert tokenize(text) == expected


def test_tokenize_splits_sentence_end_from_next_word() -> None:
    assert tokenize("I know Java. Next year") == ["i", "know", "java", "next", "year"]


def test_clean_text_joins_words_hyphenated_at_a_line_break() -> None:
    text = "software develop-\nment and test-\n  ing"
    assert clean_text(text) == "software development and testing"


def test_clean_text_keeps_real_hyphens_and_capitalized_continuations() -> None:
    assert clean_text("front-end work\nfull-\nStack") == "front-end work\nfull-\nStack"


def test_clean_text_normalizes_bullets_to_dashes() -> None:
    raw = "Skills\n• Python\n● Docker\n▪ SQL\n– Git\n* Linux\n1. Kafka\n2) Redis"
    assert clean_text(raw) == (
        "Skills\n- Python\n- Docker\n- SQL\n- Git\n- Linux\n- Kafka\n- Redis"
    )


def test_clean_text_fixes_ligatures_invisible_characters_and_whitespace() -> None:
    raw = "eﬃcient  work  ﬂow\r\nsoft­ware​\n\n\n\nend"
    assert clean_text(raw) == "efficient work flow\nsoftware\n\nend"


def test_clean_text_strips_markdown_emphasis_and_heading_marks() -> None:
    assert clean_text("## About us\n**Python** and `Django`") == "About us\nPython and Django"


def test_clean_text_does_not_touch_csharp_or_cpp() -> None:
    assert clean_text("C# and C++ developer") == "C# and C++ developer"


def test_split_sections_uses_canonical_names() -> None:
    text = clean_text(
        "Hi, we are a fintech startup.\n"
        "**Requirements:**\n- 3+ years of Python\n- PostgreSQL\n"
        "Nice to have\n- AWS\n"
        "What we offer:\n- Remote work"
    )
    assert split_sections(text) == [
        Section("body", "Hi, we are a fintech startup."),
        Section("requirements", "- 3+ years of Python\n- PostgreSQL"),
        Section("nice_to_have", "- AWS"),
        Section("benefits", "- Remote work"),
    ]


def test_split_sections_ignores_lines_that_only_start_with_a_heading_word() -> None:
    text = "Skills: Python, SQL\nExperience with Docker"
    assert split_sections(text) == [Section("body", text)]


def test_split_sections_drops_empty_sections() -> None:
    assert split_sections("Experience\nEducation\nKNUST, BSc") == [
        Section("education", "KNUST, BSc")
    ]


def test_split_sentences_treats_each_bullet_as_a_sentence() -> None:
    assert split_sentences("- Built REST APIs\n- Led a team of 3") == [
        "Built REST APIs",
        "Led a team of 3",
    ]


def test_split_sentences_splits_on_punctuation_but_not_inside_tech_names() -> None:
    text = "I use Node.js daily. I also know .NET and C#! Do you use ASP.NET? Yes."
    assert split_sentences(text) == [
        "I use Node.js daily.",
        "I also know .NET and C#!",
        "Do you use ASP.NET?",
        "Yes.",
    ]


def test_split_sentences_keeps_abbreviations_inside_a_sentence() -> None:
    assert split_sentences("Cloud tools, e.g. AWS and GCP. Then more.") == [
        "Cloud tools, e.g. AWS and GCP.",
        "Then more.",
    ]


def test_split_sentences_skips_lines_without_words() -> None:
    assert split_sentences("Python\n- \n---\n\nSQL") == ["Python", "SQL"]
