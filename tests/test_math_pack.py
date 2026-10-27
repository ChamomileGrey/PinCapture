"""The optional math zip must be byte-stable on Windows and Linux."""
import importlib.util
import zipfile
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / "installer" / "build_math_pack.py"
    spec = importlib.util.spec_from_file_location("build_math_pack", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pack_order_is_case_sensitive_parts_not_windows_casefold(tmp_path):
    module = _load()
    names = [
        "math/PyYAML-6.0.2.dist-info/LICENSE",
        "math/_yaml/__init__.py",
        "math/numpy/__init__.py",
        "math/numpy-2.2.6.dist-info/METADATA",
    ]
    for rel in names:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(rel.encode("ascii"))
    ordered = [path.relative_to(tmp_path).as_posix() for path in module.iter_pack_files(tmp_path)]
    assert ordered == sorted(names, key=module.pack_sort_key)
    assert ordered != sorted(names, key=str.lower)
    assert ordered.index("math/PyYAML-6.0.2.dist-info/LICENSE") < ordered.index("math/_yaml/__init__.py")
    # 'numpy' is a shorter part than 'numpy-…', so the directory comes first.
    # A raw string sort would put 'numpy-' first because '-' < '/'.
    assert ordered.index("math/numpy/__init__.py") < ordered.index("math/numpy-2.2.6.dist-info/METADATA")


def test_pack_zip_bytes_do_not_follow_directory_order(tmp_path):
    module = _load()
    names = [
        "math/PyYAML-6.0.2.dist-info/LICENSE",
        "math/_yaml/__init__.py",
        "models/formula/a.bin",
    ]
    hashes = []
    for index, ordered in enumerate((names, list(reversed(names)))):
        root = tmp_path / f"stage-{index}"
        for rel in ordered:
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"same-bytes")
        dest = tmp_path / f"pack-{index}.zip"
        module.write_deterministic_zip(root, dest)
        with zipfile.ZipFile(dest) as archive:
            assert archive.namelist() == sorted(names, key=module.pack_sort_key)
            assert all(info.date_time[:3] == (2026, 1, 1) for info in archive.infolist())
            assert all(info.create_system == 3 for info in archive.infolist())
        hashes.append(dest.read_bytes())
    assert hashes[0] == hashes[1]
