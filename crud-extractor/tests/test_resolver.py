from crud import ast_nodes as ast
from crud.parser import parse_sql
from crud.resolver import Resolver


def resolve(sql):
    script = parse_sql(sql)
    assert script.errors == [], script.errors
    diagnostics = Resolver().resolve_script(script)
    return script, diagnostics


def columns(node):
    return [n for n in ast.iter_nodes(node) if isinstance(n, ast.ColumnRef)]


def test_alias_qualified_teresolusi():
    script, diags = resolve("SELECT p.nama FROM pelanggan p JOIN pesanan o ON o.pelanggan_id = p.id")
    resolved = {(c.qualifier, c.name): c.resolved for c in columns(script)}
    assert resolved[("p", "nama")] == "pelanggan"
    assert resolved[("o", "pelanggan_id")] == "pesanan"
    assert diags == []


def test_alias_tidak_terdefinisi():
    _, diags = resolve("SELECT q.nama FROM pelanggan p")
    assert [d.level for d in diags] == ["error"]
    assert "'q'" in diags[0].message


def test_kolom_tanpa_qualifier_satu_tabel():
    script, diags = resolve("SELECT nama FROM pelanggan WHERE aktif = 1")
    assert {c.resolved for c in columns(script)} == {"pelanggan"}
    assert diags == []


def test_subquery_in_alias_dalam():
    script, diags = resolve(
        "SELECT p.id FROM pelanggan p WHERE p.id IN (SELECT o.pelanggan_id FROM pesanan o)")
    inner = [c for c in columns(script) if c.qualifier == "o"][0]
    assert inner.resolved == "pesanan"
    assert diags == []


# ---- regresi bug resolver -------------------------------------------------
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


# ---- kasus tepi resolver --------------------------------------------------
def test_tepi_kolom_ambigu_tanpa_qualifier():
    # Tanpa skema, resolver tidak tahu kolom milik tabel mana: warning, bukan tebakan.
    script, diags = resolve("SELECT nama FROM pelanggan p JOIN pesanan o ON o.pelanggan_id = p.id")
    nama = [c for c in columns(script) if c.name == "nama"][0]
    assert nama.resolved is None
    assert [(d.level, d.message) for d in diags] == [("warning", "kolom 'nama' ambigu tanpa skema")]


def test_tepi_correlated_subquery_melihat_alias_luar():
    # Qualifier dicari ke luar; p ada di scope luar, tetap valid di subquery.
    script, diags = resolve(
        "SELECT p.id FROM pelanggan p WHERE EXISTS (SELECT 1 FROM pesanan o WHERE o.pelanggan_id = p.id)")
    assert diags == []
    assert {c.resolved for c in columns(script) if c.qualifier == "p"} == {"pelanggan"}


def test_tepi_unqualified_di_subquery_hanya_lihat_scope_terdalam():
    # `total` tanpa qualifier di subquery hanya melihat pesanan, walau ada pelanggan di luar.
    script, diags = resolve(
        "SELECT p.id FROM pelanggan p WHERE p.id IN (SELECT pelanggan_id FROM pesanan WHERE total > 1)")
    inner = [c for c in columns(script) if c.qualifier is None]
    assert {c.resolved for c in inner} == {"pesanan"}
    assert diags == []


def test_tepi_subquery_from_tidak_melihat_tabel_saudara():
    # SPESIFIKASI 4.4: subquery di FROM di-resolve sebelum scope SELECT-nya dibuat.
    _, diags = resolve("SELECT d.x FROM pelanggan a, (SELECT a.id AS x FROM pesanan b) d")
    assert [d.level for d in diags] == ["error"]
    assert "'a'" in diags[0].message


def test_tepi_subquery_from_tanpa_alias_warning_dan_kolom_ke_subquery():
    _, diags = resolve("SELECT 1 FROM (SELECT id FROM pelanggan)")
    assert [d.level for d in diags] == ["warning"]
    script, diags = resolve("SELECT d.id FROM (SELECT id FROM pelanggan) d")
    assert [c.resolved for c in columns(script) if c.qualifier == "d"] == ["<subquery d>"]


def test_tepi_alias_ganda_dalam_scope_sama_error():
    _, diags = resolve("SELECT a.id FROM pelanggan a JOIN pesanan a ON a.id = a.id")
    assert "error" in [d.level for d in diags]


def test_tepi_tabel_berskema_memakai_nama_terakhir_sebagai_qualifier():
    script, diags = resolve("SELECT pelanggan.nama FROM crm.pelanggan")
    assert {c.resolved for c in columns(script)} == {"crm.pelanggan"}
    assert diags == []
