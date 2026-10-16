# Peta Kata Aman TTS (avocado_v2:MAI_01)

Referensi untuk naskah voice-over reels whiteboard. Dibuat 2026-10-16 dari
uji round-trip sistematis: sintesis via `/opt/hatch/bin/tts` (voice
`avocado_v2:MAI_01`, language `id`) → transkripsi balik via faster-whisper
(`~/workspace/venvs/whisper`, model small) → cek per kata.

## Temuan utama: TTS ini NON-DETERMINISTIK

Sintesis yang sama bisa menghasilkan pengucapan berbeda di tiap pemanggilan.
Kata yang aman di satu tes bisa salah di render berikutnya (dan sebaliknya).
Satu-satunya pengaman yang bisa diandalkan: **QA round-trip TTS→whisper di
konteks naskah final, setiap kali sebelum render** (sudah dipraktikkan di
pipeline whiteboard), plus **penjaga durasi otomatis** (lihat bawah).

## Kata pemicu yang TERKONFIRMASI + pengganti terverifikasi

| Kata pemicu | Masalah | Pengganti terverifikasi aman |
|---|---|---|
| simpel | Diucap "simple" (Inggris), reproduksibel | mudah (terverifikasi 2026-10-16) |
| ekstrem | Kadang "ekstrim", kadang "Extreme" (Inggris) | parah (terverifikasi 2026-10-16) |
| selisih | Kadang "isilih" (sisipan "i", terverifikasi di konteks prototipe) | perbedaan, beda, rentang, jaraknya (semua terverifikasi 2026-10-16) |
| bedanya | Kadang "ibedanya" (terverifikasi di konteks prototipe) | "Jauh banget kan?" (terverifikasi 2026-10-16) |
| ngeri | Kadang "inggri" (terverifikasi di konteks prototipe) | seram (terverifikasi 2026-10-16) |

Catatan: sisipan "i" (selisih/bedanya/ngeri) TIDAK terreproduksi dalam 6
sintesis uji umum (awal maupun tengah kalimat), tapi nyata terjadi di
konteks prototipe delta check dan terdengar oleh Adri. Perlakukan sebagai
bug intermiten: hindari kata pemicunya, jangan mengandalkan "tadi aman".

## Insiden halusinasi TTS (1 dari ~20 sintesis, 2026-10-16)

Input: "Bedanya ekstrem. Hasilnya jauh dari kemarin."
Hasil: TTS mengucap "Bedanya Extreme" lalu NGARANG intro pembawa berita
("Halo selamat datang... saya Manisa Trahir..."), total 16,5 detik untuk
kalimat yang seharusnya ~4 detik. Sintesis ulang kalimat yang sama: normal
(4,1 detik, "Bedanya ekstrim").

→ **Penjaga durasi otomatis**: tolak/flag VO bila durasinya menyimpang
>30% dari estimasi (karakter/850×60 detik). Menangkap halusinasi tanpa
didengar manual.

## Perlu dicek telinga manusia (whisper memberi sinyal, belum pasti bug)

- `pending` → di kalimat Indonesia ditranskrip "penting"; di daftar
  "pending, completed, authorized" ditranskrip benar. Mungkin artefak
  language-model whisper, tapi pastikan terdengar Inggris jelas.
- `reagen` → ditranskrip "Reagan" (vokal Inggris?).
- `preanalitik` → ditranskrip "reanalytik" (huruf 'p' awal lemah?).

## Bukan bug (artefak ejaan whisper, fonetiknya benar)

analis→"Analys", hemolisis→"Hemolysis", menelepon→"menelpon". Aman dipakai.

## Kata domain lab yang lolos uji (aman di konteks uji)

hasil, menunjukkan, nilai, kritis, segera, dilaporkan, delta,
membandingkan, kunjungan, sebelumnya, validasi, kalium, naik, menjadi,
melebihi, batas, normal, memverifikasi, sampel, dirilis, dikirim, pasien,
otorisasi, penanggung, memastikan, diagnosis, terapi, tepat, jejak, audit,
mencatat, diubah, lipemia, pemeriksaan, akurat, kalibrasi, kontrol,
kualitas, dilakukan, pengambilan, persiapan, benar, pernah, walau,
urutannya, completed, authorized, ikuti, prosedur, standar, berlaku, angka,
salah, mengubah, interpretasi, klinis, tersebut.

## Aturan penulisan naskah whiteboard

1. Jangan pakai kata di kolom "Kata pemicu"; pakai penggantinya.
2. Setiap naskah final WAJIB lewat QA round-trip (sintesis → whisper →
   cek) sebelum render. Satu kata aman kemarin belum tentu aman hari ini.
3. Terapkan penjaga durasi otomatis (>30% dari estimasi = flag).
4. Loanword Inggris yang umum di lab (pending, completed, authorized,
   delta check) sejauh ini aman, tapi masukkan dalam cek QA juga.
