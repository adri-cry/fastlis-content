# Referensi Demo FastLIS (demo.fastlis.com)

Hasil eksplorasi read-only 2026-10-15. Aplikasi LIS web berbahasa Indonesia, peran SuperAdmin.
Sumber ide topik + istilah untuk pipeline konten FastLIS.

## Ringkasan aplikasi
FastLIS = Laboratory Information System: mengelola alur lab klinik dari pre-analitik
hingga pasca-analitik. Modul utama:
1. **Kendali Mutu (QC)**: aturan Westgard, grafik Levey-Jennings, hasil QC & worklist, setup lot kontrol.
2. **Manajemen Order & Sampel**: Daftar Kerja (worklist), Entri Order, Monitor Stasiun Kerja (unmatched runs analyzer).
3. **Pelaporan**: diagnosa bulanan, hasil panik bulanan, klinisi bulanan, kumulatif (tren antar-kunjungan), sumber, tes bulanan/tahunan, tipe sampel.
4. **Reagent & Stock**: daftar reagen, kategori, lokasi penyimpanan, manufacturer, stock masuk/keluar, supplier.
5. **Kamus Tes & Stasiun Kerja**: ~200 Definisi Tes & Profil, Identifikasi Analyzer.
6. **Tabel Parameter**: diagnosa, dokter DPJP, klinisi, grup tes, metode, satuan, nilai teks, prioritas, tipe pasien/sampel/tabung, status tagihan.
7. **Keamanan**: Jejak Audit Order, Log Aktivitas, Pengguna, Peran.
8. **Master Pasien**: Registrasi Pasien. **Parameter Sistem**: Barcode (CODE 128/39, EAN-13/8, UPC-A, ITF-14 + live preview), Menu Favorit, Profil Perusahaan.

Dashboard demo: Total Pasien 2, Total Faktur 3, Total Tes 48, Tes Tertunda 47, Tes Selesai 1,
donat "LIMA TES YANG PALING SERING DIAMBIL" (mis. HEMATOLOGI LENGKAP).

## Alur kerja (pre-analitik → analitik → pasca-analitik)
- **Pre-analitik**: Entri Order (PID, nama, No. Lab, sumber/pengirim, klinisi, status),
  Registrasi Pasien, barcode sampel, tipe sampel & tabung, prioritas order.
- **Analitik**: Daftar Kerja (kelola order, check-in sampel, entri hasil, otorisasi);
  Monitor Stasiun Kerja = unmatched runs (hasil analyzer tak cocok order);
  status berjenjang PENDING → COMPLETED → AUTHORIZED.
- **Pasca-analitik**: Laporan Hasil Panik (nilai kritis LL/HH), Laporan Kumulatif
  (matriks antar-kunjungan + grafik tren klinis, maks 10 kunjungan), cetak hasil.

## 10 ide topik konten
1. **Aturan Westgard**: cara lab memastikan QC valid sebelum rilis hasil pasien
   (status In-Control/Warning/Out-of-Control). Sumber: QC → Hasil QC & Validasi.
2. **Membaca grafik Levey-Jennings**: batas ±1s/±2s/±3s dan artinya.
   Legenda: In-Control hijau, Warning 1–2s oranye, Out of Control/Reject merah.
3. **Nilai panik (LL/HH)**: hasil kritis yang wajib segera dilaporkan ke dokter.
   Sumber: Pelaporan → Laporan Hasil Panik Bulanan.
4. **Flagging L/H**: arti hasil keluar rentang normal; audit nyata: flag "L"
   di-set otomatis SYSTEM saat hasil di bawah normal (contoh: Hemoglobin 88).
5. **Alur otorisasi hasil**: kenapa PENDING → COMPLETED → AUTHORIZED berlapis.
6. **Laporan kumulatif / delta check**: tren hasil antar-kunjungan pasien.
7. **Lot kontrol QC**: kenapa tiap lot reagen butuh mean & SD sendiri
   (Nomor Lot, Bahan Kontrol, Analyzer, Kedaluwarsa).
8. **Barcode sampel**: dari No. Lab hingga CODE 128 mencegah tertukar sampel.
9. **Tipe sampel & tabung**: EDTA (DT), SERUM (SRM), URINE (RN), FESES (FSS) —
   kenapa tidak bisa sembarangan.
10. **Monitor stasiun kerja / unmatched runs**: saat hasil analyzer tak cocok order
    (praktik interfacing LIS-analyzer).

## Istilah lab (singkat)
- **Aturan Westgard**: aturan statistik validitas QC.
- **Grafik Levey-Jennings**: grafik QC, garis mean ±1s/±2s/±3s.
- **Lot kontrol**: batch bahan kontrol bernilai target.
- **Nilai panik (LL/HH)**: hasil kritis wajib lapor segera.
- **Flag L/H**: hasil di bawah/di atas rentang normal (otomatis oleh sistem).
- **Otorisasi (AUTHORIZED)**: persetujuan akhir sebelum rilis.
- **Laporan kumulatif**: banding antar-kunjungan + tren (delta check).
- **Unmatched Runs**: hasil analyzer tanpa order cocok.
- **Profil tes**: paket berisi beberapa parameter (mis. Hitung Jenis Leukosit).
- **Tipe data tes**: NUMERIC, TEXTVALUE, FREETEXT, NOVALUE.
- **Nilai teks**: hasil kualitatif baku (REACTIVE/NON REACTIVE, POSITIF/NEGATIF, titer).
- **PID / No. Lab / SID**: identitas pasien, nomor order, identitas sampel.
- **DPJP**: Dokter Penanggung Jawab Pelayanan.

## Catatan visual (referensi desain)
- Kartu statistik dashboard berwarna berani + ikon (biru, navy, oranye).
- Donat "tes paling sering diambil" + legenda, gaya analitik bersih.
- Menu Favorit: kartu ilustrasi flat line-art medis.
- Badge QC: hijau/oranye/merah konsisten.
- Tabel master: kolom Kode/Nama/Status + aksi titik-tiga.
- Live preview barcode di pengaturan.
- Tema: sidebar gelap/terang, aksen biru (~#2563eb), sans-serif modern, badge status warna.

## Batasan demo
- Baris tes hanya bisa "Ubah"/"Hapus" (tidak disentuh); detail rentang normal per tes tak terlihat.
- Banyak master kosong/minimal (analyzer, metode tes, prioritas cuma RUTIN, dst).
- Daftar Kerja & Entri Order kosong untuk 15/10/2026; contoh order via Jejak Audit.
