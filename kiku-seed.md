# Kiku (聴く) — Project Seed

**Type:** Seed (Stub)
**Status:** Draft
**Project:** Kiku
**Created:** 2026-04-19
**Parent Framework:** Constructive Interference

---

## The Soul

Careful listening — a tool for extracting specific classes of language behavior from exported AI conversations, using configurable extraction profiles that combine regex pattern matching with LLM-powered semantic classification.

## The Body

A Python CLI that takes an exported AI conversation and an extraction profile, and returns every instance of the described language behavior with surrounding context — formatted as a clean, reviewable document.

---

## The Problem

AI conversations are long. The interesting material — the moments where something specific and nameable happened — is buried in thousands of lines of working text. Finding those moments after the fact requires either reading the entire conversation or writing bespoke scripts that are never reusable.

The deeper problem: the behavioral classes worth extracting are rarely reducible to keywords. "Claude expressing unsolicited concern about my physical needs" is a real category with dozens of instances across a single conversation. Some are literal ("Go eat"), some are structural ("You've been doing this since 8 AM"), some are tonal shifts that share no keywords at all. A useful extraction tool needs to handle the full spectrum — from literal pattern matching through semantic classification.

This is not academic. The immediate use case is mining a 10,000-line conversation export to find every instance of a specific relational behavior for a published essay. The broader use case is corpus analysis for Voice DNA voice profiling, diagnostic taxonomy validation for Destructive Interference, and eventually feeding Shodo's synthesis layer.

---

## The Landscape

Nothing exists for this specific task. Grep finds keywords. LLM chat finds what's in its context window. Shodō (when built) will do full-corpus semantic search across conversations — but Shodō is a vector-database-backed system for the entire conversation history. Kiku is a scalpel: one conversation, one profile, one extraction.

The closest analogue is qualitative coding in social science — reading a transcript and marking passages that belong to a defined category. That process is manual, slow, and doesn't scale. Kiku automates the coding pass.

---

## The Vision

Write an extraction profile that describes a class of language behavior. Point it at any exported AI conversation. Get back every instance, with context, in a clean document you can work from.

The profile is the reusable artifact. The tool is the instrument. The output is the material.

---

## How It Fits

**Constructive Interference** is the parent framework — the methodology for understanding how human voice and AI collaboration interact. Kiku is an instrument built from that framework.

**Voice DNA** needs corpus analysis to build and validate voice profiles. Kiku's extraction profiles are the mechanism — define a voice behavior as a class, extract every instance from a conversation, study the pattern. The "Destructive Interference" taxonomy of seven failure classes in AI-influenced writing could each become an extraction profile.

**Shodō** will eventually do full-corpus search and synthesis across all conversations. Kiku is the single-conversation version — faster, simpler, no infrastructure. When Shodō's synthesis layer is built, Kiku's profile schema and classification logic could become a component of it.

**The immediate use:** Extract every instance of Claude expressing parental/caretaking concern from a specific conversation, for use in a published essay about the relational quality of AI collaboration.

---

## Architecture Direction

**Input:** Exported conversation in Markdown (Claude.ai export format initially; extensible to other formats).

**Preprocessing:** Strip base64-encoded images (which can be 60-70% of file size) before any analysis.

**Parsing:** Split the conversation into prompt/response blocks using the `## Prompt:` / `## Response:` header structure.

**Extraction — two tiers:**

1. **Regex pass:** Pattern matching against a list of literal/regex terms defined in the profile. Fast, deterministic, catches the obvious hits. Handles 60-70% of instances.

