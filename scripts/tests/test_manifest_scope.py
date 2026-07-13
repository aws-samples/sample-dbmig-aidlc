from dbmig import config


def test_manifest_file_scoped_and_legacy():
    assert config.manifest_file("manifest", "Person") == "manifest-PERSON.yaml"
    assert config.manifest_file("code-manifest", "sales") == "code-manifest-SALES.yaml"
    assert config.manifest_file("test-manifest", None) == "test-manifest.yaml"


def test_resolve_manifest_write_is_scoped(tmp_path):
    p = config.resolve_manifest(tmp_path, "manifest", "Person", for_write=True)
    assert p.name == "manifest-PERSON.yaml"


def test_resolve_manifest_read_prefers_scoped(tmp_path):
    (tmp_path / "manifest-PERSON.yaml").write_text("x")
    (tmp_path / "manifest.yaml").write_text("y")
    assert config.resolve_manifest(tmp_path, "manifest", "Person").name == "manifest-PERSON.yaml"


def test_resolve_manifest_read_falls_back_to_legacy(tmp_path):
    (tmp_path / "manifest.yaml").write_text("y")  # only legacy exists
    assert config.resolve_manifest(tmp_path, "manifest", "Person").name == "manifest.yaml"


def test_resolve_manifest_defaults_to_scoped_for_fresh_run(tmp_path):
    # neither exists -> a fresh run uses the schema-scoped name
    assert config.resolve_manifest(tmp_path, "manifest", "Person").name == "manifest-PERSON.yaml"


def test_two_schemas_one_project_do_not_collide(tmp_path):
    a = config.resolve_manifest(tmp_path, "manifest", "Person", for_write=True)
    b = config.resolve_manifest(tmp_path, "manifest", "Sales", for_write=True)
    assert a != b and a.name == "manifest-PERSON.yaml" and b.name == "manifest-SALES.yaml"
