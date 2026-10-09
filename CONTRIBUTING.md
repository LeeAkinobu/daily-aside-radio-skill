# Contributing

Thanks for taking an interest. A few ground rules keep the skill safe to share.

- **Offline first.** `python3 scripts/test_radio.py` and `python3 scripts/test_google_tts.py` must pass without network access, credentials, or paid requests. Add a test for any change to timing, caching, budgeting, or request handling.
- **No new dependencies.** The scripts use the Python standard library plus ffmpeg/ffprobe on purpose.
- **Never commit** episodes, caches, narration audio, music, or anything from a real account. `.gitignore` already excludes the usual files; keep it that way.
- **Keep the docs in step.** A change to a CLI flag, output file, or preset must be reflected in `SKILL.md`, the relevant `references/*.md`, `README.md`, and `README.ja.md`. Update the expected test count in the READMEs when adding tests.
- **Regenerate checksums** from the repository root after any change to tracked files:
  `git ls-files | grep -v SHA256SUMS | sort | xargs sha256sum > SHA256SUMS`
- **Live-provider changes** (model names, request shape, pricing assumptions) should cite the official page and the date you checked it, in the commit message or PR.

Small, focused pull requests are easiest to review. If you are unsure whether something fits, open an issue first.
