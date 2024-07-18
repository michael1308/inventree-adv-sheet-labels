"""
Label printing plugin which supports printing multiple labels on a single page 
arranged according to standard label sheets.
"""

import logging
import math
import random

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _

import weasyprint
from rest_framework import serializers

import report.helpers
from plugin import InvenTreePlugin
from plugin.mixins import LabelPrintingMixin, SettingsMixin
from report.models import LabelOutput, LabelTemplate

from .layouts import LAYOUTS, LAYOUT_SELECT_OPTIONS


_log = logging.getLogger('inventree')

_plugin_instance: "AdvancedLabelSheetPlugin" = ...


def get_default_layout() -> str:
    """
    Fetches the default layout setting from the database to show in form.
    """
    option: str = ""
    if _plugin_instance is not ...: 
        option = _plugin_instance.get_setting("DEFAULT_LAYOUT")
        _log.warn(f"Using default layout from settings: {option}")
    else:
        option = LAYOUT_SELECT_OPTIONS[0][0]    # use the first one if there is no other option (is)
    return option

def get_default_skip() -> int:
    """
    Fetches the default labels skip count from the database which was stored
    there the last time a printing job finished to indicate the next available label
    positions.
    """
    skip: int = 0
    if _plugin_instance is not ...: 
        skip = _plugin_instance.get_setting("LABEL_SKIP_COUNTER")
    return skip


class AdvancedLabelPrintingOptionsSerializer(serializers.Serializer):
    """Custom printing options for the advanced label sheet plugin."""

    sheet_layout = serializers.ChoiceField(
        label='Sheet Layout',
        help_text='Page size and label arrangement',
        choices=LAYOUT_SELECT_OPTIONS,
        default=get_default_layout,
    )

    count = serializers.IntegerField(
        label='Number of Labels',
        help_text='Number of labels to print for each kind',
        min_value=0,
        default=0,
    )

    skip = serializers.IntegerField(
        label='Skip Labels',
        help_text='Number of labels to skip from the top left',
        min_value=0,
        default=get_default_skip,
    )

    border = serializers.BooleanField(
        label='Border',
        help_text='Whether to print a border around each label (useful for testing)',
        default=False,
    )


