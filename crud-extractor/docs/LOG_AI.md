# Log Penggunaan AI

Catat setiap penggunaan AI atau coding agent yang memengaruhi kode atau laporan.

| No | Siapa | Prompt / tugas (ringkas) | Hasil: diterima, diubah, atau ditolak | Alasan | Cara verifikasi |
| --- | --- | --- | --- | --- | --- |
| 1 | Hilman | Meminta AI membaca `resolver.py` dan `analyzer.py` dan mencari bug serta menyelesaikan T2 | Diterima: T2 dan tiga bug resolver (urutan lookup, `_pop` pada DELETE) dan satu bug analyzer (subquery UPDATE jadi R) | Setiap perbaikan cocok dengan SPESIFIKASI 4.3, 4.5, dan 5 | Menjalankan pytest sebelum dan sesudah, menghitung `audit.sql` secara manual |
| 2 | Hilman | Meminta AI membuat test regresi dan kasus tepi untuk resolver dan analyzer | Diubah: test dipindah ke `tests/test_tambahan.py`, helper ditambahkan, jumlah kasus tepi dibatasi lima untuk seluruh kelompok | Soal mengganti folder `tests/` saat penilaian | Test dijalankan terhadap kode asli dosen: gagal sebelum perbaikan, lulus sesudahnya |
| 3 | Hilman | Meminta AI membuat ground truth pemeliharaan.sql | Diubah: draf AI ditempel dengan spasi di depan baris sehingga evaluate.py gagal membaca nama file; spasi dihapus | Soal meminta label manual berdasarkan spesifikasi, bukan salinan keluaran tool | evaluate.py kembali berjalan dan parser 1.00 / 1.00 |
| 4 | Hilman | Meminta AI membuat draf KARTU_DESAIN.md dan LAPORAN_AKHIR.md | Diubah: draf dibaca, disesuaikan, dan nama anggota diisi | Bagian laporan harus bisa dijelaskan sendiri saat demo | Isi dicocokkan dengan kode resolver.py dan analyzer.py, dan dengan keluaran evaluate.py yang dijalankan sendiri |
| 5 | Hilman | Meminta AI memeriksa seluruh ZIP proyek sebelum dikumpulkan | Diterima: AI menemukan spasi di depan baris ground_truth.csv, NameError pada lima test di test_tambahan.py, dan teks LAPORAN_BUG.md yang tertukar semuanya diperbaiki | Soal menyebut semua test terlihat lulus belum berarti pekerjaan selesai | Menjalankan ulang pytest (50 passed) dan evaluate.py setelah tiap perbaikan |


**Refleksi (3-5 kalimat).** Di bagian mana AI paling membantu? Di mana AI keliru atau
menyesatkan, dan bagaimana kalian mengetahuinya?
