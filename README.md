# FastLIS Content

Pipeline konten Instagram harian FastLIS (sistem informasi laboratorium).
Jalan otomatis tiap pagi via cron: gambar (carousel + single post) jam 06:14 WIB,
video reels jam 06:45 WIB. Hasil dikirim ke WhatsApp untuk review.

## Struktur Folder

```
fastlis-content/
├── assets/            # Logo & brand assets
├── carousel/          # Template carousel (template.html, 5 slide)
├── single/            # Template single post (template.html)
├── content/           # hari-ini.json (konten hari ini) + naskah-reels-*.md
├── data/              # Tracking: last_topics.json, used_images.json, photo_tags.json
├── docs/              # Dokumentasi & referensi (demo bank, panduan TTS, dll)
├── html/              # Bank foto lab + fonts + screenshot demo (LIVE, dipakai template)
├── reels/
│   ├── assets/        # Jingle (4 varian), SFX, fonts, logo buat video
│   ├── v2/            # Output build harian (gitignored, jangan commit)
│   ├── hyperframes.json
│   └── package.json   # hyperframes 0.8.31 (lokal, jangan install ulang)
├── scripts/
│   ├── render_all.py               # Pipeline gambar: carousel + single + QA
│   ├── rebuild_today.py            # Render carousel dari hari-ini.json
│   ├── build_single.py             # Render single post
│   ├── qa_check.py                 # QA: foto, duplikat, caption, relevansi
│   ├── cdp_shot.py                 # Screenshot via Chrome DevTools Protocol
│   ├── archive_today.py            # Arsip hasil ke folder tanggal
│   ├── build_reels_whiteboard.py   # Builder reels whiteboard (VO+animasi+karaoke)
│   ├── render_reels.py             # Wrapper render hyperframes + progress
│   ├── whisper_times.py            # Timing kata buat karaoke (dipakai builder)
│   ├── export_dashboard.py         # Export data.json buat dashboard publik
│   ├── sync_dashboard.sh           # Sync media ke sabaraya-server
│   ├── _common.py                  # BASE path, WIB today, PipelineLock
│   └── tools/                      # Generator sekali pakai
│       ├── make_jingle_variants.py # Bikin 4 varian jingle
│       └── make_sfx.py             # Bikin sound effect
└── backups/           # Backup template versi lama
```

## Alur Harian

**1. Konten gambar (06:14 WIB)** — `scripts/render_all.py`
- Baca `data/last_topics.json` (topik harus fresh, format beda dari 3 hari terakhir)
- Tulis `content/hari-ini.json` baru (5 slide + single + key `reels` buat video)
- Render + QA (foto relevan per slide, caption ≤2200, slide 5 = endcard)
- Commit lokal, sync dashboard, kirim 6 PNG + caption ke WhatsApp

**2. Video reels (06:45 WIB)** — `scripts/build_reels_whiteboard.py`
- `--tulis-naskah`: tulis `content/naskah-reels-YYYY-MM-DD.md` dari key `reels`
- `--daily`: build `reels/v2/daily.html` dari naskah (whiteboard hand-drawn, 6 scene)
- VO via TTS, timing karaoke via whisper, kamera zoom/pan per scene
- Render hyperframes (`TMPDIR=reels/.tmp`, /tmp cuma 512MB)
- Mux: VO + jingle + SFX, flag `+faststart` wajib (syarat WhatsApp)
- Kirim mp4 ke WhatsApp

## Aturan Konten

- Istilah: selalu **"kritis"**, jangan "panik" (nilai kritis, batas kritis)
- Slide 1: judul harus pertanyaan hook yang bikin penasaran
- Judul: baris 1 polos + baris 2 highlight kuning (jangan kepotong)
- Foto: relevan dengan ISI tiap slide, tolak tag "bukan foto lab"
- Minimal 1 slide berisi data konkret yang layak di-screenshot
- CTA spesifik (save/tag/komen), bukan "geser" generik
- Naskah reels: tempel teks langsung di chat kalau diminta (bukan file)

## Aturan Git

- Hasil render (mp4, png harian, archive) **JANGAN** di-commit — lihat `.gitignore`
- Distribusi hasil via dashboard publik + folder `fastlis-renders/`
- Yang di-commit: script, template, naskah, bank foto, data tracking

## Catatan Teknis

- Repo harus di `~/workspace/fastlis-content` (hanya `~/` yang survive VM replace)
- `BASE` dari env `FASTLIS_BASE`, default `~/workspace/fastlis-content`
- Semua penanggalan pakai WIB (Asia/Jakarta), bukan UTC
- `PipelineLock` cegah 2 run jalan bareng
- Screenshot via CDP (`cdp_shot.py`), bukan flag `--screenshot` Chrome
- Render browser tanpa internet: GSAP + font di-vendor lokal di `reels/assets/`
- Root div hyperframes wajib `data-composition-id`, `data-duration`, `data-width/height`
- Jangan pakai GSAP `repeat:-1` di template render (bikin hang)
- TTS voice `avocado_v2:MAI_01` punya quirk pengucapan — verifikasi via TTS→whisper round-trip
