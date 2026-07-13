from dbmig.engines.sqlserver import summarize_cross_schema_deps
from dbmig.engines import _common


def test_helper_is_shared_across_adapters():
    # The summarizer now lives in engines._common and is re-exported by the SQL Server
    # adapter and reused by the Oracle adapter; both paths must agree.
    rows = [("v", "Other", "t")]
    assert (summarize_cross_schema_deps(rows, "dbo")
            == _common.summarize_cross_schema_deps(rows, "dbo")
            == [{"referenced_schema": "Other", "edges": ["v -> Other.t"]}])



def test_groups_by_referenced_schema_and_drops_same_schema_and_null():
    rows = [
        ("ufnGetStock", "Production", "ProductInventory"),
        ("uspGetBillOfMaterials", "Production", "Product"),
        ("uspLogError", "dbo", "ErrorLog"),          # same schema -> dropped
        ("ufnGetContactInformation", "Purchasing", "Vendor"),
        ("ufnGetContactInformation", None, None),      # null ref -> dropped
    ]
    out = summarize_cross_schema_deps(rows, "dbo")
    schemas = [d["referenced_schema"] for d in out]
    assert schemas == ["Production", "Purchasing"]            # sorted, dbo excluded
    prod = next(d for d in out if d["referenced_schema"] == "Production")
    assert prod["edges"] == [
        "ufnGetStock -> Production.ProductInventory",
        "uspGetBillOfMaterials -> Production.Product",
    ]


def test_same_schema_match_is_case_insensitive():
    rows = [("v", "DBO", "t"), ("v", "HumanResources", "Employee")]
    out = summarize_cross_schema_deps(rows, "dbo")
    assert [d["referenced_schema"] for d in out] == ["HumanResources"]


def test_deduplicates_repeated_edges():
    rows = [("v", "Person", "Person"), ("v", "Person", "Person")]
    out = summarize_cross_schema_deps(rows, "Sales")
    assert out == [{"referenced_schema": "Person", "edges": ["v -> Person.Person"]}]


def test_empty_when_no_cross_schema_refs():
    assert summarize_cross_schema_deps([("v", "dbo", "t")], "dbo") == []
