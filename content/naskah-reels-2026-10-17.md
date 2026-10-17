# Naskah Reels — 2026-10-17
Topik: TAT (turnaround time): target waktu rilis hasil lab + 3 cara menjaga timer tidak jebol

## Spesifikasi produksi
Gaya: whiteboard hand-drawn — kertas putih #FBF9F4 + pola titik, font Caveat Bold, garis bergelombang (wobble), aksen biru FastLIS #1B5FD9, merah #E5484D hanya untuk "bahaya/telat"
Kanvas: 1080 x 1920 vertikal (9:16), 30 fps
Safe zone: teks & ilustrasi di x 80–900, y 220–1450
Font minimum: judul 110px, baris utama 72px, baris kedua 60px, karaoke 64px bold (y ≈ 1350)
Karaoke: timing tiap kata asli dari whisper (bukan tebakan), highlight stabilo kuning #FFE45E
Progress tracker: 3 titik kiri atas (y ≈ 250) mulai beat 3, titik aktif biru
Voice over: AI voice avocado_v2:MAI_01, Bahasa Indonesia, tempo cepat-santai, jeda 0.2 dtk antar kalimat
Musik latar: jingle FastLIS energetic (volume 12%, fade in 1.5 dtk, fade out 2.5 dtk)
SFX (volume ±25%): scribble saat garis digambar, pop saat elemen muncul, tick-tick jam, ding saat centang, swoosh saat transisi
Durasi: ±33 detik, 6 beat
Tipe scene: title_sw / timeline / steps / dashboard / alarm / closing_stamp (spesifik, ada ilustrasi) atau title / stage / checklist / flow / stamp / closing (generik)

## ATURAN WAJIB GERAK
- Tidak boleh ada frame diam lebih dari 0.4 detik. Tiap ≤0.5 dtk harus ada gerakan baru (elemen baru, emphasis, atau idle).
- Kamera bergerak KONTINU sepanjang beat (tidak berhenti di tengah), easing easeInOutCubic.
- Kamera tidak boleh sama dua beat berturut-turut.
- Latar titik-titik bergerak parallax 0.5x kecepatan kamera (kedalaman).
- Ada drift kamera halus sepanjang video: rotasi ±0.4° bolak-balik, siklus 3 dtk (kesan handheld).
- Garis boil: semua coretan bergetar tipis 8 fps (ala animasi tangan).
- Sprite spidol biru (tangan memegang spidol) mengikuti ujung garis setiap kali ada elemen digambar, lalu keluar frame ke kanan bawah.

## KAMUS ANIMASI (dipanggil di tiap beat)
M1 DRAW: stroke-dashoffset 100%→0, 0.4–0.6 dtk, easeInOut, spidol mengikuti ujung garis.
M2 POP: scale 0.5→1.15→1.0, naik 30px, rotasi -4°→0, 0.3 dtk, easeOutBack.
M3 WORD-IN: tiap kata teks masuk dari bawah 36px + opacity 0→1, 0.18 dtk, mulai tepat di timestamp kata itu (whisper).
M4 IDLE: setelah muncul, elemen terus hidup: melayang ±6px siklus 2 dtk, jarum stopwatch terus jalan, lonceng bergoyang pelan, tabung bergoyang ±2°.
M5 EMPHASIS: saat kata kunci diucapkan: scale 1→1.18→1 (0.25 dtk) + guncangan 3px + SFX pop + percikan 4–5 garis kecil di sekeliling elemen.
M6 KARAOKE: highlight kuning menyapu kiri→kanan di kata aktif (0.12 dtk), kata aktif scale 1.08, kata sebelumnya kembali normal.

## TRANSISI (tiap beat beda, durasi 0.4 dtk, tumpang tindih dengan kalimat terakhir beat sebelumnya, SFX swoosh)
T1 (B1→B2) ZOOM-THROUGH: lingkaran stopwatch membesar sampai memenuhi layar, isi lingkaran jadi kertas beat 2.
T2 (B2→B3) WHIP-PAN: seluruh isi geser cepat ke kiri dengan motion blur horizontal, beat 3 masuk dari kanan.
T3 (B3→B4) SCRIBBLE-WIPE: spidol menggambar coretan zig-zag besar menutupi layar (0.25 dtk), lalu terhapus oleh tangan penghapus memperlihatkan beat 4.
T4 (B4→B5) BURST: tabung merah "meledak" jadi percikan coretan, flash putih 0.1 dtk, lonceng jatuh dari atas dengan bounce masuk ke beat 5.
T5 (B5→B6) PAGE-FLIP: kertas diangkat dan di-scroll ke atas, kertas baru naik dari bawah, ada bayangan lipatan.

## Beat 1 — title_sw (0–4 dtk)
Visual: frame pertama langsung ada stopwatch gambar tangan, jarum berputar cepat, arc merah memenuhi. Judul besar di atasnya, sub di bawah.
Animasi: 0–0.3 dtk stopwatch M1 + tick-tick; judul M3 kata per kata (kata "telat" M5 + garis bawah merah bergelombang M1); sub M2 saat kata "3"; stopwatch M4 (jarum terus berputar, bergetar makin kencang menjelang akhir beat).
Kamera: zoom-in (scale 1.0→1.25, fokus ke stopwatch lalu naik ke judul, sepanjang beat)
Transisi keluar: T1
Judul: Hasil lab<br><span class="blue">telat keluar... lagi?</span>
Sub: 3 cara jaga TAT
Narasi: Hasil lab telat keluar lagi? 3 cara jaga TAT biar nggak jebol.

