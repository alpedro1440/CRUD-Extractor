# Laporan Akhir

## 1. Hasil evaluasi
```text
Dievaluasi: audit.sql, campuran_error.sql, laporan_penjualan.sql, pemeliharaan.sql (27 triple)

Metode   Precision  Recall     F1
parser        1.00    1.00   1.00
regex         0.65    0.81   0.72

[regex]
  salah ditemukan (FP): ('audit.sql', 16, 'sesi', 'R')
  salah ditemukan (FP): ('campuran_error.sql', 4, 'pesanan', 'R')
  salah ditemukan (FP): ('campuran_error.sql', 8, 'keranjang', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'pelanggan', 'D')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'pelanggan', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'pesanan', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'rahasia', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 15, 'pesanan', 'R')
  salah ditemukan (FP): ('pemeliharaan.sql', 2, 'crm.alamat', 'R')
  salah ditemukan (FP): ('pemeliharaan.sql', 2, 'crm.pelanggan', 'R')
  salah ditemukan (FP): ('pemeliharaan.sql', 2, 'pelanggan_lama', 'U')
  salah ditemukan (FP): ('pemeliharaan.sql', 15, 'crm.alamat', 'R')
  terlewat (FN):       ('audit.sql', 2, 'pesanan', 'R')
  terlewat (FN):       ('laporan_penjualan.sql', 3, 'pelanggan', 'R')
  terlewat (FN):       ('laporan_penjualan.sql', 3, 'pesanan', 'R')
  terlewat (FN):       ('pemeliharaan.sql', 3, 'crm.alamat', 'R')
  terlewat (FN):       ('pemeliharaan.sql', 3, 'crm.pelanggan', 'R')
```

Parser mencapai precision dan recall 1.00 pada seluruh ground truth, sedangkan regex hanya
mencapai precision 0.65 dan recall 0.81. Semua kesalahan regex (daftar FP dan FN di atas)
bersumber dari tiga hal: komentar dan string dianggap SQL, `DELETE FROM x` dihitung juga sebagai
baca, dan nomor baris statement salah karena pemisahan hanya berdasarkan `;`.

## 2. Tiga kasus di mana regex salah

1. **Komentar dianggap perintah.** `laporan_penjualan.sql` baris 2:
   `-- DELETE FROM pelanggan`. Regex melaporkan `pelanggan: D` (dan juga R) yang tidak pernah
   terjadi. Hal yang sama pada `pemeliharaan.sql`: komentar blok memuat `UPDATE pelanggan_lama`
   dan regex melaporkan `pelanggan_lama: U`. Parser benar karena **lexer** membuang komentar
   sebelum parsing dan tidak menghasilkan token, jadi teks di dalamnya tidak pernah sampai
   ke parser.
2. **Isi string dianggap SQL.** `o.catatan <> 'FROM rahasia'` membuat regex mengeluarkan tabel
   palsu `rahasia: R`. Lexer mengubah seluruh literal (termasuk `'O''Brien'`, dua kutip menjadi
   satu karakter) menjadi satu token `STRING`, sehingga kata `FROM` di dalamnya hanyalah data.
3. **`DELETE FROM x` dihitung dua kali.** Untuk `DELETE FROM sesi s WHERE ...` regex memberi
   `sesi: D` *dan* `sesi: R` karena pola `FROM <nama>` juga cocok. Pada
   `DELETE FROM crm.alamat WHERE ... (SELECT ... FROM crm.pelanggan)` regex memberi
   `crm.alamat: D` dan `crm.alamat: R`. Parser tahu **peran tata bahasa** nama tabel itu:
   di `delete_stmt` ia adalah target (D), di `table_ref` dalam subquery ia sumber (R). Regex
   hanya melihat urutan kata, tanpa struktur.

## 3. Batas pendekatan kami

1. **Kolom ambigu tanpa skema.** `SELECT nama FROM pelanggan p JOIN pesanan o ON ...` memberi
   warning "ambigu tanpa skema" dan `resolved = None`. Matriks CRUD tingkat tabel tetap benar
   (keduanya R), tetapi penggunaan kolom (`--kolom`) kehilangan baris untuk `nama`. Yang
   dibutuhkan: katalog skema (tabel dan kolomnya) untuk memutuskan kolom itu milik tabel mana.
2. **Nama tabel dengan dan tanpa skema dianggap berbeda.** `SELECT * FROM pelanggan` dan
   `SELECT * FROM crm.pelanggan` menghasilkan dua tabel terpisah (`pelanggan` dan
   `crm.pelanggan`), padahal bisa saja tabel yang sama (bergantung `search_path` atau skema
   default). Akibatnya matriks terpecah dua baris. Yang dibutuhkan: skema default dan
   `search_path` dari database.
3. **Hal di luar tata bahasa dan efek tak terlihat dari teks query.** Di luar lingkup
   (SPESIFIKASI 9): CTE (`WITH`), `UNION`, `MERGE`, view, trigger, stored procedure, dan SQL
   dinamis. Akibatnya: `SELECT ... FROM v_laporan` hanya mencatat `v_laporan` (R), bukan
   tabel dasar view-nya; `DELETE` pada tabel yang punya trigger tidak mencatat tabel yang
   disentuh trigger; `WITH x AS (...)` gagal di-parse sehingga statement tidak dihitung.
   Yang dibutuhkan: definisi view, trigger, dan prosedur dari katalog database.
4. **`INSERT` tanpa daftar kolom dan `SELECT *`.** Kolom yang terlibat tidak bisa diketahui
   tanpa skema, jadi `column_usage` kosong untuk kasus ini.

## 4. Pembagian kerja

- **Anggota 1 Alpedro:** Lexer (T3 komentar blok), Parser (T1 `INSERT ... SELECT`), error
  recovery, `LAPORAN_BUG.md`, `LOG_AI.md`, `audit.sql` pada ground truth.
- **Anggota 2 Hilman:** Resolver (T2 kolom tanpa qualifier, perbaikan urutan lookup dan
  `_pop` pada `DELETE`), Analyzer (perbaikan operasi subquery di `UPDATE`), test Resolver dan
  Analyzer, `KARTU_DESAIN.md`, draft `LAPORAN_AKHIR.md`, `pemeliharaan.sql` pada ground truth.
- **Bersama:** menjalankan seluruh pytest, evaluasi parser vs regex, review silang laporan.
- **Memastikan keduanya paham seluruh kode:** setiap anggota menjelaskan bagiannya ke partner