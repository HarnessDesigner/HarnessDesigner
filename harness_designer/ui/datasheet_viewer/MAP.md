## FILES

#### __init__.py

Re-exports the module as `_viewer` only; no public symbols of its own.

#### viewer.py

`ImageViewer(QtWidgets.QWidget)` -- `__init__(self, parent, img: str)`; a pan/zoom viewer for a part's datasheet/CAD preview image, built on `QtPdf`/`QtPdfWidgets` so it can show either a plain raster image or a PDF page through the same widget. Handles its own `mousePressEvent` for drag-panning. Distinct from `ui/widgets/cad_datasheet_ctrl.py`'s `CADDatasheetCtrl`/`CADDatasheetPreviewCtrl` (the property-grid-embedded preview used by `ui/prop_ctrls/datasheet_cad_prop.py`) -- this one is the standalone full-size viewer dock/window rather than an inline property control.