## Beat 2 — timeline (4–8.5 dtk)
Visual: kotak label "DEFINISI" (biru). Garis waktu horizontal: tabung sampel (kiri) → kertas hasil (kanan), stopwatch kecil di tengah garis. Label "SAMPEL DITERIMA" kiri, "HASIL DIRILIS" kanan.
Animasi: kotak M1 saat kata "timer"; tabung M1+M2 saat "sampel"; garis menjalar ke kanan M1 sambil stopwatch kecil meluncur mengikuti ujung garis; kertas hasil M2 + M5 saat "dirilis"; baris teks M3; semua M4.
Kamera: zoom-out (scale 1.3→1.0, lalu geser pelan ke kanan 40px mengikuti garis)
Transisi keluar: T2
Kotak: DEFINISI | biru
Baris: TAT = timer dari sampel masuk | sampai hasil keluar
Narasi: TAT itu timer. Mulai dari sampel diterima, sampai hasil dirilis.

## Beat 3 — steps (8.5–14 dtk)
Visual: angka "1" dilingkari + headline. 3 titik di garis waktu: Terima → Analisis → Rilis, jam di bawah tiap titik (08:02 / 08:20 / 08:41). Di bawah: kata "TAT" dicoret, muncul "tebakan?" merah.
Animasi: lingkaran angka M1 saat "Satu" (titik progress pertama menyala); headline M3 per kata, "catat" M5; titik 1-2-3 M2 berurutan sesuai "terima, analisis, rilis", tiap titik diikuti jam yang berganti angka cepat (efek odometer) lalu berhenti; saat "tebakan" coretan merah M1 di "TAT" + guncangan; semua M4.
Kamera: geser-kanan (translate 0→-120px sambil scale 1.05→1.15, mengikuti urutan titik)
Transisi keluar: T3
Kotak: 1 | hitam
Baris: Catat tiap titik waktu | Nggak dicatat, TAT cuma tebakan
Narasi: Satu. Catat tiap titik waktu. Terima, analisis, rilis. Nggak dicatat, TAT cuma tebakan.

## Beat 4 — dashboard (14–20 dtk)
Visual: angka "2" dilingkari + headline. Sketsa layar dashboard; di dalamnya antrean tabung menumpuk, warna bergeser hijau → oranye → merah. Panah melingkar "numpuk!" menunjuk bagian merah.
Animasi: lingkaran M1 saat "Dua" (titik progress kedua menyala); dashboard dibingkai M1 saat "pantau"; tabung jatuh satu-satu dari atas (bounce kecil) saat "antrean live", ritme makin cepat; batang warna berubah halus hijau→merah saat "numpuk"; "jebol" M5 + lingkaran merah M1; angka kecil di dashboard (jumlah antrean) terus bertambah (odometer).
Kamera: zoom-in (scale 1.0→1.35 pelan, fokus akhir ke tumpukan merah)
Transisi keluar: T4
Kotak: 2 | hitam
Baris: Pantau dashboard real-time | Antrean numpuk? Kelihatan duluan
Narasi: Dua. Pantau dashboard real-time. Tumpukan tabung kelihatan sebelum timer jebol.

## Beat 5 — alarm (20–26 dtk)
Visual: angka "3" dilingkari + headline. Lonceng (masuk dari T4), stopwatch dengan arc hampir penuh, lalu HP gambar tangan dengan notifikasi "⚠ Sampel hampir lewat batas TAT" (ID sampel dummy).
Animasi: lingkaran M1 saat "Tiga" (titik progress ketiga menyala); lonceng berayun keras M4+M5 saat "pengingat"; arc stopwatch terisi merah saat "lewat batas" (HP ikut bergetar); notifikasi slide-in dari atas HP + SFX ding + HP berputar kecil saat "notif"; headline M3.
Kamera: geser-kiri (translate 0→+120px sambil scale 1.1→1.2, berakhir di HP)
Transisi keluar: T5
Kotak: 3 | hitam
Baris: Pasang pengingat TAT | Mau lewat batas? Langsung notif
Narasi: Tiga. Pasang pengingat TAT. Peringatan otomatis. Sampel mau lewat batas? Langsung dapat notif.

## Beat 6 — closing_stamp (26–33 dtk)
Visual: judul besar + 3 centang merangkum 3 tip. Di bawah, stempel logo FASTLIS biru, lalu teks "Komen: AMAN / JEBOL" dengan panah ke bawah.
Animasi: judul M3 per kata; tiap item M2 dengan centang biru M1 + SFX ding, sinkron narasi; stempel FASTLIS jatuh dari atas dengan skala 1.6→1.0 + guncangan kamera 6px saat menghantam + riak lingkaran di kertas; panah "Komen" M1 lalu berdenyut terus (M4); confetti coretan biru 1 dtk setelah stempel.
Kamera: zoom-out (scale 1.25→1.0, lalu push-in kecil 1.0→1.04 saat stempel jatuh)
Judul: Bukan soal ngebut,<br>tapi tepat waktu.
Item: Catat tiap titik waktu
Item: Pantau antrean live
Item: Pasang alarm TAT
Stempel: FASTLIS
Narasi: Bukan soal ngebut, tapi tepat waktu. TAT lab kamu minggu ini, aman atau jebol? Komen!
