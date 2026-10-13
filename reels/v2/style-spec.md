# STYLE SPEC — FastLIS Reels Sinematik v2

Acuan gaya: video referensi @SATYAXBT (durasi 151.7 dtk, 720x1280, 30fps)
+ riset genre: cinematic map storytelling, Hormozi/karaoke caption trend.
Konten tetap edukasi lab (konteks beda, gaya yang diadopsi).

## 1. Referensi yang dianalisis

| # | Sumber | Ciri yang diambil |
|---|--------|-------------------|
| R1 | Video @SATYAXBT "sejarah AI" (151.7 dtk, dikirim Adri) | Struktur utama: VO storyteller + karaoke + chapter + kanvas sinematik |
| R2 | HYPEWHIP "The Algorithm Behind Google Maps Navigation" (IG reel) | Peta gelap + visualisasi data animasi sebagai ilustrasi narasi |
| R3 | Genre "cinematic map storytelling" / dokumenter After Effects | Kamera terbang pelan di atas kanvas, marker + rute animasi |
| R4 | Tren caption short-form (Hormozi-style, karaoke line, pop captions) | Aturan caption: word-level timing, font berat, satu gaya per series |

## 2. Motion (cara animasi masuk)

- **Judul/chapter**: fade + geser naik pelan (bukan pop).
- **Pin/marker**: pop dengan sedikit scale (spring pendek).
- **Rute/garis**: draw-on (garis kegambar bertahap).
- **Angka data**: count-up (angka berjalan naik ke nilai akhir).
- **Foto**: polaroid masuk dengan rotasi miring sedikit + drop halus.
- **Kamera**: SATU gerakan drift konstan sepanjang video (slow zoom + pan),
  tidak pernah diam total.
- **Transisi antar bagian**: crossfade + geser kamera, BUKAN hard cut.
  Terbukti: deteksi scene-change di R1 = 0 cut dalam 151 detik.
- **Kata aktif karaoke**: highlight warna + pop scale kecil (1.0 -> 1.08).

## 3. Layout (posisi elemen, kanvas 1080x1920)

```
+----------------------------------+
| timeline tipis (progress)        |  <- atas, 8px
|                                  |
|  LABEL CHAPTER (mono, kecil)     |  <- sepertiga atas
|  JUDUL BESAR (bold, 2-3 baris)   |
|                                  |
|  +----------------------------+  |
|  | visual pendukung           |  |  <- tengah: foto polaroid /
|  | (foto/diagram/kartu data)  |  |    kartu data / diagram
|  +----------------------------+  |
|                                  |
|  [ subtitle karaoke ]            |  <- sepertiga bawah (di atas
+----------------------------------+    safe-area tombol IG)
```

- Judul tidak pernah menutupi visual utama.
- Subtitle selalu di zona bawah yang sama, tidak pindah-pindah.
- Setiap beat = 1 ide = 1 visual pendukung (foto ATAU diagram ATAU kartu data).

## 4. Warna & font

- **Jumlah warna: 3.** Base gelap + 1 aksen + putih.
  - Base: navy-teal sangat gelap (`#071418`, diukur dari frame R1).
  - Aksen R1: oranye (`#f0a030`). **FastLIS pakai biru terang `#3B9EFF`**
    (varian terang dari brand `#0469DC` agar terbaca di atas gelap).
  - Teks: putih `#FFFFFF`.
- **3 layer font, tidak lebih:**
  1. Display: bold condensed, uppercase, tight (judul chapter). R1 pakai
     grotesque berat; FastLIS pakai Poppins 800 uppercase.
  2. Mono: label kecil letter-spacing lebar ("BAGIAN 01 · PRE-ANALITIK",
     label data, sitasi). Pakai ui-monospace.
  3. Sans semibold: subtitle karaoke (Poppins 600).
- Aksen dipakai hemat: kata kunci judul, kata aktif karaoke,
  progress timeline, marker. Sisanya putih di atas gelap.

## 5. Pacing

- **Visual baru muncul tiap 3-5 detik** di dalam satu chapter
  (foto masuk, lalu kartu data, lalu angka count-up, dst).
- **Chapter berganti tiap ~10-13 detik** (R1: 12 chapter / 151 dtk).
- **Tidak ada frame mati**: setiap 100ms ada minimal 1 elemen bergerak
  (drift kamera dihitung sebagai gerakan).
- Ritme per chapter: label+judul masuk (0-1 dtk) -> narasi jalan sambil
  visual pendukung muncul satu per satu -> crossfade ke chapter berikut.
- Total FastLIS: 35 dtk = hook (0-5) + 2-3 beat isi (5-28)
  + pertanyaan penutup + ajakan komen (28-35).

## 6. Audio

- **Narasi: santai, kontinyu, tanpa jeda.** Diukur: 0 jeda hening dalam
  20 detik sampel R1. Gaya storyteller ("Coba bayangin..."), bukan announcer.
  Kecepatan: pelan-menengah, artikulasi jelas.
- **Musik: ambient/instrumental pelan di bawah narasi**, tidak berkompetisi.
  FastLIS: jingle di volume 0.22 + fade in/out.
- **SFX: minimal.** R1 hampir tanpa SFX mencolok; biarkan narasi + musik
  yang bawa emosi. (Opsional: whoosh sangat pelan saat transisi chapter.)
- Aturan keras: narasi tidak boleh berhenti sementara tidak ada visual
  yang mendukung kalimat tersebut.

## 7. Adaptasi ke FastLIS (yang berubah dari template lama)

| Aspek | Template lama | v2 sinematik |
|-------|---------------|--------------|
| Driver | teks + musik | voice over + karaoke |
| Scene | 6 scene, hard cut | 3-4 beat, crossfade + drift |
| Background | foto full / putih | kanvas navy gelap + dot grid |
| Teks | statis per scene | karaoke word-highlight |
| Visual | kadang tanpa gambar | **WAJIB: tiap beat ada foto/diagram/kartu data** |
| Penutup | pill CTA kaku | pertanyaan terbuka + ajakan komen |

Catatan dari review sampel 15 dtk (2026-10-14): sampel v1 belum ada
gambar sama sekali, hanya tipografi. v2 final wajib ada layer visual
(foto lab gaya polaroid + caption, kartu data count-up, diagram alur).

## 8. Spesifikasi build (pipeline)

- Kanvas 1080x1920, 30fps, hyperframes + GSAP (struktur existing).
- VO: TTS `avocado_v2:MAI_01`, `--language id`, naskah gaya spoken
  (tulis angka terucap, pakai "..." untuk jeda dramatis).
- Karaoke: timing kata diestimasi proporsional dari durasi audio
  (bobot = panjang kata + jeda tanda baca); upgrade ke word-timestamp
  asli kalau nanti tersedia.
- Foto: pakai stok `html/` yang sudah di-tag; tampilkan sebagai polaroid
  (frame putih, tape, caption strip) atau kartu data untuk angka.
- Audio mix: VO penuh + jingle 0.22 + fade in 1 dtk / fade out 2 dtk.
- Output: H.264 + `-movflags +faststart` (syarat WhatsApp).
- Nama file: `reels/v2/style-spec.md` (file ini).
