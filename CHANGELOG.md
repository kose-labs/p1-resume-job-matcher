# Changelog

All notable changes to this project are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- MIT license, contributing guide and this changelog.

## [0.1.0] - 2026-10-08

### Added
- FastAPI backend with `/health` and `/api/v1/version`, managed with uv.
- React + TypeScript frontend (Vite) that proxies `/api` to the backend in local development.
- CI for lint, format, type checks, tests, frontend build and a Docker `/health` smoke test.
- Pre-commit hooks (Ruff, gitleaks secret scan, file hygiene) and Dependabot.
- Pull request, issue and documentation templates.
