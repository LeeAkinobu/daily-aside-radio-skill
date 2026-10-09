# Changelog

## v0.1.0 — 2026-10-09

First public release.

- Skill (`skills/daily-aside/`): five-part episode format, validator with language-specific pacing presets, offline request planning, durable attempt ledger, response/WAV import, mixing with ducking and fixed music gaps, user-run Gemini TTS client with approval flag and local cost cap.
- Fixed: `mix` failed with "BGM ended unexpectedly" for MP3 beds; the bed is now looped in the filter graph.
- Changed: Japanese preset lowered to 1950–2250 characters from live measurements; the agent now asks every episode what personal material to include.
- Added: Japanese README, sample episodes (English and Japanese) with scripts and sources under `examples/`, a GitHub Pages player, CI for the offline tests.
