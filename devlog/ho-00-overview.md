# Ho 00: Kiku — Ho Overview

**Project:** Kiku (聴く) — Careful Listening
**Date:** 2026-04-19
**Status:** Active
**Arc target:** WIP-shippable tool with README, sample profile, sample output

---

## Project Summary

Kiku is a Python CLI that extracts specific classes of language behavior from exported AI conversations. It combines regex pattern matching with LLM semantic classification, driven by external YAML extraction profiles. The immediate goal is a working tool that can mine a real conversation for a published essay. The broader goal is an instrument for Voice DNA corpus analysis and Constructive Interference research.

---

## Ho Sequence

| Ho | Title | Phase | Stage | Dependencies | Status |
|---|---|---|---|---|---|
| 00 | Overview | Kamae | — | — | ✅ |
| 01 | Parser & Scaffold | Foundation | Shu | 00 | |
| 02 | Extraction Engine | Construction | Shu→Ha | 01 | |
| 03 | Output, Samples & Ship | Polish | Ha | 02 | |

---

## Phase Map

### Foundation (Ho 01): Parser & Scaffold

**Goal:** A working CLI that can ingest a conversation export, strip base64 blobs, and parse it into structured prompt/response blocks.

**Deliverables:**
- Project structure: `src/kiku/`, `tests/`, `profiles/examples/`, `pyproject.toml`
- `parser.py` — splits a markdown conversation export into blocks with metadata (type: prompt/response, timestamp, index)
- `preprocessor.py` — strips base64-encoded images, reports size reduction
- `cli.py` — entry point: `kiku <conversation.md> --profile <profile.yaml>`
- Profile schema defined: YAML loader, validation
- Tests for parser and preprocessor
- Verification: pytest, mypy strict, flake8, black

**Why this is one ho:** Parser + preprocessor + CLI scaffold are tightly coupled. You can't test the parser without the preprocessor (base64 blobs break block detection), and you can't test either without a CLI that invokes them. The profile loader is minimal at this stage — just enough to validate the schema.

---

### Construction (Ho 02): Extraction Engine

**Goal:** Both extraction tiers operational — regex matching and LLM semantic classification — producing matched blocks with context.

**Deliverables:**
- `extractor.py` — the core engine:
  - Regex pass: compile patterns from profile, match against blocks, collect hits with context window
  - Semantic pass: send unmatched Response blocks to LLM with profile's semantic prompt, collect hits
  - Deduplication: blocks caught by both passes are reported once, labeled as regex match
- LLM backend abstraction:
  - `backends/anthropic.py` — Claude via `anthropic` SDK
  - `backends/openai_compat.py` — OpenAI-compatible (Ollama, LM Studio, etc.)
  - Backend selection via env vars: `KIKU_BACKEND`, `KIKU_API_KEY`, `KIKU_API_BASE`, `KIKU_MODEL`
- Tests for regex matching (deterministic, thorough)
- Tests for semantic pass (mocked API responses for CI; live integration test optional)
- Verification: full lint-test cycle

**Why this is one ho:** The two extraction tiers share data structures (matched blocks, context windows) and the deduplication logic depends on both being operational. Building one without the other would mean refactoring the data model when the second tier arrives. The LLM backend abstraction is thin — two functions behind a common interface, not a framework.

---

### Polish (Ho 03): Output, Samples & Ship

**Goal:** Clean output formatter, example profile, example output, README. Shippable as a WIP.

**Deliverables:**
- `formatter.py` — renders matched blocks + context into clean Markdown:
  - Chronological order
  - Each match labeled: regex or semantic, with the matched pattern or LLM justification
  - Block type (prompt/response) and timestamp preserved
  - Context window (N blocks before/after) included, visually separated
  - Summary header: total matches, regex vs. semantic breakdown, conversation stats
- Example extraction profile: `profiles/examples/caretaking.yaml` — a depersonalized version of the "Jewish mother" profile, illustrative of how profiles work
- Example output: `profiles/examples/caretaking-output.md` — generated from a depersonalized conversation excerpt, showing what the tool produces
- README.md — what this is, how to install, how to run, how to write a profile, honest note on model capabilities for the semantic pass
- LICENSE (MIT)
- Verification: full lint-test cycle, manual end-to-end run against real conversation

**Why this is one ho:** Output formatting is quick. The real work in this ho is the sample files and README — which require running the tool against the real conversation first, then depersonalizing the output. That editorial work is inseparable from the formatting decisions.

---

## Dependencies

- Python 3.10+
- `anthropic` SDK (for Claude backend)
- `openai` SDK (for Ollama/OpenAI-compatible backend)
- `pyyaml` (profile loading)
- `pytest`, `mypy`, `flake8`, `black` (dev)

---

## Scope Boundaries

**In this arc:**
- Single conversation format: Claude.ai Markdown export (`## Prompt:` / `## Response:`)
- Single profile per run
- Two extraction tiers: regex + LLM semantic
- Two LLM backends: Anthropic native + OpenAI-compatible
- Clean MD output
- Example profile and output
- README

**Deferred:**
- Multiple conversation formats (Claude Code, ChatGPT JSON, etc.)
- Multi-profile runs / cross-category tagging
- Interactive mode (review and confirm matches)
- Integration with Shodō or Voice DNA
- Cost estimation before semantic pass
- Published profile library

---

## The Approach

This is a small, sharp tool. Three hos. The arc is compressed because:

1. The problem is well-understood — we've already analyzed the conversation, identified the patterns, and know what the output should look like.
2. The architecture is simple — parse, match, classify, format. No database, no web UI, no state.
3. The user is the builder. No learner/facilitator split. Ha-stage from the start for most of the work, shu only for the API integration patterns that are new territory.

The first real test is running the tool against the LinkedIn-Lying conversation to extract "Jewish mother" moments. If the output is good enough to use in the essay without manual cleanup, the tool works. If not, iterate in Ho 03 until it does.

---

_Seed: `kiku-seed.md`_
_Framework: Ho System (framework/structure/kamae-project-framing.md)_
