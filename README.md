# The Daily Aside

A personal radio show for your day, with room to wander.

Turn a few notes and fresh public sources into an unhurried personal radio programme. Get a finished MP3 with music already mixed in, plus a WAV master, script, source list, and music credits. No player website is required.

## What it makes

- Five sections: an opening, three main topics, and one thought for tomorrow
- A mixture of everyday life, science, culture, and optional personal/work updates
- A musical introduction, four topic breaks, and a gentle outro
- English by default; configurable language, locale, programme name, DJ name, and delivery style
- Roughly eight minutes as a starting point, with actual duration measured after generation

Work updates are optional and take no more than 30–40% of a programme. The English preset is 850–1050 words; Japanese has its own 1950–2250-character preset. Other languages can supply an explicit spoken-text budget.

## Requirements

- An assistant that supports folder-based skills, or a Python command-line workflow
- Python 3.10+, ffmpeg, and ffprobe
- A supported Google Gemini TTS model/voice and the user's own configured credentials/billing, or an approved TTS integration / existing narration WAVs
- A music file the user is entitled to use, with attribution information

No music, credentials, real user episodes, private workspace links, or personal account information are distributed with the skill. Installing a skill does not configure a TTS account or approve its charges.

## Local setup for Codex or Claude Code

The repository name is `LeeAkinobu/daily-aside-radio-skill`. This is a private evaluation version; a public release will follow only after the owner completes acceptance testing and explicitly approves publication. The distributable skill is in `skills/daily-aside/`.

First check the dependencies in a terminal:

```sh
python3 --version
ffmpeg -version
ffprobe -version
```

Use Python 3.10 or later. If your system calls it `python`, substitute that command throughout. Install missing tools yourself from trusted official sources, following your normal permissions. This package does not install software or set up accounts.

### Codex CLI or IDE

From this repository's root, copy the skill into its project-local discovery folder:

```sh
python3 -c "import shutil; shutil.copytree('skills/daily-aside', '.agents/skills/daily-aside')"
```

