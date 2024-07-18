"""
ELEKTRON (c) 2024 - now
Written by melektron
www.elektron.work
18.07.24 22:42

List of sheet label paper layouts
"""

import dataclasses


@dataclasses.dataclass
class PaperSize:
    display_name: str   # paper size display name (e.g. "A4")
    width: float        # mm
    height: float       # mm


@dataclasses.dataclass
class SheetLayout:
    display_name: str
    sheet_size: PaperSize
    label_width: float      # mm
    label_height: float     # mm
    columns: int
    rows: int
    column_spacing: float   # mm
    row_spacing: float      # mm
    corner_radius: float | None         # mm, None means sharp corners
    spacing_top: float | None = None    # None means automatic centering
    spacing_left: float | None = None   # None means automatic centering


PAPER_SIZES = {
    "A4": PaperSize("A4", 210, 297)
}

LAYOUTS = {
    "4780": SheetLayout(
        display_name="4780",
        sheet_size=PAPER_SIZES["A4"],
        label_width=48.5,
        label_height=25.4,
        columns=4,
        rows=10,
        column_spacing=0,
        row_spacing=0,
        corner_radius=0
    ),
    "4737": SheetLayout(
        display_name="4737",
        sheet_size=PAPER_SIZES["A4"],
        label_width=63.5,
        label_height=29.6,
        columns=3,
        rows=9,
        column_spacing=2.54,
        row_spacing=0,
        corner_radius=2.54
    )
}

LAYOUT_SELECT_OPTIONS = [
    (
        index, 
        f"{layout.display_name} ({layout.sheet_size.display_name}, {layout.label_width}mm x {layout.label_height}mm, {layout.columns} columns x {layout.rows} rows, {'rounded' if layout.corner_radius is not None else 'straight'})"
    ) 
    for index, layout in LAYOUTS.items()
]