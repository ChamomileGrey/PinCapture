# PinCapture optional math pack — not part of the setup.exe
# Created: 2026-10-27 by Grok 4.7 via Cursor
# Changelog:
#   v0.10.0 2026-10-27 Grok 4.7 — deterministic zip of the formula model and Windows runtime
"""
Build PinCapture-Math-<version>.zip for the GitHub release asset.

The base installer does not contain this file. The app downloads it only after
the user clicks 설치. SHA-256 in pincapture.py (MATH_PACK_SHA256, MATH_PACK_BYTES,
MATH_ONNX_SHA256, MATH_TOKENIZER_SHA256) must match this zip.

    py -3.13 installer/build_math_pack.py           # write installer/output/*.zip
    py -3.13 installer/build_math_pack.py --check   # fail if pincapture.py disagrees

Runtime wheels are the official cp313 win_amd64 builds (tokenizers is abi3).
They are extracted so a frozen PinCapture.exe can put the folder on sys.path.
No package is compiled here.
"""
import hashlib
import re
import sys
import urllib.request
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "pincapture.py"
CACHE = HERE / "build" / "math-cache"
STAGE = HERE / "build" / "math-stage"
OUT = HERE / "output"

ONNX_URL = (
    "https://www.modelscope.cn/models/RapidAI/RapidDoc/resolve/v1.0.0/"
    "formula/PP-FormulaNet_plus-S/pp_formulanet_plus_s.onnx"
)
ONNX_NAME = "pp_formulanet_plus_s.onnx"
TOKENIZER_URL = (
    "https://huggingface.co/PaddlePaddle/PP-FormulaNet_plus-S/resolve/main/inference.yml"
)
TOKENIZER_NAME = "inference.yml"
WHEELS = (
    (
        "https://files.pythonhosted.org/packages/4a/93/aba75358133b3a941d736816dd392f687e7eab77215a6e429879080b76b6/"
        "onnxruntime-1.23.2-cp313-cp313-win_amd64.whl",
        "1f9cc0a55349c584f083c1c076e611a7c35d5b867d5d6e6d6c823bf821978088",
    ),
    (
        "https://files.pythonhosted.org/packages/41/f2/fd673d979185f5dcbac4be7d09461cbb99751554ffb6718d0013af8604cb/"
        "tokenizers-0.21.4-cp39-abi3-win_amd64.whl",
        "475d807a5c3eb72c59ad9b5fcdb254f6e17f53dfcbb9903233b0dfa9c943b597",
    ),
    (
        "https://files.pythonhosted.org/packages/cb/3b/d58c12eafcb298d4e6d0d40216866ab15f59e55d148a5658bb3132311fcf/"
        "numpy-2.2.6-cp313-cp313-win_amd64.whl",
        "b0544343a702fa80c95ad5d3d608ea3599dd54d4632df855e4c8d24eb6ecfa1c",
    ),
    (
        "https://files.pythonhosted.org/packages/fa/de/02b54f42487e3d3c6efb3f89428677074ca7bf43aae402517bc7cca949f3/"
        "PyYAML-6.0.2-cp313-cp313-win_amd64.whl",
        "8388ee1976c416731879ac16da0aff3f63b286ffdd57cdeb95f3f2e085687563",
    ),
)
NOTICE = """PinCapture optional math component
This archive is not part of the base installer.
The app downloads it only after the user clicks Install.

PP-FormulaNet_plus-S (PaddlePaddle; ONNX conversion published by RapidAI RapidDoc) — Apache-2.0
ONNX Runtime 1.23.2 — MIT
tokenizers 0.21.4 — Apache-2.0
NumPy 2.2.6 — BSD-3-Clause
PyYAML 6.0.2 — MIT

Wheel license files are in the .dist-info folders under math/.
"""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def download(url: str, dest: Path, expected: str) -> None:
    if dest.is_file() and sha256_file(dest) == expected:
        print(f"cached {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".partial")
    print(f"download {dest.name}")
    request = urllib.request.Request(url, headers={"User-Agent": "PinCapture-math-pack"})
    with urllib.request.urlopen(request, timeout=120) as resp, partial.open("wb") as out:
        while True:
            block = resp.read(1024 * 1024)
            if not block:
                break
            out.write(block)
    digest = sha256_file(partial)
    if digest != expected:
        partial.unlink(missing_ok=True)
        sys.exit(f"hash mismatch for {dest.name}: {digest}")
    partial.replace(dest)


def read_constants() -> dict:
    text = SRC.read_text(encoding="utf-8")
    found = {}
    for name in ("APP_VERSION", "MATH_PACK_SHA256", "MATH_ONNX_SHA256", "MATH_TOKENIZER_SHA256"):
        match = re.search(rf'^{name}\s*=\s*"([^"]*)"', text, re.M)
        if not match:
            sys.exit(f"{name} not found in pincapture.py")
        found[name] = match.group(1)
    match = re.search(r"^MATH_PACK_BYTES\s*=\s*(\d+)", text, re.M)
    if not match:
        sys.exit("MATH_PACK_BYTES not found in pincapture.py")
    found["MATH_PACK_BYTES"] = int(match.group(1))
    return found


def stage_tree(constants: dict) -> None:
    import shutil
    if STAGE.exists():
        shutil.rmtree(STAGE)
    math_dir = STAGE / "math"
    formula = STAGE / "models" / "formula"
    formula.mkdir(parents=True)
    (formula / ONNX_NAME).write_bytes((CACHE / ONNX_NAME).read_bytes())
    (formula / TOKENIZER_NAME).write_bytes((CACHE / TOKENIZER_NAME).read_bytes())
    if sha256_file(formula / ONNX_NAME) != constants["MATH_ONNX_SHA256"]:
        sys.exit("onnx hash does not match pincapture.py")
    if sha256_file(formula / TOKENIZER_NAME) != constants["MATH_TOKENIZER_SHA256"]:
        sys.exit("tokenizer hash does not match pincapture.py")
    for url, digest in WHEELS:
        filename = url.rsplit("/", 1)[-1]
        wheel = CACHE / filename
        download(url, wheel, digest)
        with zipfile.ZipFile(wheel) as archive:
            for info in archive.infolist():
                name = info.filename.replace("\\", "/")
                if name.endswith("/") or name.startswith("/") or ".." in name.split("/"):
                    continue
                target = math_dir / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, target.open("wb") as dst:
                    dst.write(src.read())
    (math_dir / "THIRD_PARTY_NOTICES.txt").write_text(NOTICE, encoding="utf-8", newline="\n")


def write_zip(version: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"PinCapture-Math-{version}.zip"
    files = sorted(path for path in STAGE.rglob("*") if path.is_file())
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            arcname = path.relative_to(STAGE).as_posix()
            info = zipfile.ZipInfo(arcname, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return dest


def main() -> None:
    check = "--check" in sys.argv
    constants = read_constants()
    version = constants["APP_VERSION"]
    CACHE.mkdir(parents=True, exist_ok=True)
    download(ONNX_URL, CACHE / ONNX_NAME, constants["MATH_ONNX_SHA256"])
    download(TOKENIZER_URL, CACHE / TOKENIZER_NAME, constants["MATH_TOKENIZER_SHA256"])
    stage_tree(constants)
    dest = write_zip(version)
    digest = sha256_file(dest)
    size = dest.stat().st_size
    print(f"zip: {dest}")
    print(f"bytes: {size}")
    print(f"sha256: {digest}")
    (OUT / f"{dest.name}.sha256").write_text(f"{digest}  {dest.name}\n", encoding="utf-8")
    if not check:
        return
    if digest != constants["MATH_PACK_SHA256"] or size != constants["MATH_PACK_BYTES"]:
        sys.exit(
            "pincapture.py does not match this zip.\n"
            f"  MATH_PACK_SHA256 = \"{digest}\"\n"
            f"  MATH_PACK_BYTES = {size}"
        )
    print("math pack matches pincapture.py")


if __name__ == "__main__":
    main()
