# -*- mode: python ; coding: utf-8 -*-
# PinCapture PyInstaller spec (onedir). Called by installer/build.py.
# Manual build: py -3.13 -m PyInstaller --noconfirm --distpath build/dist --workpath build/work PinCapture.spec
#   (run from the installer/ folder after build.py has generated build/pincapture.ico and build/version_info.txt)
import os

HERE = SPECPATH                      # installer/
ROOT = os.path.dirname(HERE)         # project root (pincapture.py)
BUILD = os.path.join(HERE, "build")

a = Analysis(
    [os.path.join(ROOT, "pincapture.py")],
    pathex=[ROOT],
    excludes=["tkinter", "unittest", "pydoc", "pdb", "doctest", "lib2to3", "xmlrpc"],
    # LGPL: ship pynput as plain .py files under _internal/pynput so a user can replace it.
    # (PySide6/Qt are already separate DLL/pyd files under _internal/PySide6.)
    module_collection_mode={"pynput": "py"},
)

# Qt pieces this app never uses. Fewer components = smaller install and fewer third-party notices.
# The app uses QtNetwork only for QLocalServer/QLocalSocket (no TLS) and only reads/writes PNG, JPG, ICO.
# Kept on purpose: platforms/qwindows, platforms/qoffscreen (build smoke test), styles/qmodernwindowsstyle,
# imageformats/qico, imageformats/qjpeg, and Python's own libcrypto-3.dll (needed by _hashlib).
DROP = {
    "opengl32sw.dll",
    "qt6pdf.dll", "qpdf.dll",
    "qt6qml.dll", "qt6qmlmodels.dll", "qt6qmlmeta.dll", "qt6qmlworkerscript.dll",
    "qt6quick.dll", "qt6virtualkeyboard.dll",
    # TLS / network-information plugins and Qt's private OpenSSL copy
    "qcertonlybackend.dll", "qopensslbackend.dll", "qschannelbackend.dll", "qnetworklistmanager.dll",
    "libssl-3-x64.dll", "libcrypto-3-x64.dll",
    # image formats / icon engines the app never loads
    "qgif.dll", "qicns.dll", "qsvg.dll", "qtga.dll", "qtiff.dll", "qwbmp.dll", "qwebp.dll",
    "qsvgicon.dll", "qt6svg.dll",
    # input / platform plugins not needed on a desktop
    "qtvirtualkeyboardplugin.dll", "qtuiotouchplugin.dll", "qdirect2d.dll", "qminimal.dll",
}
a.binaries = [b for b in a.binaries if os.path.basename(b[0]).lower() not in DROP]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PinCapture",
    console=False,
    upx=False,
    icon=os.path.join(BUILD, "pincapture.ico"),
    version=os.path.join(BUILD, "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PinCapture",
)
