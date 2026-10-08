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
