from __future__ import annotations

import zipfile


ZIP_TIMESTAMP = (2000, 1, 1, 0, 0, 0)


def write_stable_zip_entry(zf: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, data)
