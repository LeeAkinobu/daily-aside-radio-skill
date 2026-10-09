# CLAUDE.md

Guidance for coding agents working in this repository.

## What this is

A folder-based agent skill, `skills/daily-aside/`, that turns researched notes into a five-part
personal radio episode with background music. Everything in `skills/daily-aside/` is the
distributable; the repository root holds the README, license and `SHA256SUMS`.

## Layout

- `skills/daily-aside/SKILL.md` — the skill instructions an agent follows. Keep it in sync with the CLI.
- `skills/daily-aside/scripts/radio.py` — validation, request planning, cache/import, offline mixing.
- `skills/daily-aside/scripts/google_tts.py` — user-run Gemini TTS client. Never executed by tests or agents.
- `skills/daily-aside/references/` — editorial format, episode JSON schema, TTS boundary, audio rules.
- `examples/` — finished sample episodes (metadata only; the MP3s are release assets). Do not regenerate or edit them casually.
- `.claude-plugin/` — plugin and marketplace manifests; the repository root is the plugin. Bump `version` in both files on release.
- `README.md` and `README.ja.md` — keep both in sync when changing user-facing text.

## Commands

Run from `skills/daily-aside/`:

```sh
python3 scripts/test_radio.py          # offline regression tests
python3 scripts/test_google_tts.py     # mocked-provider tests, no network
python3 scripts/radio.py dry-run --out /path/to/new-dir   # synthetic 49.25 s fixture
```

Requires Python 3.10+ (standard library only), ffmpeg and ffprobe.

## Rules

- No network calls, credential reads or paid requests in tests or offline commands.
- Do not add third-party Python dependencies.
- Never commit episodes, caches, narration audio, music or credentials. `.gitignore` already excludes them.
- After changing any tracked file, regenerate the checksum list from the repository root:
  `git ls-files | grep -v SHA256SUMS | sort | xargs sha256sum > SHA256SUMS`
- If you change a CLI flag or output name, update `SKILL.md`, the relevant `references/*.md` and the README.
- Update the expected test count in the README when adding or removing tests.
