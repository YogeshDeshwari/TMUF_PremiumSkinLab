"""tyre_patch -- byte-level tyre invariant for CanvasComposer.

The composer's save() pipeline decodes the template Details.dds to
RGBA, recolours small accent regions, then re-encodes to DXT5.  The
re-encode step is LOSSY: even pixels that were never modified can drift
by 1-3 channel values per block because DXT5 picks block endpoints
from a small lookup table.

This module restores byte-identical tyre / wheel / rim blocks by
COPYING the original 16-byte DXT5 blocks from the template's
Details.dds into the freshly-encoded one, for every block that
overlaps a canonical tyre region (wheel disc, tread strip, sidewall
strip).  Mip levels included.

Region definitions (at REF=4096):
  * wheel_disc:  circle centre (1161, 506), radius 498
  * tread:       rect (0, 0)        -> (640, 960)
  * sidewall:    rect (50, 1430)    -> (1380, 1560)

Identical to tools/audit_tyre_invariant.py and tire_customizer.py.
"""
from __future__ import annotations

import struct

import numpy as np

# Canonical reference scale used by tire_customizer.  Both the
# template and our re-encoded Details.dds are at 4096x4096 -- if either
# is a different size, the patch is skipped (fail-safe).
REF = 4096
_WHEEL_CX = 1161
_WHEEL_CY = 506
_WHEEL_R = 498
_TREAD_X0, _TREAD_Y0, _TREAD_X1, _TREAD_Y1 = 0, 0, 640, 960
_SWALL_X0, _SWALL_Y0, _SWALL_X1, _SWALL_Y1 = 50, 1430, 1380, 1560

DDSD_MIPMAPCOUNT = 0x20000


def _block_mask_for_level(
    width: int,
    height: int,
    *,
    include_disc: bool = True,
    include_tread: bool = True,
    include_sidewall: bool = True,
) -> np.ndarray:
    """Return a (n_blocks_y, n_blocks_x) bool mask: True = block to restore.

    A block (4x4 pixels) is in the mask if any of its 4x4 pixels falls
    inside one of the protected regions.  Each region can be toggled
    independently -- e.g. a builder painting an outer-face ring on the
    wheel disc can pass ``include_disc=False`` to skip protecting the
    disc while keeping the rubber (tread + sidewall) invariant.
    """
    nbx = (width + 3) // 4
    nby = (height + 3) // 4
    sx = width / REF
    sy = height / REF

    bx_lo = np.arange(nbx) * 4
    bx_hi = bx_lo + 4
    by_lo = np.arange(nby)[:, None] * 4
    by_hi = by_lo + 4

    mask = np.zeros((nby, nbx), dtype=bool)

    if include_disc:
        cx = _WHEEL_CX * sx
        cy = _WHEEL_CY * sy
        r = _WHEEL_R * max(sx, sy)
        closest_x = np.clip(cx, bx_lo, bx_hi - 1)
        closest_y = np.clip(cy, by_lo, by_hi - 1)
        disc = ((closest_x - cx) ** 2 + (closest_y - cy) ** 2) <= (r + 1) ** 2
        mask |= disc

    if include_tread:
        tx0, ty0 = _TREAD_X0 * sx, _TREAD_Y0 * sy
        tx1, ty1 = _TREAD_X1 * sx, _TREAD_Y1 * sy
        tread = (bx_hi > tx0) & (bx_lo < tx1)
        tread = tread[None, :] & ((by_hi > ty0) & (by_lo < ty1))
        mask |= tread

    if include_sidewall:
        sx0, sy0 = _SWALL_X0 * sx, _SWALL_Y0 * sy
        sx1, sy1 = _SWALL_X1 * sx, _SWALL_Y1 * sy
        swall = (bx_hi > sx0) & (bx_lo < sx1)
        swall = swall[None, :] & ((by_hi > sy0) & (by_lo < sy1))
        mask |= swall

    return mask


def _parse_dds_header(buf: bytes):
    """Return (width, height, mip_count, fourcc) from a DDS file."""
    if len(buf) < 128 or buf[:4] != b"DDS ":
        return None
    height = struct.unpack("<I", buf[12:16])[0]
    width = struct.unpack("<I", buf[16:20])[0]
    flags = struct.unpack("<I", buf[8:12])[0]
    mip_count = struct.unpack("<I", buf[28:32])[0]
    if not (flags & DDSD_MIPMAPCOUNT):
        mip_count = 1
    fourcc = buf[84:88]
    return width, height, max(1, mip_count), fourcc


def patch_tyre_blocks(
    new_bytes: bytes,
    base_bytes: bytes,
    *,
    include_disc: bool = True,
    include_tread: bool = True,
    include_sidewall: bool = True,
) -> bytes:
    """Restore byte-identical tyre blocks in `new_bytes` from `base_bytes`.

    Both arguments must be DXT5-encoded DDS files of the same size and
    mip layout.  If they disagree on either, the original `new_bytes`
    is returned unchanged (fail-safe -- never corrupts output).

    Individual region toggles let callers protect just the rubber
    (tread + sidewall) while leaving the wheel disc paintable -- for
    skins that deliberately overpaint the disc with an outer ring.
    """
    new_hdr = _parse_dds_header(new_bytes)
    base_hdr = _parse_dds_header(base_bytes)
    if new_hdr is None or base_hdr is None:
        return new_bytes
    if new_hdr != base_hdr:
        # Mip count or dims differ -- bail.
        return new_bytes
    if new_hdr[3] != b"DXT5":
        return new_bytes
    if len(new_bytes) != len(base_bytes):
        return new_bytes

    width, height, mip_count, _ = new_hdr
    out = bytearray(new_bytes)
    offset = 128

    for lvl in range(mip_count):
        w = max(1, width >> lvl)
        h = max(1, height >> lvl)
        nbx = (w + 3) // 4
        nby = (h + 3) // 4
        level_bytes = nbx * nby * 16

        mask = _block_mask_for_level(
            w, h,
            include_disc=include_disc,
            include_tread=include_tread,
            include_sidewall=include_sidewall,
        )
        # mask shape is (nby, nbx).  Flatten to row-major block order.
        block_idx = np.flatnonzero(mask.ravel())
        for idx in block_idx:
            blk_off = offset + int(idx) * 16
            out[blk_off:blk_off + 16] = base_bytes[blk_off:blk_off + 16]

        offset += level_bytes
        if offset >= len(new_bytes):
            break

    return bytes(out)
