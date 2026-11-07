# Log Penggunaan AI

Catat setiap penggunaan AI atau coding agent yang memengaruhi kode atau laporan.

| No | Siapa | Prompt / tugas (ringkas) | Hasil: diterima, diubah, atau ditolak | Alasan | Cara verifikasi |
| --- | --- | --- | --- | --- | --- |
| 1 | Hilman | Meminta AI membaca `resolver.py` dan `analyzer.py` dan mencari bug serta menyelesaikan T2 | Diterima: T2 dan tiga bug resolver (urutan lookup, `_pop` pada DELETE) dan satu bug analyzer (subquery UPDATE jadi R) | Setiap perbaikan cocok dengan SPESIFIKASI 4.3, 4.5, dan 5 | Menjalankan pytest sebelum dan sesudah, menghitung `audit.sql` secara manual |
| 2 | Hilman | Meminta AI membuat test regresi dan kasus tepi untuk resolver dan analyzer | Diubah: test dipindah ke `tests/test_tambahan.py`, helper ditambahkan, jumlah kasus tepi dibatasi lima untuk seluruh kelompok | Soal mengganti folder `tests/` saat penilaian | Test dijalankan terhadap kode asli dosen: gagal sebelum perbaikan, lulus sesudahnya |
| 3 | Hilman | Meminta AI membuat draft `KARTU_DESAIN.md` dan `LAPORAN_AKHIR.md` | Diubah: [isi sesuai kenyataan] | Akar masalah harus kata-kata sendiri | [isi: misalnya dibaca dan dicocokkan dengan kode] |
| 4 | Hilman | Meminta AI membuat ground truth `pemeliharaan.sql` | Diterima setelah dicek manual | Soal meminta label manual, bukan salinan keluaran tool | Menghitung ulang tiap statement dengan aturan SPESIFIKASI 5 |


**Refleksi (3-5 kalimat).** Di bagian mana AI paling membantu? Di mana AI keliru atau
menyesatkan, dan bagaimana kalian mengetahuinya?
