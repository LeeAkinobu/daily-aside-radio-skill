---
name: daily-aside
description: Create a calm, personalized radio episode with researched topics, a five-part script, and background music baked into downloadable MP3/WAV files. Use when a user asks for a personal radio programme, an audio daily briefing with music, or an offline radio mix. Programme name, DJ name, delivery style, and supported TTS voice are configurable; no website UI is required.
---

# The Daily Aside

Produce an audio file the user can play anywhere. Resolve bundled scripts/ and references/ paths relative to the directory containing this SKILL.md, not the current project directory. Pass absolute paths to private input/output/cache locations when running scripts from elsewhere. Keep all user-specific material in a private working directory outside this skill. Do not use the skill directory for generated programmes, inputs, logs, or caches.

## Establish the episode

1. Confirm the user's date/time zone, coarse weather location when needed, preferred programme/DJ names, and mood.
2. Always ask what personal material the episode should carry before writing. This programme is made for one listener, so offer the choice every time rather than waiting to be told: (a) a few lines they type now about their day, week, work, or mood; (b) a connected source they explicitly authorize for this episode, such as a calendar or task list, with the understanding that reading it does not by itself permit sending its contents to a TTS provider; (c) nothing personal, public topics only. Record the answer in config.contentClass. Use only what they supplied or authorized; never look for personal information on your own, and never require it.
3. Use `references/editorial.md` for the five-part format. Research fresh claims in primary sources and record an HTTPS source plus a timezone-aware retrieval timestamp. Do not invent inaccessible task/calendar information.
4. Choose the programme language and locale (English by default). Create an episode JSON following `references/episode-format.md`. Make names and delivery style configurable. Default to a generic unnamed host; do not embed a real person's likeness, proprietary agent name, or personal project details.
5. Run `python3 scripts/radio.py validate EPISODE.json`. Use the language-specific spoken budget: English defaults to 850–1050 words, Japanese to 1950–2250 characters excluding whitespace and pause tags. These are pacing presets, not interchangeable units. Other languages require an explicit speechBudget. Exactly five segments are required.

## Obtain narration safely

Read `references/tts.md` before any TTS use. Use an existing approved TTS integration, or the bundled user-run Google client described below. The client reads a credential only when the user executes live generation. Do not invent a usable connector or silently select another provider. Manual response/voice import remains a fallback.

Check whether the Google service is paid or unpaid. Do not send personal or confidential text to unpaid Gemini services; use public-only content or a suitably approved paid service. Read the current provider terms and apply all host privacy rules. Set config.contentClass accurately (public, personal, or confidential; default personal). Do not mark private material public just to pass a check.

Before sending text for TTS, disclose the provider, the exact material sent, selected supported voice/model, price estimate, currency and total spending limit. Apply the host assistant's current approval and sensitive-data rules. Permission to read a connected inbox is not permission to send its contents to a TTS service. Minimize or omit sensitive material. Obtain required permission for transmission. Keep API credentials out of chats, scripts, command lines, episode files, logs, and the shared skill. The user must set up credentials through their supported secure flow.

Keep the preferred voice when supported. If it cannot be verified, ask for a supported alternative; do not silently change the established voice. Never copy another user's approval or account into this workflow.

### User-run Google client

If the user has already configured GEMINI_API_KEY in their own environment, provide the following command with verified model/voice, current prices and their approved budget. The user runs it themselves unless the host provides a specifically supported protected-credential execution route. As an agent, do not read, print, enter, configure, or transmit the key yourself; follow the host's credential handoff rules. Do not ask for a key in chat. Never run this client during offline testing.

    python3 scripts/google_tts.py --episode EPISODE.json --cache PRIVATE_CACHE --model VERIFIED_MODEL --voice VERIFIED_VOICE --all --service-tier CONFIRMED_TIER --budget-id APPROVED_EPISODE_ID --input-usd-per-million CURRENT_INPUT_PRICE --output-usd-per-million CURRENT_OUTPUT_PRICE --max-estimated-total-usd APPROVED_LIMIT --pricing-checked-at YYYY-MM-DD --approve-send-and-charge

