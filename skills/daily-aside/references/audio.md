# Audio assembly and music rights

Require Python 3.10+ standard library plus ffmpeg and ffprobe. The implementation uses no Python third-party packages. It requires cached narration input to already be 24 kHz mono 16-bit PCM; mixes at 48 kHz stereo; exports PCM WAV and 192 kbps MP3. No browser, website, database, or server is required for the offline stage.

Timing:
- 10-second musical intro
- 5 narration parts with four exact 5-second music gaps
- 18-second musical outro, fading over its final 5 seconds
- Native edge silence from each synthesized part is preserved
- BGM is reduced by 8 dB during speech, smoothly restored during music-only regions

BGM gain defaults to 0.18; voice is unchanged unless summed peaks require a single whole-programme safety attenuation. This preserves dynamic range rather than using a compressor. The mix manifest records safetyGain and peakBeforeSafetyGain. MP3 decoding can create intersample/codec overshoot; verify final decoded peaks when quality-critical.

--calibration-db defaults to zero. A known source recording may have its own verified calibration; do not copy a number to an unrelated BGM file. Keep the exact approved file and calibration when recreating an existing listening experience, and disclose any change.

No music is bundled. For a CC BY track, verify its official track page and version of the license before download or redistribution. Preserve title, author, source, license link and description of modifications in metadata and credits.txt. The skill's future code license cannot replace or erase third-party music terms. If attribution cannot be supplied, use another authorized track.

The source player mixed narration and music only during playback; this implementation actually renders both into the output samples. Synthetic dry-run output proves file mixing/timing, not narration quality, music suitability, or a real provider integration.

## Optional piano source

A potential source is “Continue Life” by Kevin MacLeod, ISRC USUAN1100282:
https://www.incompetech.com/music/royalty-free/index.html?isrc=USUAN1100282

Do not assume that every existing copy carries the same license version. The currently indexed official page references CC BY 4.0, while older official material can reference 3.0. Verify the terms accompanying the actual download and record the source URL, retrieval date, file SHA-256, and license version. No copy is bundled. If that source confirms 4.0, use a credit such as:

“Continue Life” — Kevin MacLeod (incompetech.com). Licensed under Creative Commons Attribution 4.0: https://creativecommons.org/licenses/by/4.0/. Source: the verified official track URL. Changes: looped, level-adjusted, ducked, faded and mixed with narration.

Use calibration-db 6.30 only when reproducing the previously measured exact recording and approved balance. With a new download, measure or audition its level instead of assuming a matching master.

## Explicit conversion of other narration WAV formats

Import does not silently convert files. Preserve the original and, if the user wants to use an existing incompatible narration recording, explicitly create a new compatible file before import:

    ffmpeg -n -v error -protocol_whitelist file,pipe -i SOURCE.wav -ar 24000 -ac 1 -c:a pcm_s16le NEW_CONVERTED.wav

The -n option refuses to overwrite an existing output. Conversion changes sample rate/channel count and should be disclosed. Validate the converted file before caching, and do not claim that format conversion verifies its narration content.
