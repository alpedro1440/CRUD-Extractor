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

**Ditemukan oleh:** [nama] · **Diperbaiki oleh:** [nama]

**Gejala.** `select id from t;` menghasilkan token `IDENT` untuk semua kata, lalu parser
melapor `Baris 1, kolom 1: diharapkan awal statement (...), ditemukan 'select'`. Akibatnya
seluruh `pemeliharaan.sql` (yang ditulis huruf kecil) tidak bisa diproses. Menurut SPESIFIKASI
2.2, keyword tidak peka huruf besar/kecil dan nilai tokennya dinormalisasi ke huruf besar.

**Reproduksi minimal.**

```sql
select id from t;
```

**Akar masalah.** *[Tulis sendiri.]*
Petunjuk konsep: pembedaan keyword dan identifier di lexer (Bab 4, bagian reserved words and
identifiers). Pikirkan: bagian mana dari kode yang membandingkan teks dengan `KEYWORDS`, dan
teks apa yang dibandingkan?

**Perbaikan.** `crud/lexer.py`, `_word`: teks dibandingkan ke `KEYWORDS` dalam bentuk
`text.upper()`; token keyword menyimpan bentuk huruf besar, sedangkan `IDENT` menyimpan teks
asli (parser yang menurunkannya ke huruf kecil). Alternatif yang ditolak: mengubah seluruh
sumber SQL ke huruf besar sebelum lexing, karena itu merusak isi string (`'gold'`) dan nama
identifier.

**Test regresi.** `test_regresi_keyword_tidak_peka_huruf_besar_kecil`. Penjaga tambahan:
`test_tepi_identifier_berawalan_keyword` (`selection` tetap `IDENT`).

**Peran AI.** Claude membantu menemukan bug ini saat membandingkan `_word` dengan SPESIFIKASI
2.2. [KONFIRMASI: tulis bagaimana kalian memverifikasi sendiri, misalnya menjalankan test
sebelum dan sesudah perbaikan.]

---

## Bug 2: `<>` terpecah menjadi dua token

**Ditemukan oleh:** [nama] · **Diperbaiki oleh:** [nama]

**Gejala.** `a <> 1` menghasilkan `OP '<'`, `OP '>'`, `NUMBER '1'`, dan parser melapor
`diharapkan ekspresi, ditemukan '>'`. Pada data contoh, `laporan_penjualan.sql` gagal di baris 6
kolom 41 (`o.catatan <> 'FROM rahasia'`), sehingga statement SELECT pertamanya tidak dihitung (dan, karena Bug 6, seluruh statement
sesudahnya ikut hilang).
SPESIFIKASI 2.5: `<>` adalah satu token.

**Reproduksi minimal.**

```sql
SELECT id FROM t WHERE a <> 1;
```

**Akar masalah.** 
Masalah terjadi karena lexer membandingkan kata yang ditemukan dengan daftar keywords secara langsung, tanpa mengubahnya ke huruf yang sama terlebih dahulu. Akibatnya, kata `select` yang ditulis menggunakan huruf kecil tidak dikenali sebagai keyword `SELECT`, melainkan dianggap sebagai token `IDENT`. Hal ini menyebabkan parser menerima token 'IDENT' padahal parser mengharapkan sebuah statement diawali dengan keyword `SELECT`, sehingga muncul error pada baris 1 kolom 1 dan file `pemeliharaan.sql` gagal diproses. Perbaikan dilakukan pada bagian lexer, bukan parser, karena lexer bertugas mengidentifikasi dan memberikan jenis token, seperti `KEYWORD` atau `IDENT`. Caranya adalah dengan mengubah kata yang ditemukan menjadi huruf besar menggunakan fungsi `upper()` sebelum dicocokkan dengan daftar keywords. Dengan begitu, keyword tetap dikenali meskipun ditulis menggunakan huruf kapital maupun huruf kecil. Perbaikan ini sesuai dengan pembahasan Reserved Words pada Bab 4 buku Crafting Interpreters dan ketentuan pada `SPESIFIKASI.md` bagian 2.2.

