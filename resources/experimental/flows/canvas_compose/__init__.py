"""canvas_compose -- canvas-first poster painting for TMNF stadium-car skins.

This package implements the architecture revealed by forensic study of 15+
community handpainted skins by MINA_TM and SparkyTM (May 2026).  The core
insight: MINA paints a flat 2D POSTER on the 2048x2048 PSD canvas without
respecting UV island boundaries; the UV unwrap is treated as an OUTPUT
that determines what shows on the car, not as a constraint on the
composition.

Public API
==========
- CanvasComposer       (composer.CanvasComposer)
- MaterialFinish enum  (finish.MaterialFinish)
- Motif protocol       (motifs.Motif)
- Concrete motifs:
    Gradient, CarbonFiber, BrushStreaks, Galaxy, MarbleSwirl (see motifs.py)

Typical usage:
    from skins.canvas_compose import CanvasComposer, MaterialFinish
    from skins.canvas_compose.motifs import BrushStreaks, Galaxy, Gradient

    comp = CanvasComposer(theme_name="MyAurora")
    comp.paint(Gradient(stops=[...]))
    comp.paint(Galaxy(...))
    comp.paint(BrushStreaks(palette=[...], direction="vertical"))
    comp.apply_finish(MaterialFinish.DEFAULT)
    comp.save()
"""
from .finish import MaterialFinish, FINISH_VALUES
from .composer import CanvasComposer

__all__ = ["CanvasComposer", "MaterialFinish", "FINISH_VALUES"]
