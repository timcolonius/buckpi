from html import escape

import panel as pn

from buckpi import SymbolError, UnitError, analyze_options, symbol_latex

pn.extension("katex", sizing_mode="stretch_width")

pn.config.raw_css.append("""
:root { --buck-ink: #17212b; --buck-blue: #176b87; }
body { background: #f7f8f6; }
.bkpi-hero { padding: 22px 26px; border-left: 6px solid #d8a529; background: linear-gradient(120deg,#e7f2f3,#f8f5ea); border-radius: 10px; }
.bkpi-hero h1 { color:#17212b; margin:0 0 4px; font-size:32px; }
.bkpi-hero p { color:#53606a; margin:0; }
.bkpi-card { background:white; border:1px solid #d9deda; border-radius:10px; padding:16px 18px; }
.bkpi-error { background:#fff0ee; border-left:4px solid #b44335; padding:12px 16px; border-radius:6px; }
""")

UNIT_TIP = (
    "Use any Pint-recognized unit name or abbreviation, including SI, US customary, and CGS. "
    "Combine units with * or /, use ^ or ** for powers, and use parentheses for grouping. "
    "Examples: kg/m^3, N/m, Pa*s, slug/ft^3, lbf, psi, and mph. Prefixes, plurals, and mixed "
    "unit systems are allowed. BuckPi uses dimensionality only; it does not convert numerical values."
)
VARIABLE_TIP = (
    r"Enter ordinary text or LaTeX-style notation. Examples: U, \rho, c_p, U_{\infty}, and \Delta p. "
    "Greek commands, subscripts, and superscripts are supported."
)
REQUIRE_TIP = (
    "By default BuckPi shows every admissible basis of independent Pi groups. Check one or more "
    "boxes to restrict the table to bases in which each selected variable appears with exponent 1 "
    "in a separate Pi group."
)

EDITED_EXAMPLE_STYLESHEET = """
select, .bk-input { color: #9ca3af !important; font-style: italic !important; }
"""
PREVIEW_STYLE = {
    "color": "#176b87",
    "padding": "7px 8px",
    "min-height": "38px",
}
PREVIEW_ERROR_STYLE = {
    "color": "#b44335",
    "padding": "7px 8px",
    "min-height": "38px",
}
HEADER_STYLE = {
    "background": "#176b87",
    "color": "white",
    "padding": "10px 12px",
    "border": "1px solid #cfd8d8",
    "font-weight": "600",
}
OPTION_STYLE = {
    "background": "#eef6f7",
    "padding": "10px 12px",
    "border": "1px solid #cfd8d8",
    "font-weight": "600",
}
MATH_CELL_STYLE = {
    "background": "white",
    "padding": "10px 12px",
    "border": "1px solid #cfd8d8",
    "min-height": "48px",
}

EXAMPLES = {
    "Sphere volume": [("V", "m^3"), ("R", "m")],
    "Pendulum": [("T", "s"), ("L", "m"), ("g", "m/s^2")],
    "Drag force": [
        ("F", "N"), (r"\rho", "kg/m^3"), ("U", "m/s"), ("L", "m"),
        (r"\mu", "Pa*s"),
    ],
    "Surface gravity waves": [
        ("c_p", "m/s"), (r"\lambda", "m"), ("g", "m/s^2"), ("h", "m"),
        (r"\rho", "kg/m^3"), (r"\sigma", "N/m"),
    ],
}

rows = []
loading_example = False

example = pn.widgets.Select(
    name="Load an example", options=list(EXAMPLES), value="Pendulum", width=280
)
calculate = pn.widgets.Button(
    name="Find dimensionless groups", button_type="primary", width=250
)
clear = pn.widgets.Button(name="Clear", button_type="light", width=90)
add = pn.widgets.Button(name="+ Add row", button_type="light", width=110)
table = pn.Column(sizing_mode="stretch_width")
result = pn.Column(sizing_mode="stretch_width")


def mark_example_edited(event=None):
    if not loading_example:
        example.stylesheets = [EDITED_EXAMPLE_STYLESHEET]
        if result.objects:
            result.styles = {
                "opacity": "0.35",
                "filter": "grayscale(1)",
                "transition": "opacity 120ms ease",
            }
            calculate.name = "Recalculate dimensionless groups"
            calculate.button_type = "warning"


def update_preview(event, preview):
    if not event.new.strip():
        preview.object = r"$\text{preview}$"
        preview.styles = PREVIEW_STYLE | {"color": "#9ca3a7"}
        return
    try:
        preview.object = "$" + symbol_latex(event.new) + "$"
        preview.styles = PREVIEW_STYLE
    except SymbolError:
        preview.object = r"$\text{invalid}$"
        preview.styles = PREVIEW_ERROR_STYLE


def make_row(name_value="", unit_value=""):
    index = len(rows) + 1
    name = pn.widgets.TextInput(
        name=f"Variable {index}", value=name_value, placeholder=r"e.g. \rho", width=150
    )
    unit = pn.widgets.TextInput(
        name="Dimensions / units",
        value=unit_value,
        placeholder="e.g. kg/m^3",
        width=240,
    )
    require = pn.widgets.Checkbox(name="", value=False, width=165, align="center")
    preview_text = "$" + symbol_latex(name_value) + "$" if name_value else r"$\text{preview}$"
    preview = pn.pane.LaTeX(
        preview_text,
        renderer="katex",
        width=105,
        height=42,
        styles=PREVIEW_STYLE if name_value else PREVIEW_STYLE | {"color": "#9ca3a7"},
    )
    name.param.watch(lambda event, pane=preview: update_preview(event, pane), "value")
    for widget in (name, unit, require):
        widget.param.watch(mark_example_edited, "value")
    row_layout = pn.Row(name, unit, require, preview, sizing_mode="stretch_width")
    return name, unit, require, preview, row_layout