**Perbaikan.** `crud/lexer.py`, `_scan_token`: setelah `<`, coba `=` (jadi `<=`), lalu `>`
(jadi `<>`), baru jatuh ke `<`. Alternatif yang ditolak: menggabungkan `<` dan `>` di parser
bila berdampingan, karena itu menyembunyikan kesalahan lexer dan membuat `a < > 1` ikut diterima.

**Test regresi.** `test_regresi_operator_tidak_sama_dengan_satu_token`.

**Peran AI.** [KONFIRMASI: sama seperti Bug 1.]

---

## Bug 3: `''` di dalam string mengakhiri string

**Ditemukan oleh:** [nama] · **Diperbaiki oleh:** [nama]

**Gejala.** `'O''Brien'` menghasilkan dua token `STRING` (`O` dan `Brien`), dan parser melapor
`diharapkan ';' di akhir statement, ditemukan 'Brien'`. Seharusnya satu `STRING` bernilai
`O'Brien` (SPESIFIKASI 2.4). Data contoh `pemeliharaan.sql` memuat `'O''Brien'` dan `'O''Neil'`.

**Reproduksi minimal.**

```sql
SELECT id FROM t WHERE n = 'O''Brien';
```

**Akar masalah.** *[Tulis sendiri.]*
Petunjuk konsep: pemindaian string di lexer (Bab 4) dan kebutuhan melihat satu karakter ke
depan (*lookahead*) sebelum memutuskan sebuah kutip adalah penutup atau bukan.

**Perbaikan.** `crud/lexer.py`, `_string`: saat bertemu `'`, bila karakter berikutnya juga `'`
maka keduanya dikonsumsi dan satu `'` ditambahkan ke nilai; selain itu string berakhir.

**Test regresi.** `test_regresi_kutip_ganda_dalam_string_satu_token`; kasus tepi
`test_tepi_penanda_komentar_di_dalam_string`.

**Peran AI.** [KONFIRMASI.]

---

## Bug 4: `AND` dan `OR` memiliki presedensi yang sama

**Ditemukan oleh:** [nama] · **Diperbaiki oleh:** [nama]

**Gejala.** `a = 1 OR b = 2 AND c = 3` diparse sebagai `((a = 1 OR b = 2) AND c = 3)`.
Menurut SPESIFIKASI 3.1 seharusnya `a = 1 OR (b = 2 AND c = 3)`. Tidak terlihat di test
yang ada karena hanya menguji satu `AND`. Bug ini tidak mengubah CRUD matrix (AND/OR tidak
memengaruhi tabel yang disentuh), tetapi tetap bug karena melanggar spesifikasi. `audit.sql`
baris 4-6 memuat pola ini.

**Reproduksi minimal.**

```sql
SELECT id FROM t WHERE a = 1 OR b = 2 AND c = 3;
```

**Akar masalah.** *[Tulis sendiri.]*
Petunjuk konsep: presedensi dan asosiatif dalam grammar (Bab 5), dan cara recursive descent
menyatakan presedensi (Bab 6): satu fungsi per tingkat, tingkat yang lebih rendah memanggil
tingkat yang lebih tinggi. Hitung berapa tingkat yang dilebur oleh fungsi `_logical` lama.

**Perbaikan.** `crud/parser.py`: `_logical` dipecah menjadi `_or` (memanggil `_and`) dan `_and`
(memanggil `_not`); `_expr` memanggil `_or`. Alternatif yang ditolak: tabel presedensi
numerik (precedence climbing). Lebih ringkas, tetapi grammar di SPESIFIKASI sudah berbentuk satu
aturan per tingkat, sehingga bentuk saat ini lebih mudah dicocokkan satu per satu.

**Test regresi.** `test_regresi_presedensi_and_lebih_tinggi_dari_or`,
`test_regresi_not_lebih_tinggi_dari_and`; kasus tepi `test_tepi_between_diikuti_and_logika`.