The --all command generates missing chunks 0 through 4 in order and skips ready chunks. For an explicitly approved retry, select one --chunk INDEX with --retry-unknown; do not retry unknown chunks as a batch. Reuse the same budget ID and cache root across all text/model/voice revisions of the approved episode. Do not start a new budget ID to evade prior spending; obtain a new approval that accounts for previous charges when scope changes. Each completed chunk is reused without reading credentials or making another request. The client records conservative estimated cost before sending, rejects a request over the local estimate limit, and never automatically retries. An uncertain failure requires fresh retry approval and --retry-unknown. The Google account's actual invoice and billing controls remain authoritative. A local estimate is not a guaranteed/provider-wide spending cap.

If using an approved TTS connector instead, follow the plan/reserve/import route below. Do not mix unpriced manual attempts into the automatic client's budget ledger. Reconcile earlier charges first.

### Approved integration or manual import

Prepare the request plan without network access:

    python3 scripts/radio.py prepare --episode EPISODE.json --cache PRIVATE_CACHE --model MODEL --voice VOICE --out PRIVATE_REQUESTS

Before each approved external TTS request, reserve that exact chunk. Reservation records an attempt even if the provider response is lost:

    python3 scripts/radio.py reserve --episode EPISODE.json --cache PRIVATE_CACHE --model MODEL --voice VOICE --chunk 0

Send only that chunk's generated request with the approved integration. Do not automatically retry on timeouts or ambiguous failures. Import its complete response JSON (or an ordered JSON list of streaming events):

    python3 scripts/radio.py import-response --episode EPISODE.json --cache PRIVATE_CACHE --model MODEL --voice VOICE --chunk 0 --response RESPONSE.json

Repeat for the five chunks, skipping verified cached chunks. `prepare` reports ready/missing/unknown states. An unknown attempt requires renewed retry approval and the explicit `reserve --retry-unknown` flag. If using local narration WAVs instead, import with `import-wav` and the same episode/model/voice identity. Do not claim that imported files prove what the provider was asked to say; confirm provenance with the user/integration and audit the audio before delivery.

## Mix and deliver

Read `references/audio.md`. Require Python 3.10+, ffmpeg and ffprobe. Check installed tools first; obtain any installation permission required by the host environment. Do not install packages automatically.

Use only user-authorized music with known rights and a complete credit JSON. This prototype contains no third-party music. Fetching music is not permission to redistribute it without attribution or to relicense it.

    python3 scripts/radio.py mix --episode EPISODE.json --cache PRIVATE_CACHE --model MODEL --voice VOICE --bgm MUSIC.mp3 --credit CREDIT.json --out NEW_OUTPUT_DIRECTORY

Output a baked-in `episode.mp3` and `episode.wav`, plus `script.txt`, `episode.json`, `mix.json` and a readable `credits.txt`. Files are private deliverables; sharing the skill does not share episodes. Do not automatically publish any episode or source information. Prefer MP3 for everyday listening and preserve WAV when desired. Attach files using the host's supported native file-delivery tools, not inaccessible local paths.

Verify five complete spoken sections, duration and file decoding, BGM at the intro/gaps/outro, readable music credit, no clipping, and no unintended private information. State whether a listening check was actually performed. Approximately eight minutes is a target, not a guarantee. Do not secretly stretch speech or incur another TTS charge to meet it.

## Test without spending

Run `python3 scripts/test_radio.py` and `python3 scripts/test_google_tts.py` for offline/mock regression tests and `python3 scripts/radio.py dry-run --out NEW_TEST_DIRECTORY` for locally synthesized test tones. Neither command reads credentials or sends network requests. Label these outputs as synthetic QA fixtures, never as a narrated episode. Do not attach fixtures unless requested.
