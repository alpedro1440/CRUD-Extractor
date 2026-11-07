# Laporan Bug

Salin blok di bawah untuk setiap bug. Bagian **Akar masalah** wajib ditulis dengan kata-kata
sendiri dan memakai konsep dari *Crafting Interpreters* (sebutkan bab). Bagian ini diuji lisan.

> **Status draft (Anggota 1: lexer dan parser).** Gejala, reproduksi, perbaikan, dan test sudah
> diisi dari hasil menjalankan kode asli. Bagian **Akar masalah** masih kosong dan berisi
> *petunjuk konsep* saja. Tulis penjelasannya sendiri, lalu hapus petunjuknya. Ganti `[nama]`
> dan konfirmasi tiap baris bertanda `[KONFIRMASI]`. Bug resolver dan analyzer (Anggota 2)
> ditambahkan di bawah Bug 6.

---

## Bug 1: Keyword hanya dikenali jika ditulis huruf besar

**Ditemukan oleh:** Alpedro · **Diperbaiki oleh:** nama

**Gejala.** `select id from t;` menghasilkan token `IDENT` untuk semua kata, lalu parser
melapor `Baris 1, kolom 1: diharapkan awal statement (...), ditemukan 'select'`. Akibatnya
seluruh `pemeliharaan.sql` (yang ditulis huruf kecil) tidak bisa diproses. Menurut SPESIFIKASI
2.2, keyword tidak peka huruf besar/kecil dan nilai tokennya dinormalisasi ke huruf besar.

**Reproduksi minimal.**

```sql
select id from t;
```

**Akar masalah.**
Masalah terjadi karena lexer membandingkan kata yang ditemukan dengan daftar keywords secara langsung, tanpa mengubahnya ke huruf yang sama terlebih dahulu. Akibatnya, kata `select` yang ditulis menggunakan huruf kecil tidak dikenali sebagai keyword `SELECT`, melainkan dianggap sebagai token `IDENT`. Hal ini menyebabkan parser menerima token 'IDENT' padahal parser mengharapkan sebuah statement diawali dengan keyword `SELECT`, sehingga muncul error pada baris 1 kolom 1 dan file `pemeliharaan.sql` gagal diproses. Perbaikan dilakukan pada bagian lexer, bukan parser, karena lexer bertugas mengidentifikasi dan memberikan jenis token, seperti `KEYWORD` atau `IDENT`. Caranya adalah dengan mengubah kata yang ditemukan menjadi huruf besar menggunakan fungsi `upper()` sebelum dicocokkan dengan daftar keywords. Dengan begitu, keyword tetap dikenali meskipun ditulis menggunakan huruf kapital maupun huruf kecil. Perbaikan ini sesuai dengan pembahasan Reserved Words pada Bab 4 buku Crafting Interpreters dan ketentuan pada `SPESIFIKASI.md` bagian 2.2.

**Perbaikan.** `crud/lexer.py`, `_word`: teks dibandingkan ke `KEYWORDS` dalam bentuk
`text.upper()`; token keyword menyimpan bentuk huruf besar, sedangkan `IDENT` menyimpan teks
asli (parser yang menurunkannya ke huruf kecil). Alternatif yang ditolak: mengubah seluruh
sumber SQL ke huruf besar sebelum lexing, karena itu merusak isi string (`'gold'`) dan nama
identifier.

**Test regresi.** `test_regresi_keyword_tidak_peka_huruf_besar_kecil`. Penjaga tambahan:
`test_tepi_identifier_berawalan_keyword` (`selection` tetap `IDENT`).

**Peran AI dan verifikasi.** Draf sebelumnya mencatat bantuan Claude untuk menemukan ketidaksesuaian ini. Perbaikannya diverifikasi dengan test token untuk variasi huruf besar/kecil dan dengan test yang memastikan kata seperti `selection` tetap menjadi `IDENT`. Pastikan nama AI pada catatan awal memang sesuai dengan alat yang benar-benar digunakan kelompok.

