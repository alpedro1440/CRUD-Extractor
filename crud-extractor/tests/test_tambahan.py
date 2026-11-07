"""Test tambahan buatan kelompok.

Isi dengan:
1. Satu test regresi untuk setiap bug yang kalian perbaiki (gagal sebelum perbaikan,
   lulus sesudahnya). Beri nama yang menjelaskan bug-nya.
2. Lima test kasus tepi, masing-masing dengan komentar singkat mengapa kasus itu berisiko.

Bagian A (Anggota 1): lexer dan parser. Anggota 2 menambahkan bagian resolver/analyzer di bawahnya.
"""
import pytest

from crud import ast_nodes as ast
from crud.lexer import LexError, TokenType as T, tokenize
from crud.analyzer import analyze_statement
from crud.parser import parse_sql
from crud.resolver import Resolver



# ---- helper -----------------------------------------------------------------
def tok_values(src):
    return [t.value for t in tokenize(src) if t.type != T.EOF]


def tok_types(src):
    return [t.type for t in tokenize(src) if t.type != T.EOF]


def shape(node):
    """Ringkas ekspresi menjadi tuple bersarang agar bentuk pohon mudah dibandingkan."""
    if isinstance(node, ast.BinaryOp):
        return (node.op, shape(node.left), shape(node.right))
    if isinstance(node, ast.UnaryOp):
        return (node.op, shape(node.operand))
    if isinstance(node, ast.Between):
        return ("BETWEEN", shape(node.expr), shape(node.low), shape(node.high))
    if isinstance(node, ast.ColumnRef):
        return node.name
    if isinstance(node, ast.Literal):
        return node.value
    raise AssertionError(f"node tidak dikenal: {node!r}")


def crud(sql):
    script = parse_sql(sql)
    assert script.errors == [], script.errors
    return analyze_statement(script.statements[0])


def resolve(sql):
    script = parse_sql(sql)
    assert script.errors == [], script.errors
    return script, Resolver().resolve_script(script)


def columns(node):
    return [n for n in ast.iter_nodes(node) if isinstance(n, ast.ColumnRef)]

def where_of(sql):
    script = parse_sql(sql)
    assert script.errors == [], script.errors
    return script.statements[0].where


# =============================================================================
# A. TEST REGRESI (satu per bug)
# =============================================================================

# ---- Lexer ------------------------------------------------------------------
def test_regresi_keyword_tidak_peka_huruf_besar_kecil():
    # Bug: kata dicocokkan ke KEYWORDS tanpa .upper(), jadi `select` menjadi IDENT.
    toks = tokenize("select Id From t wHeRe")
    assert [(t.type, t.value) for t in toks[:5]] == [
        (T.KEYWORD, "SELECT"), (T.IDENT, "Id"), (T.KEYWORD, "FROM"),
        (T.IDENT, "t"), (T.KEYWORD, "WHERE"),
    ]


def test_regresi_operator_tidak_sama_dengan_satu_token():
    # Bug: maximal munch tidak diterapkan untuk `<`; `<>` terpecah menjadi `<` lalu `>`.
    assert tok_values("a <> 1") == ["a", "<>", "1"]
    assert tok_types("a <> 1") == [T.IDENT, T.OP, T.NUMBER]


def test_regresi_kutip_ganda_dalam_string_satu_token():
    # Bug: `''` dianggap penutup string, sehingga 'O''Brien' menjadi dua string.
    toks = tokenize("'O''Brien'")
    assert [(t.type, t.value) for t in toks[:-1]] == [(T.STRING, "O'Brien")]


def test_regresi_komentar_blok_T3():
    # TODO(T3): komentar blok lintas baris, berisi '*', tidak menghasilkan token,
    # dan nomor baris token sesudahnya tetap benar.
    toks = tokenize("/* satu *\n   dua ** */ SELECT /* x */ a")
    assert [(t.type, t.value) for t in toks[:-1]] == [(T.KEYWORD, "SELECT"), (T.IDENT, "a")]
    assert (toks[0].line, toks[0].col) == (2, 14)


def test_regresi_komentar_blok_tidak_ditutup_lexerror():
    with pytest.raises(LexError) as info:
        tokenize("SELECT a\n  /* tidak pernah ditutup")
    assert (info.value.line, info.value.col) == (2, 3)
    assert "tidak ditutup" in str(info.value)


# ---- Parser -----------------------------------------------------------------
def test_regresi_presedensi_and_lebih_tinggi_dari_or():
    # Bug: AND dan OR ditangani satu fungsi dengan presedensi sama (kiri-ke-kanan).
    w = where_of("SELECT id FROM t WHERE a = 1 OR b = 2 AND c = 3")
    assert shape(w) == ("OR", ("=", "a", "1"), ("AND", ("=", "b", "2"), ("=", "c", "3")))
    w = where_of("SELECT id FROM t WHERE a = 1 AND b = 2 OR c = 3")
    assert shape(w) == ("OR", ("AND", ("=", "a", "1"), ("=", "b", "2")), ("=", "c", "3"))


def test_regresi_not_lebih_tinggi_dari_and():
    w = where_of("SELECT id FROM t WHERE NOT a = 1 AND b = 2")
    assert shape(w) == ("AND", ("NOT", ("=", "a", "1")), ("=", "b", "2"))


def test_regresi_left_outer_join():
    # Bug: _join tidak menerima OUTER setelah LEFT (grammar: "LEFT" [ "OUTER" ]).
    script = parse_sql("SELECT a.id FROM a LEFT OUTER JOIN b ON b.a_id = a.id")
    assert script.errors == []
    join = script.statements[0].joins[0]
    assert join.kind == "LEFT" and join.source.name == "b"


