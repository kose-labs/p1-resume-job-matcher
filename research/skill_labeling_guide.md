# Skill labelling guide (K9)

**Purpose:** a hand-labelled reference to measure skill extraction against: precision, recall
and F1 on 20 job descriptions (8 dev, 12 test), with targets of **F1 ≥ 0.70 and precision ≥ 0.80**
(project plan, Evaluation).

**Labeller:** Kobi. **Time:** about 3 minutes per JD, so 1 hour in total.

## How
1. Build the packet (once): from `backend/`, run `uv run python -m scripts.skill_eval packet`.
2. Open `data/skills/packet.html` in a browser and `research/skill_labels/kobi.csv` in an editor.
3. For each JD, write one row per skill: `jd_id,skill,level`. Replace the JD's empty starter row
   with your first skill and add rows below it.

```csv
jd_id,skill,level
jd-python-03,Python,required
jd-python-03,Django,required
jd-python-03,PostgreSQL,required
jd-python-03,Docker,nice
```

- `skill`: the name as the JD writes it, or its usual name. "Postgres" and "PostgreSQL" are
  both fine, because the evaluation maps spellings to one name.
- `level`: `required` for what the candidate must have, `nice` for "nice to have", "a plus" or
  "will be an advantage". When the JD doesn't say, use `required`.

**Label before you look at the extractor's output**, and don't change labels after seeing it.
Otherwise the labels drift towards whatever the extractor finds, and the score means nothing.

## What counts as a skill
Label every **technical skill, tool or method the JD asks the candidate to know or use**:

| Label | Examples |
|---|---|
| Programming languages | Python, Java, TypeScript, SQL, Bash |
| Frameworks and libraries | Django, Spring Boot, React, pandas, PyTorch |
| Databases, queues, search | PostgreSQL, MongoDB, Redis, Kafka, Elasticsearch |
| Cloud, DevOps, tools | AWS, Docker, Kubernetes, Terraform, Git, Jira, Linux |
| Testing | unit testing, test automation, Selenium, Postman, API testing |
| Methods and knowledge areas | REST API, microservices, CI/CD, Agile, Scrum, OOP, machine learning, statistics |

## What doesn't count
- **Soft skills and traits:** communication, teamwork, problem-solving, "self-motivated".
- **Spoken languages:** English, Ukrainian, even with a level ("B2", "upper-intermediate").
- **Experience, degrees, seniority:** "3+ years", "BSc in Computer Science", "senior".
- **The company's own product or domain:** "we build a SaaS platform for fintech" is not a
  skill asked of the candidate, unless the JD asks for that experience ("experience in fintech"
  still doesn't count: it's a domain, not a technical skill).
- **Benefits and process:** remote work, "code reviews in our team", "we use Slack". Count a tool
  only when the candidate is expected to know it ("experience with Jira").

## Edge cases
- **Lists with "or":** "AWS or GCP" → label both. The matcher shows each as covered or missing.
- **Versions:** "Python 3.10+" → `Python`. "Java 17" → `Java`.
- **Umbrella and specific:** "SQL databases (PostgreSQL, MySQL)" → `SQL`, `PostgreSQL`, `MySQL`.
- **Same skill twice in a JD:** one row. If it's required in one place and a plus in another,
  use `required`.
- **Vague phrases:** "modern frameworks", "cloud", "databases" with no name → skip, unless the
  phrase is itself a method or area someone could study ("cloud computing", "relational
  databases", "data structures and algorithms" are fine).
- **Unsure:** label it. A few borderline labels matter less than the
  consistency of the rest.

## Afterwards
- `uv run python -m scripts.skill_eval evaluate` reports precision, recall and F1 on **dev**, with
  every false positive and miss, to improve the dictionary and rules.
- `--split test` is run **once** per extractor version, for the model card. Nothing is changed
  because of a test result.
