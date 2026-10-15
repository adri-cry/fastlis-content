# Referensi gaya video: @stocks.space.id (Switching & VLAN)

Sumber: video referensi dari Adri, 2026-10-15. Topik jaringan komputer, dipakai
murni untuk GAYA, bukan materi. File: workspace/user/media_library/video/bc/bcab3021fdbf84d187f419318b216b66dd61a3826985c5d76ba8d0fea0b320df.mp4

## Sistem desain yang bisa ditiru

1. **Diagram sebagai pencerita utama.** Bukan foto, melainkan diagram vektor yang
   dibangun bertahap mengikuti narasi: ikon line-art (laptop, printer, server,
   switch), tabel data, dan paket animasi (titik bergerak sepanjang jalur).
2. **Kode warna per kategori, konsisten di semua elemen.** Contoh: KEUANGAN=biru,
   HR=ungu, TAMU=oranye. Warna yang sama dipakai di ikon, label, baris tabel,
   dan badge. FastLIS bisa pakai pola ini mis. PRE-ANALITIK / ANALITIK / PASCA-ANALITIK.
3. **Progressive reveal sinkron narasi.** Elemen muncul satu per satu sesuai
   kalimat yang diucapkan: dulu perangkat, lalu switch, lalu MAC address, lalu
   baris tabel MAC satu per satu, lalu animasi paket "unicast → Gi0/8".
   Tiap klaim narasi = satu perubahan visual.
4. **Chapter pill + judul besar.** Pill mono kecil (BAGIAN 1, MASALAH BARU,
   DI LAPANGAN, RANGKUMAN) + judul besar dua warna (putih + satu aksen).
5. **Tabel sebagai elemen visual.** Tabel data nyata (MAC address table) di-render
   sebagai tabel bergaya, terisi baris per baris. Cocok untuk konten lab:
   tabel rentang normal, aturan Westgard, tipe tabung.
6. **Kartu perbandingan.** Dua kartu berdampingan (Layer 2 vs Layer 3) dengan
   daftar centang/silang. Cocok untuk mitos-vs-fakta versi diagram.
7. **Kartu rangkuman bernomor di penutup.** 01 / 02 / 03 dengan satu kalimat
   kunci tiap poin.
8. **Chrome konsisten.** Progress bar tipis di atas, deret titik timeline di
   bawah, watermark pojok kanan atas, background gelap bertekstur garis
   diagonal halus + glow lembut di pojok.
9. **Hook masalah dulu, teori belakangan.** Dibuka dengan pertanyaan konkret
   ("kenapa komputer tamu nggak bisa ngintip data keuangan?"), baru masuk
   ke definisi. Judul cover = pertanyaan, sesuai aturan template FastLIS.
10. **Kalimat pendek per scene, satu ide per layar.** Tidak ada paragraf
    panjang; tiap scene 1-2 kalimat.

## Topik FastLIS yang cocok gaya ini
- Alur otorisasi PENDING → COMPLETED → AUTHORIZED (diagram alur + paket animasi)
- Aturan Westgard / grafik Levey-Jennings (tabel + grafik terisi bertahap)
- Tipe sampel & tabung (ikon berkode warna per tipe)
- Alur barcode sampel (jalur animasi dari registrasi ke analyzer)
- Nilai kritis LL/HH (diagram alur pelaporan + read-back)
- Delta check / laporan kumulatif (grafik tren antar-kunjungan)

## Catatan implementasi
- Semua elemen = SVG/CSS murni, tanpa foto. Bisa di-render dengan pipeline
  hyperframes yang sama; animasi via CSS keyframes + GSAP lokal (sudah di-vendor).
- Berbeda dari template v2 sinematik (foto polaroid + karaoke). Ini varian
  kedua: "diagram explainer". Perlu template HTML terpisah bila diputuskan.
- Estimasi: satu template diagram generik (chapter pill, ikon line-art,
  tabel animasi, kartu banding, kartu rangkuman) lalu diisi per topik.
