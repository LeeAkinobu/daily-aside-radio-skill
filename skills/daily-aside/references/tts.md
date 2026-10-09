# TTS integration boundary

The skill includes a user-run Google client (google_tts.py), plus request planning, durable attempt tracking, response import and safe reuse for an existing approved integration. Offline tools/tests never read credentials or make network calls. The Google client reads only the user-configured GEMINI_API_KEY at live execution, uses a fixed HTTPS Google endpoint, blocks redirects, and does not log credentials or automatically retry. It uses ordinary generateContent JSON/WAV, while the importer also supports streaming PCM responses.

Do not execute the live client as an agent unless the host offers a supported protected-credential route that complies with its current safety rules. Otherwise hand this one authenticated step to the user, or use an authorized TTS connector. Do not ask the user to paste credentials into the conversation or create credentials on their behalf. Installation alone does not configure a Google account, establish billing, authorize data transmission or approve charges.

Recheck model, voice, tags, output format, and prices in official provider documentation before live use:
- https://ai.google.dev/gemini-api/docs/speech-generation
- https://ai.google.dev/gemini-api/docs/pricing

For the previously evaluated Gemini 3.8 Flash TTS route, ordinary generation returns a WAV container, 24 kHz mono 16-bit PCM. Streaming responses may contain headerless signed 16-bit little-endian PCM; append chunks in order and add one WAV header only. Do not write WAV headers into the middle of the stream. Import only a complete response with terminal STOP. Reject other finish reasons, mixed audio formats, unsupported rates, malformed base64, truncated audio or oversized chunks.

The importer accepts provider response JSON or an ordered JSON list of streaming events, not raw SSE text. An integration must preserve event order and remove SSE framing first. Never treat an interrupted stream as a complete chunk.

Generated request plans use contents[].parts[].speech_metadata.style and generationConfig.speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName. Do not put style instructions in speech text. Voice names must be selected from the user's actual supported model. Recommended defaults, verified on 2026-10-09: Nika for Japanese, Sulafat for English; both are prebuilt voices of gemini-3.8-flash-tts and were used for the sample episodes. A previously preferred custom/library voice may be unavailable to other accounts.

The 4096 output-token cap per chunk is a quality/cost guard, not a provider-wide monetary limit. Reconfirm current pricing and give an episode-level estimate and cap before generation. All retries count toward the cap, including requests with lost responses. Price limits require the executing integration's own enforcement and user-approved billing controls; a local attempt log cannot cap usage by other apps. Do not hard-code a promise of a particular total cost.

Before the external request, run reserve. Cache ready chunks are immutable. A reserved attempt without imported audio is unknown, even after a timeout. Retry only when the user approves possible duplicate billing and the integration permits it, then explicitly reserve with --retry-unknown. Prefer recovering an existing provider response where supported. Never automatically resynthesize all five chunks.

## Local estimate guard

The automatic client requires current positive input/output USD prices per million tokens, a pricing-check date within 30 days, an approved episode-level estimated-total limit, and an explicit send-and-charge flag. It uses UTF-8 request bytes plus 2048 input-token overhead and the 4096 output-token maximum for a conservative per-request estimate. This is not a guaranteed monetary bound; explain the distinction. Attempts with unknown outcomes keep their estimated cost, and retries add a fresh reservation. Successful cached audio is returned without touching the credential or network. Earlier manually reserved unpriced attempts block the automatic client until billing is reconciled. The user should use provider billing controls as well.

Budget accounting is stored outside content-specific caches under the same cache root and a stable user-approved budget ID. Keep that ID across text/model/voice changes; prior attempts continue to consume its limit. A new episode needs a distinct explicitly approved budget ID. Do not rename the ID or change the cache root to bypass earlier charges. A content edition already associated with one budget cannot be silently moved to another.

## Service tier and private information

Check the current Gemini terms: https://ai.google.dev/gemini-api/terms . Unpaid services must not receive personal or confidential information. The CLI requires --service-tier paid or unpaid. It rejects unpaid generation unless config.contentClass is explicitly public; personal is the conservative default. This declaration must match the actual account/service and reviewed content; it is not a way to bypass the terms. Paid-service status does not itself authorize a private-data transfer. Disclose the recipient and exact content and obtain the host-required consent before sending.

For current authentication and billing setup, direct users to official instructions rather than copying old key-creation steps: https://ai.google.dev/gemini-api/docs/api-key and https://ai.google.dev/gemini-api/docs/billing/ . Do not create credentials, change persistent access, configure billing, or accept terms for users without the required authorization/handoff.