class AdvancedLabelSheetPlugin(LabelPrintingMixin, SettingsMixin, InvenTreePlugin):
    """Plugin for advanced label sheet printing.

    This plugin arrays multiple labels onto a single larger sheet,
    and returns the resulting PDF file.
    """

    NAME = 'AdvancedLabelSheet'
    TITLE = 'Advanced Label Sheet Printer'
    DESCRIPTION = 'Arrays multiple labels onto single, standard layout label sheets with advanced layout options'
    VERSION = '1.0.0'
    AUTHOR = 'InvenTree contributors & melektron'

    BLOCKING_PRINT = True

    SETTINGS = {
        "DEFAULT_LAYOUT": {
            "name": "Default Sheet Layout",
            "description": "The default sheet layout selection when printing labels",
            "choices": LAYOUT_SELECT_OPTIONS,
            "default": LAYOUT_SELECT_OPTIONS[0][0],
            "required": True
        },
        "LABEL_SKIP_COUNTER": {
            "name": "Label Skip Counter",
            "description": "Global counter for auto-incrementing the default amount of labels to skip when printing. If page is full, this wraps back to zero accordingly.",
            "default": 0,
            "validator": [
                int,
                MinValueValidator(0)
            ],
            "hidden": True  # maybe shoudl actually show this for manual reset? but for now I'll not show it
        }
    }

    PrintingOptionsSerializer = AdvancedLabelPrintingOptionsSerializer

    def __init__(self):
        _log.warn("Initializing Advanced Sheet Label Plugin")
        super().__init__()
        # save instance so serializers can access it.
        global _plugin_instance
        _plugin_instance = self

    def print_labels(
        self, label: LabelTemplate, output: LabelOutput, items: list, request, **kwargs
    ):
        """Handle printing of the provided labels.

        Note that we override the entire print_labels method for this plugin.
        """
        printing_options = kwargs['printing_options']

        # Extract page size for the label sheet
        page_size_code = printing_options.get('page_size', 'A4')
        landscape = printing_options.get('landscape', False)
        border = printing_options.get('border', False)
        skip = int(printing_options.get('skip', 0))

        # Extract size of page
        page_size = report.helpers.page_size(page_size_code)
        page_width, page_height = page_size

        if landscape:
            page_width, page_height = page_height, page_width

        # Calculate number of rows and columns
        n_cols = math.floor(page_width / label.width)
        n_rows = math.floor(page_height / label.height)
        n_cells = n_cols * n_rows

        if n_cells == 0:
            raise ValidationError(_('Label is too large for page size'))

        # Prepend the required number of skipped null labels
        items = [None] * skip + list(items)

        n_labels = len(items)

        # Data to pass through to each page
        document_data = {
            'border': border,
            'landscape': landscape,
            'page_width': page_width,
            'page_height': page_height,
            'label_width': label.width,
            'label_height': label.height,
            'n_labels': n_labels,
            'n_pages': math.ceil(n_labels / n_cells),
            'n_cols': n_cols,
            'n_rows': n_rows,
        }

        pages = []

        idx = 0

        while idx < n_labels:
            if page := self.print_page(
                label, items[idx : idx + n_cells], request, **document_data
            ):
                pages.append(page)

            idx += n_cells

        if len(pages) == 0:
            raise ValidationError(_('No labels were generated'))

        # Render to a single HTML document
        html_data = self.wrap_pages(pages, **document_data)

        # Render HTML to PDF
        html = weasyprint.HTML(string=html_data)
        document = html.render().write_pdf()

        output.output = ContentFile(document, 'labels.pdf')
        output.progress = 100
        output.complete = True
        output.save()

    def print_page(self, label: LabelTemplate, items: list, request, **kwargs):
        """Generate a single page of labels.

        For a single page, generate a simple table grid of labels.
        Styling of the table is handled by the higher level label template

        Arguments:
            label: The LabelTemplate object to use for printing
            items: The list of database items to print (e.g. StockItem instances)
            request: The HTTP request object which triggered this print job

        Kwargs:
            n_cols: Number of columns
            n_rows: Number of rows
        """
        n_cols = kwargs['n_cols']
        n_rows = kwargs['n_rows']

        # Generate a table of labels
        html = """<table class='label-sheet-table'>"""

        for row in range(n_rows):
            html += "<tr class='label-sheet-row'>"

            for col in range(n_cols):
                # Cell index
                idx = row * n_cols + col

                if idx >= len(items):
                    break

                html += f"<td class='label-sheet-cell label-sheet-row-{row} label-sheet-col-{col}'>"

                # If the label is empty (skipped), render an empty cell
                if items[idx] is None:
                    html += """<div class='label-sheet-cell-skip'></div>"""
                else:
                    try:
                        # Render the individual label template
                        # Note that we disable @page styling for this
                        cell = label.render_as_string(
                            items[idx], request, insert_page_style=False
                        )
                        html += cell
                    except Exception as exc:
                        _log.exception('Error rendering label: %s', str(exc))
                        html += """
                        <div class='label-sheet-cell-error'></div>
                        """

                html += '</td>'

            html += '</tr>'

        html += '</table>'

        return html

    def wrap_pages(self, pages, **kwargs):
        """Wrap the generated pages into a single document."""
        border = kwargs['border']

        page_width = kwargs['page_width']
        page_height = kwargs['page_height']

        label_width = kwargs['label_width']
        label_height = kwargs['label_height']

        n_rows = kwargs['n_rows']
        n_cols = kwargs['n_cols']

        inner = ''.join(pages)

        # Generate styles for individual cells (on each page)
        cell_styles = []

        for row in range(n_rows):
            cell_styles.append(
                f"""
            .label-sheet-row-{row} {{
                top: {row * label_height}mm;
            }}
            """
            )

        for col in range(n_cols):
            cell_styles.append(
                f"""
            .label-sheet-col-{col} {{
                left: {col * label_width}mm;
            }}
            """
            )

        cell_styles = '\n'.join(cell_styles)

        return f"""
        <head>
            <style>
                @page {{
                    size: {page_width}mm {page_height}mm;
                    margin: 0mm;
                    padding: 0mm;
                }}

                .label-sheet-table {{
                    page-break-after: always;
                    table-layout: fixed;
                    width: {page_width}mm;
                    border-spacing: 0mm 0mm;
                }}

                .label-sheet-cell-error {{
                    background-color: #F00;
                }}

                .label-sheet-cell {{
                    border: {'1px solid #000;' if border else '0mm;'}
                    width: {label_width}mm;
                    height: {label_height}mm;
                    padding: 0mm;
                    position: absolute;
                }}

                {cell_styles}

                body {{
                    margin: 0mm !important;
                }}
            </style>
        </head>
        <body>
            {inner}
        </body>
        </html>
        """