---

## Bug 2: `<>` terpecah menjadi dua token

**Ditemukan oleh:** Alpedro · **Diperbaiki oleh:** Alpedro

**Gejala.** `a <> 1` menghasilkan `OP '<'`, `OP '>'`, `NUMBER '1'`, dan parser melapor
`diharapkan ekspresi, ditemukan '>'`. Pada data contoh, `laporan_penjualan.sql` gagal di baris 6
kolom 41 (`o.catatan <> 'FROM rahasia'`), sehingga statement SELECT pertamanya tidak dihitung (dan, karena Bug 6, seluruh statement
sesudahnya ikut hilang).
SPESIFIKASI 2.5: `<>` adalah satu token.

**Reproduksi minimal.**

```sql
SELECT id FROM t WHERE a <> 1;
```

**Akar masalah.** Pada kode awal, cabang pemindaian karakter `<` hanya memeriksa apakah karakter sesudahnya adalah `=`. Jika bukan, Lexer langsung menghasilkan token `<`. Karakter `>` yang mengikutinya kemudian diproses lagi sebagai token terpisah. Cara tersebut tidak menerapkan prinsip *maximal munch* secara lengkap, yaitu memilih rangkaian operator terpanjang yang cocok. Dalam *Crafting Interpreters* Bab 4, pemindaian token perlu mempertimbangkan karakter berikutnya sebelum memutuskan batas token. Karena `<>` merupakan operator dua karakter yang sah menurut spesifikasi, Lexer harus memeriksa `=` dan `>` sebelum mengeluarkan `<` tunggal.

**Perbaikan.** `crud/lexer.py`, `_scan_token`: setelah `<`, coba `=` (jadi `<=`), lalu `>`
(jadi `<>`), baru jatuh ke `<`. Alternatif yang ditolak: menggabungkan `<` dan `>` di parser
bila berdampingan, karena itu menyembunyikan kesalahan lexer dan membuat `a < > 1` ikut diterima.

**Test regresi.** `test_regresi_operator_tidak_sama_dengan_satu_token`.

**Peran AI dan verifikasi.** AI membantu membandingkan aturan operator pada spesifikasi dengan cabang pemindaian Lexer. Kelompok memverifikasi jenis dan nilai token melalui test regresi serta menjalankan seluruh pytest.

---

## Bug 3: `''` di dalam string mengakhiri string

**Ditemukan oleh:** Alpedro · **Diperbaiki oleh:** Alpedro

**Gejala.** `'O''Brien'` menghasilkan dua token `STRING` (`O` dan `Brien`), dan parser melapor
`diharapkan ';' di akhir statement, ditemukan 'Brien'`. Seharusnya satu `STRING` bernilai
`O'Brien` (SPESIFIKASI 2.4). Data contoh `pemeliharaan.sql` memuat `'O''Brien'` dan `'O''Neil'`.

**Reproduksi minimal.**

```sql
SELECT id FROM t WHERE n = 'O''Brien';
```

**Akar masalah.** Pemindaian string pada kode awal menganggap setiap kutip tunggal yang ditemukan sebagai tanda akhir string. Lexer tidak melihat karakter berikutnya untuk membedakan kutip penutup dengan dua kutip berurutan yang bermakna satu apostrof di dalam nilai string. Akibatnya, nilai string terpotong terlalu awal. Perbaikan membutuhkan *lookahead*: ketika menemukan kutip tunggal, Lexer memeriksa karakter sesudahnya. Jika karakter berikutnya juga kutip tunggal, keduanya dikonsumsi dan satu karakter kutip ditambahkan ke nilai string; jika tidak, string dinyatakan selesai. Ini termasuk proses pemindaian literal string pada *Crafting Interpreters* Bab 4.

**Perbaikan.** `crud/lexer.py`, `_string`: saat bertemu `'`, bila karakter berikutnya juga `'`
maka keduanya dikonsumsi dan satu `'` ditambahkan ke nilai; selain itu string berakhir.

