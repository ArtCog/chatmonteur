# Subtitles — burned-in captions standard

Based on Netflix Timed Text Style Guides + BBC Subtitle Guidelines. Goal: every session produces
**identical** subtitles. Locked; brand styling overrides only fonts/colors, never the rules.

## The #1 rule that gets broken: CASING

**Sentence case — normal capitalization, exactly as a book would print it. Never random/ALL-CAPS.**
- Capital letter only at sentence start and proper nouns. All-caps = shouting (BBC).
- Same casing rule for every subtitle in the project. No mixing.
- Emphasis = **accent color on the emphasized word**, NOT capitalization, NOT a bigger font.
- (ALL-CAPS acceptable only for short on-screen UI labels — never for spoken dialogue.)

## Locked numeric spec

| Parameter | Value | Source |
|---|---|---|
| Max lines per cue | **2** (16:9); 3 only for vertical 9:16 | Netflix / BBC |
| Max characters per line | **≤ 42** latin; aim **37–39** for Cyrillic (wider glyphs) | Netflix / BBC |
| Reading speed | **≤ 17 CPS** adult (SDH ≤ 20, children ≤ 13) | Netflix |
| Min duration on screen | **≥ 0.83 s** — never flash | BBC |
| Max duration | ~7 s | Netflix |
| Min gap between cues | ≥ 2 frames | Netflix |
| Line breaks | at clause boundaries; balance line lengths; never split noun+adjective or preposition+noun | BBC |

## Styling (defaults; the user's brand kit overrides)

- **One font, one size for the whole video.** Default height ≈ **4.5% of frame height** (1080p → ~48, 1440p → ~64).
- Base color near-white; **black outline** (3 px @1080p / 4 px @1440p) + shadow 1 — readable on any footage.
- Emphasis word: accent color recolor only.
- Position: lower-center (`Alignment=2`, `MarginV` ≈ 70 @1080p / 95 @1440p). Keep clear of important on-screen content — never caption over the thing the viewer must see.

## Build procedure

1. Transcribe with word timings. **Fix ASR mishears by meaning** before writing cues (brands and technical terms suffer most), and apply proper capitalization/punctuation — a raw transcript is uncased garbage; never burn it as-is.
2. Segment into ≤2-line cues respecting CPL and CPS; break at clause boundaries.
3. Build the cue file with ONE style: SRT + `force_style` (simple) or ASS (per-word accent color / karaoke).
4. Burn in, forcing the locked style (never trust the SRT's own casing/size):
```bash
ffmpeg -i video.mp4 -vf "subtitles=subs.srt:fontsdir='<fonts-dir>':force_style='FontName=<Font>,FontSize=64,PrimaryColour=&H00EBEDE8,OutlineColour=&H00000000,BorderStyle=1,Outline=4,Shadow=1,Alignment=2,MarginV=95'" \
  -c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p -c:a aac -b:a 256k out.mp4
```
   - ASS/SRT colors are **BGR hex** `&HAABBGGRR` (e.g. `#E8EDEB` → `&H00EBEDE8`).
   - Custom fonts need `fontsdir` pointing at the folder with the TTF.
5. **Verify on 2–3 extracted frames** (casing/size/position uniform) before the full render.

## Checklist (every subtitle job)

- [ ] sentence case, no random caps  · [ ] one font size everywhere · [ ] ≤2 lines
- [ ] CPL within limit (≤39 Cyrillic / ≤42 latin) · [ ] ≤17 CPS, ≥0.83 s per cue
- [ ] outline+shadow on; accent color only on emphasis words · [ ] lower-center, clear of key content

## Sources

- [Netflix — Timed Text Style Guide: General Requirements](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements)
- [Netflix — Russian Timed Text Style Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215346638-Russian-Timed-Text-Style-Guide)
- [BBC Subtitle Guidelines](https://www.bbc.co.uk/accessibility/forproducts/guides/subtitles/)