def refresh_table():
    variable_heading = pn.Row(
        pn.pane.Markdown("**Variable**", width=120, margin=0),
        pn.widgets.TooltipIcon(value=VARIABLE_TIP, width=20, margin=0),
        width=150,
        margin=(5, 10),
    )
    unit_heading = pn.Row(
        pn.pane.Markdown("**Dimensions / units**", width=210, margin=0),
        pn.widgets.TooltipIcon(value=UNIT_TIP, width=20, margin=0),
        width=240,
        margin=(5, 10),
    )
    exponent_heading = pn.Row(
        pn.pane.Markdown("**Require exponent = 1**", width=135, margin=0),
        pn.widgets.TooltipIcon(value=REQUIRE_TIP, width=20, margin=0),
        width=165,
        margin=(5, 10),
    )
    heading = pn.Row(
        variable_heading,
        unit_heading,
        exponent_heading,
        pn.pane.Markdown("**Preview**", width=105),
        sizing_mode="stretch_width",
    )
    table.objects = [heading, *[row[4] for row in rows], add]


def load_example(event=None):
    global loading_example
    loading_example = True
    rows.clear()
    for name_value, unit_value in EXAMPLES[example.value]:
        rows.append(make_row(name_value, unit_value))
    refresh_table()
    example.stylesheets = []
    loading_example = False
    calculate_groups()


def add_row(event=None):
    rows.append(make_row())
    refresh_table()
    mark_example_edited()


def result_table(answers):
    answer = answers[0]
    summary = pn.pane.HTML(
        f'<h2>Result</h2><p>{len(answer.names)} variables, rank {answer.rank}: '
        f'<strong>{answer.group_count} independent dimensionless group(s)</strong>, shown in '
        f'<strong>{len(answers)} admissible form(s)</strong>.</p>'
    )
    header = pn.Row(
        pn.pane.HTML("Option", width=80, styles=HEADER_STYLE),
        *[
            pn.pane.HTML(f"&Pi;<sub>{i}</sub>", width=220, styles=HEADER_STYLE)
            for i in range(1, answer.group_count + 1)
        ],
    )
    option_rows = []
    for row_number, option in enumerate(answers, 1):
        cells = [
            pn.pane.LaTeX(
                "$" + group.expression_latex(list(option.names)) + "$",
                renderer="katex",
                width=220,
                height=52,
                styles=MATH_CELL_STYLE,
            )
            for group in option.groups
        ]
        option_rows.append(
            pn.Row(
                pn.pane.HTML(str(row_number), width=80, styles=OPTION_STYLE),
                *cells,
            )
        )
    note = pn.pane.HTML(
        "<small>Each row is a complete independent set. Equivalent rows differ only in the chosen basis.</small>"
    )
    grid = pn.Column(header, *option_rows, styles={"overflow-x": "auto"})
    return pn.Column(summary, grid, note, styles={"background": "white", "border": "1px solid #d9deda", "border-radius": "10px", "padding": "16px 18px"})


def calculate_groups(event=None):
    variables = [
        (name.value, unit.value)
        for name, unit, _, _, _ in rows
        if name.value.strip() or unit.value.strip()
    ]
    preferred = [
        name.value
        for name, _, require, _, _ in rows
        if require.value and name.value.strip()
    ]
    try:
        if any(not name.strip() or not unit.strip() for name, unit in variables):
            raise ValueError("Each row needs both a variable name and a unit expression")
        answers = analyze_options(variables, preferred)
        result.objects = [result_table(answers)]
    except (ValueError, UnitError, SymbolError) as exc:
        result.objects = [
            pn.pane.HTML(
                f'<div class="bkpi-error"><strong>Check the input:</strong> {escape(str(exc))}</div>'
            )
        ]
    result.styles = {}
    calculate.name = "Find dimensionless groups"
    calculate.button_type = "primary"


def clear_rows(event=None):
    for name, unit, require, _, _ in rows:
        name.value = ""
        unit.value = ""
        require.value = False
    result.objects = []
    result.styles = {}
    calculate.name = "Find dimensionless groups"
    calculate.button_type = "primary"
    mark_example_edited()


example.param.watch(load_example, "value")
calculate.on_click(calculate_groups)
clear.on_click(clear_rows)
add.on_click(add_row)

app = pn.Column(
    pn.pane.HTML(
        '<div class="bkpi-hero"><h1>BuckPi</h1><p>Dimensional analysis using the Buckingham &Pi; theorem</p></div>'
    ),
    pn.Row(example, pn.Spacer(width=12), clear),
    pn.pane.HTML(
        '<div class="bkpi-card"><p>Enter each variable using ordinary text or LaTeX-style notation such as '
        '<code>\\rho</code>, <code>c_p</code>, <code>U_{\\infty}</code>, or <code>\\Delta p</code>. '
        'Enter units separately using expressions such as <code>m/s</code>, <code>kg/m^3</code>, '
        '<code>Pa*s</code>, or <code>N/m</code>. By default, every admissible set of &Pi; groups is shown.</p></div>'
    ),
    table,
    calculate,
    result,
    pn.pane.Markdown(
        "Exact rational linear algebra runs locally in your browser. No data is uploaded.  \n"
        "Tim Colonius · California Institute of Technology"
    ),
    max_width=920,
    margin=(20, 0),
)

load_example()
app.servable(title="BuckPi — Dimensional Analysis")