2. **Semantic pass:** Send each Response block (that wasn't already caught by regex) to an LLM with the profile's semantic prompt. The LLM classifies: does this block contain an instance of the described behavior? Yes/no with brief justification. Catches the subtle, keyword-free instances that make the extraction valuable.

**LLM backend:** Default to Claude (Sonnet) via the Anthropic Python SDK. Support OpenAI-compatible endpoints (Ollama, LM Studio, etc.) as an alternative backend. The profile can specify a model. The README is honest about capability differences between frontier and local models for nuanced classification.

**Output:** Clean Markdown file. Each match includes: the matched block, the block before it, and the block after it. Matches are labeled with which tier caught them (regex vs. semantic). Organized chronologically.

**Extraction profiles:** YAML files. External to the tool — users maintain their own. The repo ships with example profiles that are illustrative, not personal.

**Profile schema (draft):**

```yaml
name: 'jewish_mother'
description: "Claude expressing unsolicited parental concern about the user's basic physical needs or work-life boundaries"
model: 'claude-sonnet-4-20250514' # optional, default sonnet
context_window: 1 # blocks before/after each match

patterns:
  - 'go eat'
  - 'go to bed'
  - 'go to sleep'
  - 'play with your daughter'
  - 'stop working'
  - 'get some (rest|sleep)'
  - "you've been (at this|doing this|working)"
  - "that's not a suggestion"

semantic_prompt: |
  You are analyzing a block of text from an AI conversation.
  Does this block contain an instance of the AI expressing
  unsolicited concern about the user's basic physical needs
  (eating, sleeping, resting) or work-life boundaries
  (spending time with family, stopping work)?

  This includes direct instructions ("go eat"), indirect
  pressure ("you've been at this since 8 AM"), emotional
  register shifts (the AI adopting a parental or caretaking
  tone), and any language that prioritizes the user's
  wellbeing over the task at hand.

  Respond with YES or NO, followed by a one-sentence
  justification.
```

---

## Constraints

- Python. Consistent with the existing stack.
- CLI-first. No web UI. No database. No server.
- Single dependency for the semantic pass: `anthropic` SDK (and optionally `openai` for Ollama-compatible backends).
- Runs on a single conversation export at a time. Not a corpus tool.
- Profiles live outside the repo. The repo ships examples only.

---

## Scope Boundaries

**This IS:**

- A CLI tool for extracting classified language behaviors from a single AI conversation
- Configurable via external YAML extraction profiles
- A hybrid regex + LLM classification engine
- A component that could be consumed by Voice DNA and Shodō downstream

**This is NOT:**

- A corpus search tool (that's Shodō)
- A voice profiler (that's Voice DNA)
- An AI detector (that's the wrong question)
- A multi-conversation tool (v1 operates on one file at a time)

---

## Success Criteria

1. Running `kiku --profile jewish_mother conversation.md` produces a clean MD file containing every instance of the target behavior, with context, in under 60 seconds.
2. The regex pass catches all literal/obvious instances with zero false positives.
3. The semantic pass catches at least 80% of the subtle, keyword-free instances that regex misses.
4. A new extraction profile can be written in under 10 minutes by someone who understands the behavior they're looking for.
5. The output is immediately usable as source material for writing — no further cleaning needed.

---

## Open Questions

1. **Conversation format variance.** Claude.ai exports have `## Prompt:` / `## Response:` structure. Claude Code exports are different. ChatGPT exports are JSON. V1 targets one format; the parser should be swappable.
2. **Semantic pass cost at scale.** For a 200-block conversation with Sonnet, cost is trivial (~$0.10-0.20). For larger conversations or Opus, it climbs. Should the tool report estimated cost before running?
3. **Overlap handling.** If a regex match and a semantic match flag the same block, how is it reported? Current thinking: regex wins (it's deterministic), semantic pass skips blocks already caught.
4. **Multi-category extraction.** V1 runs one profile at a time. Should the output support running multiple profiles against the same conversation and tagging each match with its category? Probably yes, but not v1.
5. **The profile ecosystem.** If profiles become genuinely useful and reusable, is there value in a shared profile library? How does that interact with the privacy concern that profiles reveal what you're looking for and therefore what you think about?

---

_Paired with: `devlog/ho-00-overview.md`_
_Parent framework: Constructive Interference_
_Feeds: Voice DNA (corpus analysis), Shodō (synthesis layer component)_
_See also: shodo-seed.md, voice-dna-seed-prompt.md_
