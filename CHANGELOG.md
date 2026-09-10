# Changelog

## 0.2.0 - 2026-09-10

- Added Graph and Swarm state persistence through the Strands repository API.
- Added PostgreSQL JSONB storage with a compatible Alembic migration from `v0.1.0`.
- Added the composite message-to-agent foreign key and complete session scoping for deletes.
- Updated CI for Python 3.10 through 3.14, package builds, artifact validation, and blocking mypy checks.
- Verified the package against Strands Agents 1.55.1.