def test_regresi_recovery_berhenti_di_titik_koma():
    # Bug: _synchronize membuang token sampai EOF, sehingga statement valid sesudah error hilang.
    sql = "SELECT id nama, FROM a;\nSELECT id FROM b;\nDELETE FROM;\nDELETE FROM c;"
    script = parse_sql(sql)
    assert [e.line for e in script.errors] == [1, 3]          # tepat satu error per statement rusak
    assert [type(s).__name__ for s in script.statements] == ["Select", "Delete"]
    assert [s.table.name if hasattr(s, "table") else s.sources[0].name
            for s in script.statements] == ["b", "c"]


def test_regresi_insert_select_T1():
    # TODO(T1): INSERT ... SELECT, dengan dan tanpa daftar kolom.
    s = parse_sql("INSERT INTO arsip (id, total) SELECT id, total FROM pesanan WHERE total > 1").statements[0]
    assert isinstance(s, ast.Insert)
    assert s.columns == ["id", "total"] and s.values == []
    assert isinstance(s.query, ast.Select) and s.query.sources[0].name == "pesanan"

    s = parse_sql("INSERT INTO arsip SELECT id FROM pesanan").statements[0]
    assert s.columns == [] and s.query.sources[0].name == "pesanan"

# ---- analyzer -----------------------------------------------------------------
def test_regresi_update_subquery_di_where_dibaca_R():
    # Bug: subquery di UPDATE ditandai "U", padahal membaca lewat subquery selalu R (SPESIFIKASI 5).
    assert crud("UPDATE pelanggan SET level = 'gold' "
                "WHERE id IN (SELECT pelanggan_id FROM pesanan)") == {
        "pelanggan": {"U"}, "pesanan": {"R"}}


def test_regresi_update_subquery_di_set_dibaca_R():
    assert crud("UPDATE a SET x = (SELECT MAX(y) FROM b)") == {"a": {"U"}, "b": {"R"}}


# ---- resolver -----------------------------------------------------------------
def test_regresi_shadowing_alias_dalam_menutupi_luar():
    # Bug: _lookup() dulu mencari dari scope terluar, sehingga x di subquery
    # ter-resolve ke pelanggan (luar), bukan pesanan (dalam). SPESIFIKASI 4.3.
    script, _ = resolve(
        "SELECT x.id FROM pelanggan x WHERE x.id IN (SELECT x.pelanggan_id FROM pesanan x)")
    dalam = [c for c in columns(script) if c.name == "pelanggan_id"][0]
    luar = [c for c in columns(script) if c.name == "id"][0]
    assert dalam.resolved == "pesanan"
    assert luar.resolved == "pelanggan"


def test_regresi_scope_delete_tidak_bocor_ke_statement_berikutnya():
    # Bug: _delete() tidak memanggil _pop(), jadi alias s bocor. SPESIFIKASI 4.5.
    _, diags = resolve("DELETE FROM sesi s WHERE s.id = 1; DELETE FROM sesi s WHERE s.id = 2")
    assert diags == []                       # dulu: error "dideklarasikan dua kali"
    _, diags = resolve("DELETE FROM sesi s WHERE s.id = 1; SELECT s.id FROM pengguna u")
    assert [d.level for d in diags] == ["error"]   # alias s tidak boleh terlihat lagi


def test_regresi_kolom_tanpa_qualifier_satu_tabel_t2():
    # TODO T2 dulu kosong: resolved selalu None.
    script, diags = resolve("UPDATE produk SET stok = stok - 1 WHERE id = 3")
    assert {c.resolved for c in columns(script)} == {"produk"}
    assert diags == []


# =============================================================================
# B. KASUS TEPI (lima)
# =============================================================================

def test_tepi_identifier_berawalan_keyword():
    # Berisiko: pencocokan keyword memakai startswith/prefix. Yang benar: cocok seluruh kata.
    toks = tokenize("selection fromage order_total insertion")
    assert [t.type for t in toks[:-1]] == [T.IDENT] * 4


def test_tepi_penanda_komentar_di_dalam_string():
    # Berisiko: lexer menganggap `--` atau `/*` di dalam string sebagai awal komentar.
    toks = tokenize("SELECT '-- bukan /* komentar' FROM t")
    assert [t.value for t in toks[:-1]] == ["SELECT", "-- bukan /* komentar", "FROM", "t"]


def test_tepi_bentuk_komentar_blok_khusus():
    # Berisiko: `/*/` bukan komentar utuh (bintang pembuka tidak boleh dipakai ulang sebagai
    # bagian penutup), dan `/**/` adalah komentar kosong yang sah.
    assert tok_values("/*/ masih komentar */ SELECT") == ["SELECT"]
    assert tok_values("/**/ SELECT /***/ a") == ["SELECT", "a"]
    with pytest.raises(LexError):
        tokenize("/*/ tidak ditutup")


def test_tepi_between_diikuti_and_logika():
    # Berisiko: AND milik BETWEEN tertukar dengan AND logika (spesifikasi 3.2).
    w = where_of("SELECT id FROM t WHERE x BETWEEN 1 AND 5 AND y = 2")
    assert shape(w) == ("AND", ("BETWEEN", "x", "1", "5"), ("=", "y", "2"))


def test_tepi_error_tepat_di_titik_koma():
    # Berisiko: error terdeteksi pada token `;` itu sendiri. Recovery harus ikut membuang `;`
    # tersebut, bukan berhenti sebelumnya (lalu menghasilkan error kedua) dan bukan melewatinya.
    script = parse_sql("SELECT a FROM ;\nSELECT b FROM t;")
    assert len(script.errors) == 1
    assert str(script.errors[0]) == "Baris 1, kolom 15: diharapkan nama tabel, ditemukan ';'"
    assert len(script.statements) == 1 and script.statements[0].sources[0].name == "t"
