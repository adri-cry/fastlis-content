# Wiring gaya diagram ke cron reels harian — rencana eksekusi

Status: MENUNGGU verdict Adri (diminta 2026-10-15 19:30 WIB, cron reels jalan 06:45 WIB).
Tanpa verdict: besok otomatis sinematik v2 seperti biasa. Jangan mulai wiring tanpa persetujuan.

## Fakta yang sudah dicek (2026-10-15 20:16 WIB)

- `reels/v2/diagram.html` (21 KB, update 06:19 WIB): prototipe gaya diagram untuk SATU topik
  spesifik (nilai kritis). 6 scene hardcoded (s0..s5) + timeline gsap dengan waktu enter
  hardcoded (0, 6.03, 12.73, 23.03, 32.63, 42.33), komposisi 52 detik.
  Komponen generik yang dipakai: chapter pill, judul dua-warna, tabel data animasi
  (baris terisi bertahap), alur 4 langkah berkonektor, kartu rangkuman bernomor,
  karaoke subtitle, watermark logo tiap frame, closing card + CTA follow.
- `scripts/build_reels_v2.py` (22 KB): builder harian sinematik. Antarmuka baku yang
  bisa dipakai ulang 70%:
  - Input: `content/hari-ini.json` key "reels" (s1 hook, s2 konteks, s3-s5 poin, s6 closing/CTA)
  - TTS: `/opt/hatch/bin/tts`, voice `avocado_v2:MAI_01`
  - Karaoke timing: whisper (`~/workspace/venvs/whisper`, model small di
    `~/workspace/models/faster-whisper-small`), fallback estimasi proporsional
  - Output: `reels/v2/daily.html`, `vo_daily.mp3`, `timings_daily.json`,
    `render_status.json` (progress live ke dashboard)
  - Mux: `build_reels_v2.py --mux` (VO + rotasi jingle 4 varian + faststart WAJIB)
- Cron `fastlis-daily-reels` (Asia/Jakarta 06:45, file
  `~/workspace/goals/fastlis-daily-content-pipeline/crons/daily/fastlis-daily-reels__daily@06:45:00.md`):
  langkah 2 memanggil `scripts/build_reels_v2.py`, langkah 4 render `v2/daily.html`,
  langkah 5 mux, 6 copy ke `~/workspace/fastlis-renders/YYYY-MM-DD/`, 7-8 sync dashboard.

## Checklist eksekusi (estimasi 1-2 jam)

1. Tulis `scripts/build_reels_v2_diagram.py`: impor fungsi TTS/whisper/mux/write_status
   dari `build_reels_v2` (jangan duplikasi logika audio).
2. Bangun composer scene generik: petakan s1..s6 hari-ini.json ke komponen diagram
   (s1 = hook question + lingkaran, s2 = konteks/tabel, s3-s5 = poin sebagai langkah
   alur atau baris tabel, s6 = rangkuman bernomor + closing card + CTA follow).
   Waktu enter tiap scene dihitung dari timing whisper (bukan hardcoded).
3. Output `reels/v2/daily.html` (timpa path yang sama supaya langkah cron 4-8
   tidak berubah) + `timings_daily.json` + `render_status.json`.
4. QA render sekali manual (TMPDIR=reels/.tmp, hyperframes lokal, no CDN), cek visual
   dengan Playwright screenshot: centering pixel (aturan OCD Adri), karaoke sinkron,
   watermark tiap frame, faststart + audio stream via ffprobe.
5. Kalau QA lolos: ubah langkah 2 definisi cron jadi memanggil builder diagram,
   update kalimat "gaya SINEMATIK v2" di cron. Kirim hasil ke WhatsApp (aturan
   auto-send), tunggu verdict Adri sebelum final (review gate).
6. Commit + push (Adri sudah setuju push manual 12:20 UTC; auto-push cron tetap OFF).

## Risiko

- Scene diagram yang generik bisa terlihat kaku untuk topik yang tidak tabular
  (mis. topik opini/mitos). Mitigasi: composer memilih komponen per tipe beat;
  kalau topik tidak cocok, fallback ke sinematik (keputusan per render, bukan
  per template).
- Render diagram 52 detik + whisper + TTS: total mirip pipeline sinematik (~5-10 menit),
  masih aman sebelum 06:45.
