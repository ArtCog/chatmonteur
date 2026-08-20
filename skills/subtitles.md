# Subtitles — burned-in captions standard

Based on Netflix Timed Text Style Guides + BBC Subtitle Guidelines. Goal: every session produces
**identical** subtitles. Locked; brand styling overrides only fonts/colors, never the rules.

## The #1 rule that gets broken: CASING

**Sentence case — normal capitalization, exactly as a book would print it. Never random/ALL-CAPS.**
- Capital letter only at sentence start and proper nouns. All-caps = shouting (BBC).
- Same casing rule for every subtitle in the project. No mixing.
- Emphasis = **inversion of the emphasized word** (paper chip, ink text), NOT colour,
  NOT capitalization, NOT a bigger font.
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

## THE STANDARD (locked — geometry from the tuner, style from the brand kit)

Captions never move. Size/position are a % of frame height/width so they hold at 1080p and
1440p. **Geometry** was set in the tuner; **style** (font, colour, plate) comes from the active
brand's `frame.md` and tokens. Rendered via ASS with PlayRes
pinned to the frame — see `references/edit-sequence.md` and the note below.

| Parameter | Value | px @1080 / @1440 | Why |
|---|---|---|---|
| **Font size** | **5.5% of frame height** | 59 / 79 | Артур 2026-07-24: 5% мелковато; 6% уже ест кадр |
| **Bottom margin** (MarginV) | **9% of frame height** | 97 / 130 | Sits ABOVE YouTube's player controls/progress bar (lower ~8–10% gets covered) |
| **Max line width** | **80% of frame width** | — | Short lines read faster; >85% makes the eye travel edge to edge |
| **Anchor** | bottom-center, `Alignment=2`, FIXED | — | 1 or 2 lines share the same bottom line; line 2 grows UP — captions never jump |
| **Font** | **Golos Text Bold** (brand) | — | Brand kit «Mono»; excellent Cyrillic. TTF in `assets/brand/default/fonts/` |
| **Colour** | paper `#FAFAF7` bold text **on a scrim** `rgba(8,9,10,.52)` | padding 0.27 em | Артур 2026-08-03 (отменяет решение 24.07 «без плашки»): рендерим карточку 04 как нарисована. Скрим = ASS BorderStyle 3, проверено на пёстром скринкасте — держит текст там, где тень не справлялась |
| **Accent** | key/spoken word **INVERTED**: paper chip, ink text `#0B0B0D` | chip padding 0.12 em | Карточка 04 + правило бренда «цвет не несёт текст». Жёлтый #FFD700 из субтитров УБРАН (следом за зелёным). Параметра `accent=` больше нет — выбирать нечего |
| **Emphasis** | = the Accent row (inversion); NEVER size-scaled, NEVER caps | — | size-scaling and caps остаются запрещены |

## The five variants — the agent PICKS PER VIDEO, then asks

Geometry above is identical for all five; only the per-word motion and font differ.
Pass `variant=` to the `subtitles` capability. Verified on real frames over a busy
screencast (2026-08-03) — previews in `черновик/СУБТИТРЫ-v2-*.png`.

| `variant=` | Look | Use it for | Font |
|---|---|---|---|
| `clean` | whole line, soft-in, no per-word motion | the safe default; dense talking-head | Golos Bold |
| `read_aloud` | words fade in one-by-one, synced to speech | narrated key lines, the hook | Golos Bold |
| `accent` | the marked word (`"emph": true`) inverted into a chip | a single punch-word per line | Golos Bold |
| `typewriter` | chars typed in + `▌` cursor, 23/26 size | "agent typing live" / terminal moments | JetBrains Mono |
| `highlight` | whole line visible; the SPOKEN word inverts into the chip in sync | the dominant modern look (Hormozi/CapCut era) | Golos Bold |

**Choosing is an APPROVAL GATE — never silently default past it.** Propose the fittest
variant for the video's tone and ASK the user to confirm or switch. One
variant per video unless they ask to mix. Accent words: the agent marks them in the
transcript (`"emph": true`) by MEANING (terms, numbers, names — not random).

Colour default of the whole pipeline: NO grade — the original look; a LUT is an explicit
agent-asked choice (`color` passes through when `lut` is empty).

> Baseline agreed in the tuner + design kit; WILL be refined. When it changes, update HERE and in
> `chatmonteur/tools/subtitles.py` (the `_to_ass` constants) together. Verify on a real frame —
> libass scales SRT+force_style by its 288 PlayResY; we use ASS with real PlayRes to get true pixels.

## What the tool automates vs what YOU (the agent) must do

The `subtitles` capability enforces the **deterministic** half of the spec automatically:
CPL 39 (Cyrillic-friendly wrap), orphan-safe line breaks (prepositions stay with their noun),
and timing fit (min 0.83 s, ≤17 CPS, no cue overlap — `_fit_timing`). Don't hand-tune these.

The **semantic** half is YOURS and is NOT scripted (a naive pass would break it, like the deleted
`cut_meaning`): **casing** (never lowercase a proper noun — «Claude», «OBS», names) and **ASR
mishear repair** («код-код» → Claude Code). Fix these in the transcript text before burning.

## Build procedure

1. Transcribe with word timings. **Fix ASR mishears by meaning** before writing cues (brands and technical terms suffer most), and apply proper capitalization/punctuation — a raw transcript is uncased garbage; never burn it as-is. **Delete Whisper's ghost credits**: the RU model hallucinates lines like «Субтитры делал DimaTorzok» / «Субтитры сделал …» / «Продолжение следует» on silence — they are NEVER real speech; drop the whole segment. Fix mangled anglicisms the same pass («код-код» → Claude Code, «капкат» → CapCut).
2. Segment into ≤2-line cues respecting CPL and CPS; break at clause boundaries. *(The tool does this — CPL 39, orphan-safe breaks, timing fit. Override only for a deliberate reason.)*
3. Build the cue file with ONE style: SRT + `force_style` (simple) or ASS (per-word chip / karaoke).
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
- [ ] scrim on, accent by INVERSION only, one emphasis word · [ ] lower-center, clear of key content
- [ ] `variant=` confirmed with the user for this video (clean / read_aloud / accent / typewriter / highlight)

## Sources

- [Netflix — Timed Text Style Guide: General Requirements](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements)
- [Netflix — Russian Timed Text Style Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215346638-Russian-Timed-Text-Style-Guide)
- [BBC Subtitle Guidelines](https://www.bbc.co.uk/accessibility/forproducts/guides/subtitles/)