**Test regresi.** `test_regresi_kutip_ganda_dalam_string_satu_token`; kasus tepi
`test_tepi_penanda_komentar_di_dalam_string`.

**Peran AI dan verifikasi.** AI membantu menjelaskan penggunaan *lookahead* dan menyarankan test. Test diperiksa terhadap aturan string pada spesifikasi dan dijalankan bersama test Lexer.

---

## Bug 4: `AND` dan `OR` memiliki presedensi yang sama

**Ditemukan oleh:** Alpedro · **Diperbaiki oleh:** Alpedro

**Gejala.** `a = 1 OR b = 2 AND c = 3` diparse sebagai `((a = 1 OR b = 2) AND c = 3)`.
Menurut SPESIFIKASI 3.1 seharusnya `a = 1 OR (b = 2 AND c = 3)`. Tidak terlihat di test
yang ada karena hanya menguji satu `AND`. Bug ini tidak mengubah CRUD matrix (AND/OR tidak
memengaruhi tabel yang disentuh), tetapi tetap bug karena melanggar spesifikasi. `audit.sql`
baris 4-6 memuat pola ini.

**Reproduksi minimal.**

```sql
SELECT id FROM t WHERE a = 1 OR b = 2 AND c = 3;
```

**Akar masalah.** Fungsi `_logical()` pada Parser awal menangani `AND` dan `OR` dalam satu perulangan yang sama. Karena kedua operator diproses pada tingkat fungsi yang sama dan digabung secara asosiatif kiri, Parser tidak membedakan tingkat presedensinya. Padahal grammar menentukan `or_expr` sebagai tingkat lebih rendah yang berisi `and_expr`, sedangkan `and_expr` berisi `not_expr`. Dalam *Crafting Interpreters* Bab 5 dan Bab 6, struktur grammar dan fungsi recursive descent perlu mencerminkan tingkat presedensi operator. Jika beberapa tingkat digabung ke satu fungsi, bentuk AST dapat berbeda dari aturan grammar.

**Perbaikan.** `crud/parser.py`: `_logical` dipecah menjadi `_or` (memanggil `_and`) dan `_and`
(memanggil `_not`); `_expr` memanggil `_or`. Alternatif yang ditolak: tabel presedensi
numerik (precedence climbing). Lebih ringkas, tetapi grammar di SPESIFIKASI sudah berbentuk satu
aturan per tingkat, sehingga bentuk saat ini lebih mudah dicocokkan satu per satu.

**Test regresi.** `test_regresi_presedensi_and_lebih_tinggi_dari_or`,
`test_regresi_not_lebih_tinggi_dari_and`; kasus tepi `test_tepi_between_diikuti_and_logika`.

**Peran AI dan verifikasi.** AI membantu menelusuri perbedaan grammar dan implementasi recursive descent. Verifikasi dilakukan dengan membandingkan bentuk AST yang dihasilkan untuk kombinasi `AND`, `OR`, dan `NOT`.
---

## Bug 5: `LEFT OUTER JOIN` ditolak

**Ditemukan oleh:** Alpedro · **Diperbaiki oleh:** Alpedro

**Gejala.** `LEFT OUTER JOIN` menghasilkan `Baris 1, kolom 25: diharapkan JOIN, ditemukan
'OUTER'`. Grammar: `"LEFT" [ "OUTER" ] "JOIN"`. Data contoh `pemeliharaan.sql` memakainya.

**Reproduksi minimal.**

```sql
SELECT a.id FROM a LEFT OUTER JOIN b ON b.a_id = a.id;
```

**Akar masalah.** Fungsi `_join()` pada kode awal mengenali keyword `LEFT`, tetapi setelah itu langsung memanggil pemeriksaan wajib untuk `JOIN`. Fungsi tersebut tidak memeriksa kemungkinan hadirnya `OUTER`. Dengan demikian, bahasa yang diterima implementasi Parser lebih sempit daripada bahasa yang ditentukan grammar. Bab 6 *Crafting Interpreters* membahas parser recursive descent yang menerjemahkan aturan grammar ke fungsi; bagian opsional pada grammar harus direpresentasikan sebagai pemeriksaan opsional, bukan token wajib yang dilewati.

