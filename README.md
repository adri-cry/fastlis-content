# FastLIS Content

Kumpulan template, foto, dan script untuk generate konten harian FastLIS
(carousel, single post, reels).

## Struktur Folder

```
fastlis-content/
├── carousel/          # Template carousel (5 slide) + hasil render slide*.png
├── single/            # Template single post + hasil render
├── reels/             # Project hyperframes untuk video reels
│   ├── index.html     # Definisi animasi
│   ├── hyperframes.json
│   ├── package.json   # npm scripts (preview/render/publish)
│   └── assets/        # Aset gambar buat reels
├── html/              # Aset HTML: base template, font, demo screenshot
├── photos/            # Pool foto (lab, dashboard, dll) buat carousel/single
├── content/           # Data konten harian (hari-ini.json)
├── archive/           # Arsip hasil per tanggal (YYYY-MM-DD)
│   └── <tanggal>/
│       ├── slide1-5.png
│       ├── single-post.png
│       └── fastlis-reels.mp4
├── scripts/           # Script Python generator
├── data/              # Tracking JSON (used_images, last_topics)
├── assets/            # Logo & aset global
└── backups/           # Backup template & script versi lama
```

## Script

Semua script pakai `BASE = "/root/.fastlis-content"` (absolute path).

| Script | Fungsi |
|--------|--------|
| `scripts/rebuild_today.py` | Render carousel dari `content/hari-ini.json` |
| `scripts/build_single.py` | Render single post |
| `scripts/render_all.py` | Pipeline lengkap: carousel + single + reels + QA + tracking |
| `scripts/qa_check.py` | QA cek konten |
| `scripts/archive_today.py` | Arsipkan hasil hari ini ke `archive/<tanggal>/` |
| `scripts/update_used.py` | Update tracking foto terpakai |
| `scripts/killchrome.py` | Bersihin proses chrome nyangkut |

## Cara Pakai

1. Edit `content/hari-ini.json` — isi topik, slide, foto.
2. Render carousel:
   ```bash
   python3 scripts/rebuild_today.py
   ```
3. Render single:
   ```bash
   python3 scripts/build_single.py
   ```
4. Atau sekali jalan semua:
   ```bash
   python3 scripts/render_all.py
   ```
5. Arsipkan hasil:
   ```bash
   python3 scripts/archive_today.py
   ```

## Reels (hyperframes)

```bash
cd reels
npm run preview    # preview animasi
npm run render     # render ke mp4
npm run publish    # publish
```

## Catatan

- **Jangan** hapus `content/hari-ini.json` tanpa backup — dipakai semua script.
- Backup template ada di `backups/` (v1, v2, neobrutalism).
- Foto yang sudah terpakai dicatat di `data/used_images.json`.
- Riwayat topik di `data/last_topics.json` (30 hari terakhir).

## v2 (2026-10-09, restore pasca VM replace)

- PENTING: repo tinggal di `~/workspace/fastlis-content` (hanya `~/` yang survive VM replace; `/root` ikut ke-wipe).
- `scripts/_common.py`: `BASE` dari env `FASTLIS_BASE` (default `~/workspace/fastlis-content`), deteksi Chrome otomatis.
- `scripts/cdp_shot.py`: screenshot via Chrome DevTools Protocol (stdlib only, port unik per proses). Pengganti flag `--screenshot` yang pernah gagal diam-diam (false positive).
- `scripts/generate_content.py`: generate `hari-ini.json` via LLM + guard anti topik kembar (alat bantu manual; jadwal resmi pakai agen langsung).
- `scripts/daily.py`: orkestrator manual (generate -> render_all -> reels -> git).
- `reels/`: hyperframes 0.8.31 terinstall lokal; gsap + font Plus Jakarta Sans di-vendor lokal (CDN diblokir di sandbox). Render: `TMPDIR=reels/.tmp npm run render` (/tmp cuma 512MB).
- Jadwal: cron `fastlis-daily-content` (~06:14 WIB, gambar) + `fastlis-daily-reels` (06:45 WIB, video). Push GitHub off (kirim ke chat dulu).

## Audit fixes (2026-10-09)
- Waktu: semua penanggalan pakai WIB (Asia/Jakarta), bukan UTC sistem.
- `PipelineLock`: cegah 2 run jalan bareng (jadwal vs manual).
- `cdp_shot.py`: profile Chrome di /tmp dibersihkan tiap run.
- `update_used.py`: DEPRECATED (berbahaya, hardcode 2026-09-15) jadi stub.
- `archive_today.py`: satu-satunya implementasi arsip, prune 30 hari.
- `killchrome.py`: hanya bunuh chrome headless nyangkut.
- `qa_check.py`: + cek foto duplikat antar slide, + batas caption 2200.
- `build_reels.py`: catat bg video ke today_video.
- `render_all.py`: prune backup hari-ini.json.bak-* >30 hari.
- `preview.py`: render 1 slide saja buat cek cepat.
- Cron: rotasi format dipaksakan (beda dari 3 hari terakhir).
