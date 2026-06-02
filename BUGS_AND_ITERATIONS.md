# Bugs and Iterations

## 2026-06-02 - Standalone Extraction

Problem: Primordial Chamber was buried inside a full Hermes fork, making the
actual project hard to understand and maintain.

Root cause: The first prototype used Hermes as the integration substrate, so
the chamber code was developed under `agent/primordial` and pushed as a renamed
fork.

Fix: Extracted the chamber into a standalone `primordial_chamber` package with
its own CLI, tests, docs, storage path, and repository scaffold.