Open this folder in Codex. Use `/skills` to find the skill, or mention `$daily-aside` in a prompt. The command intentionally refuses to overwrite an existing destination. For use across local projects, copy to `~/.agents/skills/daily-aside` instead. Do not keep duplicate installations with the same name unless you intend to select between them. These local discovery locations are documented in [OpenAI's skill guide](https://learn.chatgpt.com/docs/build-skills).

### Claude Code terminal

From the same repository root:

```sh
python3 -c "import shutil; shutil.copytree('skills/daily-aside', '.claude/skills/daily-aside')"
```

Open this folder in Claude Code and invoke `/daily-aside`. The command refuses to overwrite an existing copy. For use across local projects, copy to `~/.claude/skills/daily-aside` instead. Local personal files do not by themselves install the skill in Cowork or cloud sessions. These locations and invocation rules are documented in [Claude Code's skill guide](https://code.claude.com/docs/en/skills).

Both routes use the same portable SKILL.md, Python scripts, and references. No plugin marketplace installation is required for this local test. Agent permissions and credential handling still depend on the host. Agent-specific metadata in `agents/openai.yaml` is optional for the core workflow.

## Suggested acceptance-test prompts

### 1. Offline first

In Codex, start with `$daily-aside`; in Claude Code, start with `/daily-aside`, followed by:

> Run the offline regression tests and synthetic audio dry run for The Daily Aside. Do not read credentials, make network requests, generate paid speech, install software, or publish anything. Put test outputs in a new private directory outside the skill. Confirm that MP3 and WAV include background music, four five-second topic gaps, a ten-second intro, an eighteen-second outro, and the final five-second fade. Label synthetic tones clearly. Report any failures and which checks you did not perform.

Expected: 21 tests pass; the built-in dry run makes approximately 49.25 seconds of synthetic tones and music. This is a timing/format fixture, not a narrated eight-minute programme.

### 2. Prepare the first real episode without spending

> Prepare a roughly eight-minute episode of The Daily Aside in English, locale en-US, using public information only. Use today's date and ask for a coarse weather location if needed. Include science, culture, everyday life, and one thought for tomorrow. Save the five-part episode JSON, script and timestamped primary sources in a private output directory. Check which Gemini model and voice I can actually use, explain current pricing, and prepare the exact local generation command. Do not read my API key or call the paid API. Stop for my review of the script, voice, service tier, BGM rights and total spending limit.

### 3. User-run live test and finish

Review the script and configure your own credential through Google's current [API-key instructions](https://ai.google.dev/gemini-api/docs/api-key). Never put the key into a prompt, issue, repository file, or a command-line argument. Confirm the actual paid/unpaid service tier: unpaid Gemini services must not receive personal or confidential information. Review [current pricing](https://ai.google.dev/gemini-api/docs/pricing) and [provider terms](https://ai.google.dev/gemini-api/terms).

Run the prepared `google_tts.py --all` command yourself using your existing environment configuration, chosen voice/model, a stable approved budget ID and explicit spending approval. It generates five chunks and preserves successful ones. If a request fails with an unknown outcome, inspect it before authorizing a single-chunk retry; do not repeatedly run paid requests as a troubleshooting shortcut.

Then ask:

> The narration has been generated. Use the verified cached chunks and my authorized local BGM to render MP3 and WAV. Do not regenerate speech or incur any further charge. Measure the actual duration, check the final files decode, inspect peaks and timing, and provide the script, timestamped sources and music credits. Keep everything private. Tell me what still needs my listening check.

Listen for complete narration, pronunciation, voice consistency, music balance, transitions and the ending. Record the actual provider/voice, total duration and any problems without including keys or private scripts in a public issue. Live-provider and human listening checks remain the user's acceptance test.

## Start with a free offline check

From `skills/daily-aside/`:

```sh
python3 scripts/test_radio.py
python3 scripts/test_google_tts.py
python3 scripts/radio.py dry-run --out /path/to/new-test-output
```

The dry run uses synthetic tones rather than a spoken episode. Tests do not contact Google, read real credentials, or incur TTS charges.

## Make a programme

Ask the assistant: “Use The Daily Aside to make an eight-minute radio show in English. Include one short update from the notes I provide, then science, culture, and something useful for everyday life.”

The skill researches current primary sources, prepares an episode JSON and a five-part script, and checks its language-specific budget. Review the material going to the TTS provider, the selected voice/model and the episode spending limit before generation. Exact usage and input formats are in the skill's SKILL.md and references.

The bundled Google client generates one section at a time. It reuses verified successful audio, records attempts before sending, and never automatically retries an unknown request. It checks a local estimated-cost limit, but cannot guarantee the provider's final invoice or limit other applications using the same account. Check current provider pricing and use the provider's billing controls too.

Users can run the client using their own already-configured GEMINI_API_KEY. Never paste a key into an assistant chat, source file, command-line argument, issue, or output document. An assistant must respect its host's credential-handling rules; it may need to hand this authenticated step to the user or use an approved protected integration.

## Outputs

- episode.mp3: portable listening copy with music baked in
- episode.wav: uncompressed mix
- script.txt: five-part narration
- episode.json: episode configuration and timestamped sources
- mix.json: exact timing, gain information and music credit
- credits.txt: readable music attribution

Do not send personal or confidential information to unpaid Gemini services. The client requires the service tier and treats material as personal unless explicitly reviewed and marked public-only. Check the current provider terms even when using a paid service.

Keep generated episodes and caches private. Sharing the skill does not authorize sharing a user's episode, source material, or account information.

## Music and attribution

The current prototype does not bundle third-party tracks. Supply authorized music and a credit file recording the title, creator, source, license, and changes (looping, level adjustment, ducking, fades and mixing). The output includes that information. A code license would not replace a music license.

## Prototype verification

The offline and mocked-provider tests verify timing, format handling, cache integrity, duplicate-request guards, unknown-outcome handling, cost-estimate checks, redirects, and credential-free reuse. An independent synthetic-audio check confirmed that both exported formats contain music and approximately 8 dB ducking. No live paid-provider end-to-end test or subjective listening test has been performed for this package.

## License

The code, skill instructions, and bundled documentation are licensed under the [MIT License](LICENSE), copyright 2026 Akinobu Lee. No third-party music or FFmpeg binary is included. Music selected by a user retains its own license and attribution obligations; this code license does not relicense it.

## Release status

Private evaluation version for `LeeAkinobu/daily-aside-radio-skill`. The owner will run the final live-provider and listening tests in Codex or Claude Code. Public visibility will remain off until the owner explicitly approves it after testing. Setup references above were checked on 2026-10-09.
