# Kiku — description

A hybrid regex-plus-LLM detector that runs the Destructive Interference taxonomy across a writer's accumulated AI-conversation corpus.

A diagnostic framework that cannot scale to a corpus cannot generalize. Kiku (聴く, "listen") is the operational answer — a two-tier detector that runs the eight named Destructive Interference failure classes across the practitioner's accumulated AI conversation history at speed. YAML-defined profiles drive the two tiers: fast regex matching for literal patterns, then Claude API semantic classification for the patterns that resist rules. The deeper argument is methodological: a taxonomy without instrumentation is a position paper, and instrumentation without a taxonomy is automated nothing — Kiku closes the loop, making the failure classes actionable at the corpus scale where sustained AI collaboration actually happens. It is in active personal use, built to the full Ho verification stack.

Python (mypy strict, flake8, full test coverage), combining regex matching with Claude API semantic classification driven by YAML-defined detection profiles.
