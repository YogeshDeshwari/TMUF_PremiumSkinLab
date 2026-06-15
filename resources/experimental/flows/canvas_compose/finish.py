"""MaterialFinish -- the uniform-alpha values that actually render on TMNF.

In TMNF Stadium, the Diffuse alpha is the per-pixel **finish / specular
reflection** map (NOT transparency).  Higher alpha = more environment
reflection mixed into the surface paint; lower alpha = more matte.

CRITICAL CAVEAT about alpha=0 (audited and re-confirmed 2026-05-20):

The TMNF Stadium STOCK shader (driven by the stock CH_2026 ``MainBody
.Solid.Gbx`` mesh that our pipeline ships with) renders Diffuse
alpha=0 as **flat black across the entire body**, regardless of the
RGB content underneath.  This was first observed with Aurora v2
(canvas-mean luminance 106 + alpha=0 -> in-game black) and re-
confirmed in-game with the Tron BlackCyan_Reactor build at alpha=0
(body went pitch black even though the RGB canvas contained bright
cyan strokes at score > 300).

Misleading reference -- DO NOT REPEAT THIS MISTAKE:
Several MINA-TM community skins (``Deep-Galaxy``, ``Liquicity``,
``Summer-2024``) ship Diffuse.dds with **uniform alpha=0** AND
render vibrant in-game.  Inspection of the zip contents shows the
critical confound: those skins **also ship a custom
``MainBody.Solid.Gbx`` + ``MainBodyHigh.Solid.Gbx``** that bind a
different shader / material configuration.  Their alpha=0 evidence
is NOT transferable to our pipeline (which only ships DDS textures
on top of the stock car mesh).

Bottom line for our pipeline:
* Lowest safe global Diffuse alpha = 100 (``MATTE``).
* Per-pixel alpha=0 may be safe in small accent regions (the engine
  appears to fall back to neighbour-block colour when only a tiny
  fraction of a 4x4 BC3 block has alpha=0), but global alpha=0 is
  NOT safe.  Treat ``PURE_MATTE = 0`` as **experimental** -- use
  only via per-pixel selective overrides on small accent strokes
  inside ``selective_finish_on_color`` / ``selective_finish_on_hue_score``,
  never as the global ``set_finish`` value, until/unless a custom
  Gbx is also shipped.

Quick reference (all values verified safe as global finish):
    PURE_MATTE = 0   - **EXPERIMENTAL.**  Safe ONLY when applied via
                       per-pixel selective overrides on small accent
                       regions, NEVER as the global ``set_finish``
                       value.  Setting the whole Diffuse to alpha=0
                       on our pipeline renders the body flat black
                       when the body RGB is also dark (the Aurora v1
                       postmortem: dark RGB + alpha=0 = no env
                       reflection to lift it).  MINA's alpha=0 skins
                       avoid this because they paint bright RGB
                       across the canvas + ship a custom
                       ``MainBody.Solid.Gbx``.
    NEON       = 16  - Community-validated "bright pixels glow"
                       value (centre of the ``0x10 - 0x20`` range
                       in TMNF_SKINNING_NOTES "Finish values that
                       work" table).  Use SELECTIVELY on bright
                       accent strokes (neon cyan / magenta / yellow
                       on a glossier body): the matte makes those
                       pixels reflect almost no environment, so the
                       saturated RGB renders true regardless of
                       Stadium lighting.  Closest practical match
                       to the alpha=0 wheel-rim look for accents.
    DEEP_MATTE = 50  - Halfway between NEON and MATTE; matte enough
                       that paint pops, but still picks up a bit of
                       env reflection so dark RGB doesn't go black.
                       Good global value for full-body matte themes.
    MATTE      = 100 - Mild specular, mostly matte.  Lowest safe
                       value for global ``set_finish``.  Good for
                       poster-graphic designs with 2-3 sharp colours.
    DEFAULT    = 113 - The CH_2026 template default, balanced gloss.
                       Used by handpainted_pack and the Fallen-leaves
                       / Winter / KACKY-style community references.
    WET        = 114 - One notch glossier than default; oil / wet
                       marble look.  Used by DeepOcean.
    GLOSS      = 127 - Semi-reflective.  Premium / luxury palettes
                       (black marble + gold, royal blue + chrome).
    CHROME     = 255 - Maximum specular.  Mirror-finish themes.
                       Use for body where surface presence matters,
                       and pair with selective DEEP_MATTE on accent
                       strokes that need to stay saturated under
                       bright Stadium lighting.
"""
from __future__ import annotations

from enum import IntEnum


class MaterialFinish(IntEnum):
    PURE_MATTE = 0      # see module docstring -- experimental, accent-only
    NEON       = 16     # bright accent strokes glow (community 0x10-0x20)
    DEEP_MATTE = 50     # halfway matte; safe global value for matte themes
    MATTE      = 100    # lowest safe value for global set_finish
    DEFAULT    = 113
    WET        = 114
    GLOSS      = 127
    CHROME     = 255


FINISH_VALUES = {f.name: int(f) for f in MaterialFinish}
