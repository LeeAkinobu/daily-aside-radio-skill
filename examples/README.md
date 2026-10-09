# Sample episodes / サンプルエピソード

Two complete episodes produced with this skill on 2026-10-09, exactly as delivered: one in English, one in Japanese. Each folder holds the episode JSON, the five-part script, the timestamped primary sources, the mix manifest, and the music credit. The finished audio is attached to the [v0.1.0 release](https://github.com/LeeAkinobu/daily-aside-radio-skill/releases/tag/v0.1.0) so that the repository stays small.

| Episode | Script | Narration | Audio (MP3, 192 kbps) |
|---|---|---|---|
| English, 2026-10-09 | 969 words | gemini-3.8-flash-tts, voice Sulafat, 405.6 s | [daily-aside-2026-10-09-en.mp3](https://github.com/LeeAkinobu/daily-aside-radio-skill/releases/download/v0.1.0/daily-aside-2026-10-09-en.mp3) (7:34) |
| Japanese, 2026-10-09 | 2101 characters | gemini-3.8-flash-tts, voice Nika, 407.0 s | [daily-aside-2026-10-09-ja.mp3](https://github.com/LeeAkinobu/daily-aside-radio-skill/releases/download/v0.1.0/daily-aside-2026-10-09-ja.mp3) (7:35) |

Both were mixed with `radio.py mix --calibration-db 6.3`. The scripts use public information only (Nobel Prize press releases, UN and WHO campaign pages, JST and 文化庁 press releases, the NAOJ calendar). No weather, location, or personal material is included. The TTS output has not been edited; a listening check by the author found no mispronunciations worth re-recording.

## Music / 音楽

"Continue Life" by Kevin MacLeod (incompetech.com), licensed under [Creative Commons: By Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). Changes: looped, level-adjusted, ducked under narration, faded and mixed with narration. The same credit is embedded in each MP3's comment tag and in `credits.txt`.

## Licence of the samples / サンプルのライセンス

The sample scripts, episode metadata, and finished audio in this folder and in the release are published under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/), copyright 2026 Akinobu Lee, with the music credit above carried along. The code remains under the MIT licence in the repository root.

---

このスキルで 2026 年 10 月 9 日に実際に制作した 2 本のエピソード（英語・日本語）を、納品時のまま置いています。各フォルダには episode JSON、五部構成の台本、取得時刻付きの一次ソース一覧、ミックスの記録、音楽クレジットが入っています。音声ファイルはリポジトリを軽く保つため [v0.1.0 リリース](https://github.com/LeeAkinobu/daily-aside-radio-skill/releases/tag/v0.1.0) に添付しています。

台本は公開情報のみで構成し、天気・所在地・個人情報は含みません。TTS 出力は無編集です。音楽は Kevin MacLeod「Continue Life」（CC BY 4.0）をループ・音量調整・ダッキング・フェードして使用しています。サンプルの台本・メタデータ・音声は CC BY 4.0（著作権 2026 Akinobu Lee）、コードは MIT ライセンスです。