**Perbaikan.** `crud/parser.py`, `_join`: setelah `LEFT`, `_match_kw("OUTER")` bersifat opsional.

**Test regresi.** `test_regresi_left_outer_join`.

**Peran AI dan verifikasi.** AI membantu mencocokkan aturan `LEFT [OUTER] JOIN` dengan urutan pemeriksaan token. Kelompok memverifikasi bahwa query `LEFT OUTER JOIN` berhasil diparse dan jenis join tetap `LEFT`.

---

## Bug 6: Error recovery membuang seluruh sisa file

**Ditemukan oleh:** Alpedro · **Diperbaiki oleh:** Alpedro

**Gejala.** Satu statement yang rusak membuat semua statement sesudahnya hilang. Pada
`SELECT id nama, FROM a; SELECT id FROM b; DELETE FROM c;` kode lama menghasilkan 1 error
dan **0** statement; seharusnya 1 error dan 2 statement valid (SPESIFIKASI 6). Pada
`campuran_error.sql`, `UPDATE produk` dan `DELETE FROM keranjang` tidak terhitung.

**Reproduksi minimal.**

```sql
SELECT id nama, FROM a;
SELECT id FROM b;
```

**Akar masalah.** Fungsi `_synchronize()` pada kode awal terus memanggil `_advance()` selama belum EOF tanpa mencari titik sinkronisasi. Akibatnya, satu kesalahan sintaks dapat menghilangkan semua statement yang tersisa dalam file. Dalam konsep *panic mode recovery* dan *synchronization* pada *Crafting Interpreters* Bab 6, Parser harus mencari token aman untuk melanjutkan proses. Untuk proyek ini, token sinkronisasi yang ditentukan spesifikasi adalah `;`, sehingga recovery harus berhenti setelah mengonsumsi titik koma tersebut.

**Perbaikan.** `crud/parser.py`, `_synchronize`: membuang token sampai dan **termasuk** `;`
berikutnya. Bila token error adalah `;` itu sendiri (misalnya `SELECT a FROM ;`), token itu
ikut dibuang dan parsing berlanjut ke statement berikutnya.
Alternatif yang ditolak: berhenti di keyword `SELECT/INSERT/UPDATE/DELETE` berikutnya, karena
keyword itu juga muncul di dalam subquery sehingga recovery bisa berhenti di tengah statement
rusak dan menghasilkan error ganda.

**Test regresi.** `test_regresi_recovery_berhenti_di_titik_koma`; kasus tepi
`test_tepi_error_tepat_di_titik_koma`.

**Peran AI dan verifikasi.** AI membantu mengidentifikasi bahwa kode awal tidak memiliki token sinkronisasi. Verifikasi dilakukan dengan file berisi statement rusak diikuti statement valid dan memeriksa jumlah error serta statement yang berhasil disimpan.

---

## Bukan bug, tetapi TODO yang diselesaikan

- **T1 `INSERT ... SELECT`** (`parser.py`, `_insert`): memanggil `_select()` dan mengembalikan
  `Insert(table, columns, [], query)`. Test: `test_regresi_insert_select_T1`.
- **T3 komentar blok** (`lexer.py`, `_block_comment`): `*` pembuka dikonsumsi dulu agar `/*/`
  tidak dianggap tertutup; berhenti di `*/` pertama (tidak bersarang); komentar yang tidak
  ditutup menjadi `LexError` di posisi `/*`. Test: `test_regresi_komentar_blok_T3`,
  `test_regresi_komentar_blok_tidak_ditutup_lexerror`, `test_tepi_bentuk_komentar_blok_khusus`.

<!-- Bug dari Anggota 2 (resolver/analyzer) ditambahkan di bawah ini. -->
