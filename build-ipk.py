#!/usr/bin/env python3
"""Build an OpenWrt .ipk for luci-app-openflux without the OpenWrt SDK.

The package is architecture independent: it only contains shell scripts,
LuCI JavaScript and a UCI config. The OpenFlux client binary is not bundled.

Usage:
    python3 build-ipk.py

Result:
    dist/luci-app-openflux_<version>_all.ipk
"""

import gzip
import io
import os
import sys
import tarfile
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "root")
DIST = os.path.join(HERE, "dist")

PKG_NAME = "luci-app-openflux"
PKG_SECTION = "luci"
PKG_DEPENDS = "luci-base"
PKG_MAINTAINER = "OpenFlux LuCI contributors"
PKG_DESCRIPTION = (
    "LuCI application for the OpenFlux client. Keeps any number of tunnel "
    "profiles in UCI and runs exactly one selected profile, exposing a local "
    "SOCKS5 port for proxy managers such as Mihomo or sing-box."
)

FIXED_MTIME = 1700000000
FIXED_UID = 0
FIXED_GID = 0


def read_version():
    with open(os.path.join(HERE, "VERSION"), encoding="utf-8") as fh:
        return fh.read().strip()


def file_mode(rel):
    rel = rel.replace("\\", "/")
    if rel in ("etc/init.d/openflux",):
        return 0o755
    if rel == "etc/config/openflux":
        return 0o600
    return 0o644


def add_bytes(tar, name, data, mode):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.mtime = FIXED_MTIME
    info.uid = FIXED_UID
    info.gid = FIXED_GID
    info.uname = "root"
    info.gname = "root"
    tar.addfile(info, io.BytesIO(data))


def add_dir(tar, name):
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    info.size = 0
    info.mode = 0o755
    info.mtime = FIXED_MTIME
    info.uid = FIXED_UID
    info.gid = FIXED_GID
    info.uname = "root"
    info.gname = "root"
    tar.addfile(info)


def make_tar_gz(entries):
    """entries: list of (arcname, bytes|None, mode); None means directory."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tar:
        dirs = set()
        for arcname, data, _ in entries:
            parts = arcname.strip("./").split("/")[:-1]
            acc = "."
            for part in parts:
                acc = acc + "/" + part
                if acc not in dirs:
                    dirs.add(acc)
                    add_dir(tar, acc)
        for arcname, data, mode in entries:
            if data is None:
                if arcname.strip("./") not in dirs:
                    dirs.add(arcname.strip("./"))
                    add_dir(tar, arcname)
            else:
                add_bytes(tar, arcname, data, mode)

    packed = io.BytesIO()
    with gzip.GzipFile(fileobj=packed, mode="wb", compresslevel=9, mtime=0) as gz:
        gz.write(raw.getvalue())
    return packed.getvalue()


def ar_entry(name, data):
    if len(name) % 2:
        name += " "
    header = (
        name.ljust(16).encode()
        + b"0".ljust(12)
        + b"0".ljust(6)
        + b"0".ljust(6)
        + b"100644".ljust(8)
        + str(len(data)).encode().ljust(10)
        + b"`\n"
    )
    payload = data + (b"\n" if len(data) % 2 else b"")
    return header + payload


def collect_data_files():
    entries = []
    files = []
    for base, _dirs, names in os.walk(ROOT):
        for name in names:
            path = os.path.join(base, name)
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            files.append((rel, path))
    files.sort()

    for rel, path in files:
        with open(path, "rb") as fh:
            data = fh.read()
        if rel == "etc/config/openflux":
            data = data.replace(b"\r\n", b"\n")
        entries.append(("./" + rel, data, file_mode(rel)))
    return entries


def build():
    version = read_version()
    data_entries = collect_data_files()
    total_bytes = sum(len(data) for _, data, _ in data_entries if data is not None)
    installed_kb = max(1, (total_bytes + 1023) // 1024)

    desc = textwrap.wrap(PKG_DESCRIPTION, width=76)
    control_lines = [
        "Package: " + PKG_NAME,
        "Version: " + version,
        "Depends: " + PKG_DEPENDS,
        "Section: " + PKG_SECTION,
        "Priority: optional",
        "Maintainer: " + PKG_MAINTAINER,
        "Architecture: all",
        "Installed-Size: " + str(installed_kb),
        "Description: " + desc[0],
    ]
    control_lines += [" " + line for line in desc[1:]]
    control = "\n".join(control_lines)

    postinst = """#!/bin/sh
[ -n "$IPKG_INSTROOT" ] && exit 0

mkdir -p /etc/openflux
chmod 600 /etc/config/openflux 2>/dev/null
rm -rf /tmp/luci-indexcache* /tmp/luci-modulecache 2>/dev/null
/etc/init.d/rpcd restart >/dev/null 2>&1
/etc/init.d/uhttpd restart >/dev/null 2>&1
exit 0
"""

    control_entries = [
        ("./control", (control + "\n").encode(), 0o644),
        ("./conffiles", b"/etc/config/openflux\n", 0o644),
        ("./postinst", postinst.encode(), 0o755),
    ]

    control_tar = make_tar_gz(control_entries)
    data_tar = make_tar_gz(data_entries)

    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "%s_%s_all.ipk" % (PKG_NAME, version))
    with open(out, "wb") as fh:
        fh.write(b"!<arch>\n")
        fh.write(ar_entry("debian-binary", b"2.0\n"))
        fh.write(ar_entry("control.tar.gz", control_tar))
        fh.write(ar_entry("data.tar.gz", data_tar))

    print("built:", out)
    print("size: %.1f KiB" % (os.path.getsize(out) / 1024.0))
    print("files:", len(data_entries))
    return out


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:  # noqa: BLE001
        print("build failed:", exc, file=sys.stderr)
        sys.exit(1)
