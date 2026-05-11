# Kiku 聴く

**Extract classes of language behavior from AI conversation exports.**

Kiku is a hybrid regex + LLM extraction tool. Given an exported AI conversation (Claude.ai Markdown export OR Anthropic data export ZIP) and an extraction profile (YAML), it identifies blocks that match specific language patterns — first with regex, then with semantic classification via an LLM. Operates on a single conversation or a corpus of many.

Built to study how AI language shifts during extended collaboration. The caretaking profile included here was the first application — extracting unsolicited wellbeing advice from an eight-hour working session with Claude. That data became the evidence base for [Everybody is Making Out with AI in the Back of the Bus](https://sageframe.substack.com/p/everybody-is-making-out-with-ai-in).

## How it works

1. **Dispatch** — selects a parser based on the input file (Markdown or Anthropic ZIP).
2. **Parse** — produces one or more conversations as structured prompt/response blocks with timestamps. The Markdown parser also strips base64 images (which can be 60%+ of an export file).
3. **Extract (Tier 1: Regex)** — matches literal patterns from the profile against blocks of the configured target.
4. **Extract (Tier 2: Semantic)** — sends unmatched blocks of the target type to an LLM for classification, including the prior block as context where relevant.
5. **Format** — renders matches with context, per-match conversation header for corpus runs.

The two-tier approach gives you speed (regex catches the obvious hits) and nuance (semantic catches relational register shifts that no pattern could).

## Installation

```bash
cd kiku
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick start

```bash
# Single Markdown conversation, regex only — fast, no API key needed
kiku conversation.md --profile profiles/examples/caretaking.yaml --regex-only

# Full extraction with semantic pass
export ANTHROPIC_API_KEY=sk-ant-...
kiku conversation.md --profile profiles/examples/caretaking.yaml -o output.md

# Corpus run against an Anthropic data export ZIP
kiku ~/Downloads/data-*-batch-*.zip \
  --profile profiles/examples/overshoot-recognition.yaml \
  -o overshoot-candidates.md
```

## Extraction profiles

Profiles are YAML files that define what to extract:

```yaml
name: caretaking
description: >
  Extracts moments where the AI expresses personal concern for the user's
  wellbeing — eating, sleeping, taking breaks, spending time with family.

patterns:
  - "go (eat|get food)"
  - "go to (bed|sleep)"
  - "take a break"
  - "play with your (daughter|son)"

semantic_prompt: >
  Does this text contain the AI expressing personal concern for the user's
  physical wellbeing or family life?

model: claude-sonnet-4-6
context_window: 1
```

- **target**: which block type to match — `prompt` (human messages), `response` (assistant messages), or `both`. Default: `both`.
- **patterns**: regex patterns (case-insensitive). Tier 1 — fast, literal.
- **semantic_prompt**: sent to the LLM with each unmatched target block, along with the prior block as context. Tier 2 — nuanced.
- **model**: which model to use for semantic classification. Default: `claude-sonnet-4-6`.
- **context_window**: how many blocks before/after each match to include in output. Default: 1.

## Example profiles

- `caretaking.yaml` — extracts "Jewish mother" caretaking moments (assistant urging the user to eat, sleep, take breaks). The first application; `target: response`.
- `overshoot-recognition.yaml` — surfaces moments where the human reacted to AI overshooting their request. Hunts the human's reaction language; `target: prompt`. Built for corpus runs against Anthropic data exports.

## LLM backends

**Anthropic (default, recommended):**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or
export KIKU_API_KEY=sk-ant-...
```

**OpenAI-compatible (Ollama, LM Studio, etc.):**
```bash
export KIKU_BACKEND=openai
export KIKU_API_BASE=http://localhost:11434/v1
export KIKU_MODEL=llama3.1
```

Anthropic's Claude is strongly recommended for semantic classification. The task requires nuanced reading of relational register — distinguishing genuine care from task-related suggestions. Local models can work for simpler profiles but will produce more noise on subtle extractions.

## CLI reference

```
kiku <conversation> --profile <profile.yaml> [--output <file>] [--regex-only]
```

| Argument | Description |
|---|---|
| `conversation` | Path to conversation export (Claude.ai Markdown or Anthropic ZIP) |
| `--profile`, `-p` | Path to extraction profile (YAML) |
| `--output`, `-o` | Output file (default: stdout) |
| `--regex-only` | Skip semantic pass, regex only |

## Development

```bash
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Lint + format
flake8 src/ tests/
black src/ tests/
```

## Background

Kiku is one instrument in an ongoing research project on the language dynamics of human-AI collaboration. More at [Sageframe](https://sageframe.substack.com).

## License

MIT
