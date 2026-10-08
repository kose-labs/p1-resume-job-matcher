# Contributing

How we work on this repo. The full team rules live in the handbook's
[working agreement](https://github.com/kose-labs/handbook/blob/main/WORKING_AGREEMENT.md).

## Setup

Follow the [README quickstart](README.md#quickstart-no-docker-needed), then install the git hooks once per clone:

```bash
uvx pre-commit install
```

## Making a change

1. Pick or create an issue. One issue is at most about two hours of work and has acceptance criteria.
2. Branch off an up-to-date `main`, named after the issue:
   `feat/<issue#>-short-name`, `fix/…`, `docs/…`, `chore/…`, or `exp/…` for ML experiments.
3. Commit in small, single-purpose steps using [Conventional Commits](https://www.conventionalcommits.org):

   ```
   <type>(<scope>): <imperative summary under 72 characters>
   ```

   Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `exp`.
   Add a body when the reason isn't obvious. Mark breaking changes with `!` or `BREAKING CHANGE:`.
4. Run the checks locally (the same ones CI runs, listed in the [README](README.md#checks-the-same-ones-ci-runs)).
5. Open a pull request using the template: what and why, how it was tested, evidence, linked issue.

## Review and merge

- CI must be green and the other person must approve. Nobody merges their own unreviewed work.
- Review within 24 hours. Comments are suggestions unless marked **blocking**.
- Merge with **Squash and merge**, so `main` gets one commit per pull request.
- Add a line under `Unreleased` in [CHANGELOG.md](CHANGELOG.md) for anything a user of the project would notice.

## Experiments

ML experiments go on `exp/` branches with an
[experiment issue](.github/ISSUE_TEMPLATE/experiment.md). When an experiment wins and changes the
app's model or pipeline, it lands as a `feat:` or `perf:` pull request with before-and-after metrics.

## Never commit

- Secrets: use `.env` (git-ignored) and document new variables in `.env.example`.
- Personal data: real CVs and raw datasets stay off git. Only synthetic files go in `backend/tests/fixtures/`.
