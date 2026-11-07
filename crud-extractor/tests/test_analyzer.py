from pathlib import Path

from crud.analyzer import analyze_statement
from crud.parser import parse_sql
from crud.pipeline import analyze_source

DATA = Path(__file__).resolve().parents[1] / "data" / "sample"


def crud(sql):
    script = parse_sql(sql)
    assert script.errors == [], script.errors
    return analyze_statement(script.statements[0])


def test_crud_select_join():
    assert crud("SELECT p.id FROM pelanggan p JOIN pesanan o ON o.pelanggan_id = p.id") == {
        "pelanggan": {"R"}, "pesanan": {"R"}}


def test_crud_insert_values():
    assert crud("INSERT INTO log (id) VALUES (1)") == {"log": {"C"}}


def test_crud_update_sederhana():
    assert crud("UPDATE produk SET stok = stok - 1 WHERE id = 3") == {"produk": {"U"}}


def test_crud_delete():
    assert crud("DELETE FROM sesi WHERE dibuat < :batas") == {"sesi": {"D"}}


def test_matrix_laporan_penjualan():
    res = analyze_source((DATA / "laporan_penjualan.sql").read_text(encoding="utf-8"))
    assert res.lex_error is None and res.parse_errors == []
    assert res.matrix() == {"arsip_pesanan": "C", "pelanggan": "RU", "pesanan": "RD"}


# ---- regresi bug analyzer -------------------------------------------------
def test_regresi_update_subquery_di_where_dibaca_R():
    # Bug: subquery di UPDATE ditandai "U", padahal membaca lewat subquery selalu R (SPESIFIKASI 5).
    assert crud("UPDATE pelanggan SET level = 'gold' "
                "WHERE id IN (SELECT pelanggan_id FROM pesanan)") == {
        "pelanggan": {"U"}, "pesanan": {"R"}}


def test_regresi_update_subquery_di_set_dibaca_R():
    assert crud("UPDATE a SET x = (SELECT MAX(y) FROM b)") == {"a": {"U"}, "b": {"R"}}


# ---- kasus tepi analyzer --------------------------------------------------
def test_tepi_tabel_sama_target_dan_subquery_jadi_RU():
    # Satu tabel punya dua peran; hasil gabungan harus {R, U} dan tertulis "RU".
    from crud.pipeline import format_ops
    ops = crud("UPDATE pesanan SET status = 'X' WHERE id IN (SELECT id FROM pesanan)")
    assert ops == {"pesanan": {"R", "U"}}
    assert format_ops(ops["pesanan"]) == "RU"


def test_tepi_delete_dengan_subquery_baca_tabel_lain():
    assert crud("DELETE FROM alamat WHERE pelanggan_id NOT IN (SELECT id FROM pelanggan)") == {
        "alamat": {"D"}, "pelanggan": {"R"}}


def test_tepi_subquery_bersarang_dan_derived_table_R():
    sql = ("SELECT d.x FROM (SELECT a.id AS x FROM a WHERE a.id IN (SELECT id FROM b)) d "
           "WHERE EXISTS (SELECT 1 FROM c)")
    assert crud(sql) == {"a": {"R"}, "b": {"R"}, "c": {"R"}}


def test_tepi_penggunaan_kolom_butuh_resolusi():
    # Kolom ambigu (resolved None) tidak boleh ditebak masuk ke column_usage.
    from crud.analyzer import column_usage
    from crud.resolver import Resolver
    script = parse_sql("SELECT nama, p.id FROM pelanggan p JOIN pesanan o ON o.pelanggan_id = p.id")
    Resolver().resolve_script(script)
    usage = column_usage(script.statements[0])
    assert ("pelanggan", "id", "R") in usage and ("pesanan", "pelanggan_id", "R") in usage
    assert all(name != "nama" for _, name, _ in usage)


def test_tepi_update_kolom_set_tercatat_U_dan_pembacaan_R():
    from crud.analyzer import column_usage
    from crud.resolver import Resolver
    script = parse_sql("UPDATE produk SET stok = stok - 1 WHERE id = 3")
    Resolver().resolve_script(script)
    assert column_usage(script.statements[0]) == {
        ("produk", "stok", "U"), ("produk", "stok", "R"), ("produk", "id", "R")}