**Peran AI.** [KONFIRMASI.]

---

## Bug 5: `LEFT OUTER JOIN` ditolak

**Ditemukan oleh:** [nama] · **Diperbaiki oleh:** [nama]

**Gejala.** `LEFT OUTER JOIN` menghasilkan `Baris 1, kolom 25: diharapkan JOIN, ditemukan
'OUTER'`. Grammar: `"LEFT" [ "OUTER" ] "JOIN"`. Data contoh `pemeliharaan.sql` memakainya.

**Reproduksi minimal.**

```sql
SELECT a.id FROM a LEFT OUTER JOIN b ON b.a_id = a.id;
```

**Akar masalah.** *[Tulis sendiri.]*
Petunjuk konsep: setiap fungsi parser harus menerima persis bahasa yang didefinisikan satu
aturan grammar (Bab 6). Bandingkan `_join` dengan aturan `join` di SPESIFIKASI 3, bagian
yang berada di dalam kurung siku.

**Perbaikan.** `crud/parser.py`, `_join`: setelah `LEFT`, `_match_kw("OUTER")` bersifat opsional.

**Test regresi.** `test_regresi_left_outer_join`.

**Peran AI.** [KONFIRMASI.]

---

## Bug 6: Error recovery membuang seluruh sisa file

**Ditemukan oleh:** [nama] · **Diperbaiki oleh:** [nama]

**Gejala.** Satu statement yang rusak membuat semua statement sesudahnya hilang. Pada
`SELECT id nama, FROM a; SELECT id FROM b; DELETE FROM c;` kode lama menghasilkan 1 error
dan **0** statement; seharusnya 1 error dan 2 statement valid (SPESIFIKASI 6). Pada
`campuran_error.sql`, `UPDATE produk` dan `DELETE FROM keranjang` tidak terhitung.

**Reproduksi minimal.**

```sql
SELECT id nama, FROM a;
SELECT id FROM b;
```

**Akar masalah.** *[Tulis sendiri.]*
Petunjuk konsep: *panic mode* dan *synchronization* (Bab 6, bagian error recovery). Apa
"titik aman" yang dipakai kode lama, dan apa titik aman yang diminta spesifikasi?

**Perbaikan.** `crud/parser.py`, `_synchronize`: membuang token sampai dan **termasuk** `;`
berikutnya. Bila token error adalah `;` itu sendiri (misalnya `SELECT a FROM ;`), token itu
ikut dibuang dan parsing berlanjut ke statement berikutnya.
Alternatif yang ditolak: berhenti di keyword `SELECT/INSERT/UPDATE/DELETE` berikutnya, karena
keyword itu juga muncul di dalam subquery sehingga recovery bisa berhenti di tengah statement
rusak dan menghasilkan error ganda.

**Test regresi.** `test_regresi_recovery_berhenti_di_titik_koma`; kasus tepi
`test_tepi_error_tepat_di_titik_koma`.

**Peran AI.** [KONFIRMASI.]

---

## Bukan bug, tetapi TODO yang diselesaikan

- **T1 `INSERT ... SELECT`** (`parser.py`, `_insert`): memanggil `_select()` dan mengembalikan
  `Insert(table, columns, [], query)`. Test: `test_regresi_insert_select_T1`.
- **T3 komentar blok** (`lexer.py`, `_block_comment`): `*` pembuka dikonsumsi dulu agar `/*/`
  tidak dianggap tertutup; berhenti di `*/` pertama (tidak bersarang); komentar yang tidak
  ditutup menjadi `LexError` di posisi `/*`. Test: `test_regresi_komentar_blok_T3`,
  `test_regresi_komentar_blok_tidak_ditutup_lexerror`, `test_tepi_bentuk_komentar_blok_khusus`.

<!-- Bug dari Anggota 2 (resolver/analyzer) ditambahkan di bawah ini. -->
