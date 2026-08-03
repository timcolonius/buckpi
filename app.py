from html import escape

import panel as pn

from buckpi import SymbolError, UnitError, analyze_options, symbol_latex

pn.extension("katex", sizing_mode="stretch_width")

pn.config.raw_css.append("""
:root {
  --buck-navy: #0b2d4d;
  --buck-blue: #126a9c;
  --buck-mid: #4e91b8;
  --buck-soft: #dcecf5;
  --buck-pale: #f3f4f6;
  --buck-line: #b9d4e4;
}
body { background: var(--buck-pale); color: var(--buck-navy); }
.bkpi-banner {
  overflow: hidden;
  border: 1px solid var(--buck-line);
  border-radius: 8px;
  background: white;
  box-shadow: 0 5px 18px rgba(11, 45, 77, 0.10);
}
.bkpi-banner-meta {
  padding: 6px 20px;
  background: var(--buck-soft);
  color: #416b86;
  font-size: 11px;
  letter-spacing: 0.05em;
  text-align: right;
}
.bkpi-brand {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 18px 24px 20px;
}
.bkpi-mark {
  display: flex;
  align-items: center;
  color: var(--buck-navy);
  font-family: "STIX Two Math", "Cambria Math", Georgia, serif;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
}
.bkpi-mark .bkpi-pi { font-style: italic; }
.bkpi-mark .bkpi-pi { color: #0e5f91; font-size: 42px; }
.bkpi-brand h1 { color: var(--buck-navy); margin: 0; font-size: 34px; line-height: 1; }
.bkpi-brand p { color: #52738a; margin: 5px 0 0; font-size: 14px; }
.bkpi-intro {
  background: #e8f3f9;
  border-left: 5px solid var(--buck-blue);
  border-radius: 7px;
  color: #244f6b;
  line-height: 1.55;
  padding: 13px 18px;
}
.bkpi-intro p { margin: 0; }
.bkpi-error { background:#fff5f5; border-left:4px solid #b42318; color:#b42318; padding:12px 16px; border-radius:6px; }
@media (max-width: 620px) {
  .bkpi-brand { gap: 14px; padding: 16px; }
  .bkpi-mark { transform: scale(0.86); transform-origin: left center; margin-right: -8px; }
  .bkpi-brand h1 { font-size: 29px; }
}
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
select, .bk-input { color: #7794a8 !important; font-style: italic !important; }
"""
PREVIEW_STYLE = {
    "color": "#126a9c",
    "padding": "7px 8px",
    "min-height": "38px",
}
PREVIEW_ERROR_STYLE = {
    "color": "#174f75",
    "padding": "7px 8px",
    "min-height": "38px",
}
HEADER_STYLE = {
    "background": "#126a9c",
    "color": "white",
    "padding": "10px 12px",
    "border": "1px solid #a9cadc",
    "font-weight": "600",
}
OPTION_STYLE = {
    "background": "#e3f0f7",
    "padding": "10px 12px",
    "border": "1px solid #b9d4e4",
    "font-weight": "600",
}
MATH_CELL_STYLE = {
    "background": "white",
    "padding": "10px 12px",
    "border": "1px solid #b9d4e4",
    "box-sizing": "border-box",
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
add = pn.widgets.Button(name="+ Add row", button_type="light", width=110)
table = pn.Column(sizing_mode="stretch_width")
result = pn.Column(sizing_mode="stretch_width")


def mark_example_edited(event=None):
    if not loading_example:
        example.stylesheets = [EDITED_EXAMPLE_STYLESHEET]
        calculate_groups()


def update_preview(event, preview):
    if not event.new.strip():
        preview.object = r"$\text{preview}$"
        preview.styles = PREVIEW_STYLE | {"color": "#7794a8"}
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
        name=f"Variable {index}",
        value=name_value,
        value_input=name_value,
        placeholder=r"e.g. \rho",
        width=150,
    )
    unit = pn.widgets.TextInput(
        name="Dimensions / units",
        value=unit_value,
        value_input=unit_value,
        placeholder="e.g. kg/m^3",
        width=240,
    )
    require = pn.widgets.Checkbox(name="", value=False, width=20, margin=0)
    require_cell = pn.Row(
        require,
        width=165,
        height=42,
        margin=(5, 10),
        styles={"display": "flex", "justify-content": "center", "align-items": "center"},
    )
    remove = pn.widgets.Button(name="Remove", button_type="light", width=80, align="center")
    preview_text = "$" + symbol_latex(name_value) + "$" if name_value else r"$\text{preview}$"
    preview = pn.pane.LaTeX(
        preview_text,
        renderer="katex",
        width=105,
        height=42,
        styles=PREVIEW_STYLE if name_value else PREVIEW_STYLE | {"color": "#7794a8"},
    )
    name.param.watch(lambda event, pane=preview: update_preview(event, pane), "value_input")
    name.param.watch(mark_example_edited, "value_input")
    unit.param.watch(mark_example_edited, "value_input")
    require.param.watch(mark_example_edited, "value")
    remove.on_click(lambda event, target=name: remove_row(target))
    row_layout = pn.Row(name, unit, require_cell, preview, remove, sizing_mode="stretch_width")
    return name, unit, require, preview, remove, row_layout


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
        pn.Spacer(width=80, margin=(5, 10)),
        sizing_mode="stretch_width",
    )
    table.objects = [heading, *[row[5] for row in rows], add]


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


def remove_row(target):
    rows[:] = [row for row in rows if row[0] is not target]
    refresh_table()
    mark_example_edited()


def result_table(answers):
    answer = answers[0]
    pi_width = min(320, max(230, 780 // max(answer.group_count, 1)))
    grid_width = 80 + answer.group_count * pi_width
    summary = pn.pane.HTML(
        f'<h2>Result</h2><p>{len(answer.names)} variables, rank {answer.rank}: '
        f'<strong>{answer.group_count} independent dimensionless group(s)</strong>, shown in '
        f'<strong>{len(answers)} admissible form(s)</strong>.</p>'
    )
    option_header = pn.FlexBox(
        pn.pane.HTML("Option", margin=0, styles={"color": "white", "text-align": "center"}),
        width=80,
        height=42,
        sizing_mode="fixed",
        margin=0,
        align_items="center",
        justify_content="center",
        styles=HEADER_STYLE,
    )
    pi_headers = [
        pn.FlexBox(
            pn.pane.HTML(
                f"&Pi;<sub>{i}</sub>",
                margin=0,
                styles={"color": "white", "text-align": "center"},
            ),
            width=pi_width,
            height=42,
            sizing_mode="fixed",
            margin=0,
            align_items="center",
            justify_content="center",
            styles=HEADER_STYLE,
        )
        for i in range(1, answer.group_count + 1)
    ]
    header = pn.Row(
        option_header,
        *pi_headers,
        width=grid_width,
        sizing_mode=None,
        margin=0,
    )
    option_rows = []
    for row_number, option in enumerate(answers, 1):
        option_cell = pn.FlexBox(
            pn.pane.HTML(str(row_number), margin=0),
            width=80,
            height=86,
            sizing_mode="fixed",
            margin=0,
            align_items="center",
            justify_content="center",
            styles=OPTION_STYLE,
        )
        cells = [
            pn.FlexBox(
                pn.pane.LaTeX(
                    r"$\displaystyle " + group.expression_latex(list(option.names)) + "$",
                    renderer="katex",
                    sizing_mode="stretch_width",
                    margin=0,
                    styles={"font-size": "20px", "text-align": "center"},
                ),
                width=pi_width,
                height=86,
                sizing_mode="fixed",
                margin=0,
                align_items="center",
                justify_content="center",
                styles=MATH_CELL_STYLE,
            )
            for group in option.groups
        ]
        option_rows.append(
            pn.Row(
                option_cell,
                *cells,
                width=grid_width,
                sizing_mode=None,
                margin=0,
            )
        )
    note = pn.pane.HTML(
        "<small>Each row is a complete independent set. Equivalent rows differ only in the chosen basis.</small>"
    )
    grid = pn.Column(
        header,
        *option_rows,
        width=grid_width,
        sizing_mode=None,
        align="center",
        styles={"overflow-x": "auto"},
    )
    return pn.Column(
        summary,
        grid,
        note,
        sizing_mode="stretch_width",
        styles={
            "background": "white",
            "border": "1px solid #b9d4e4",
            "border-radius": "10px",
            "padding": "16px 18px",
        },
    )


def calculate_groups(event=None):
    variables = [
        (name.value_input, unit.value_input)
        for name, unit, _, _, _, _ in rows
        if name.value.strip() or unit.value.strip()
    ]
    preferred = [
        name.value_input
        for name, _, require, _, _, _ in rows
        if require.value and name.value_input.strip()
    ]
    try:
        if any(not name.strip() or not unit.strip() for name, unit in variables):
            raise ValueError("Each row needs both a variable name and a unit expression")
        answers = analyze_options(variables, preferred)
        result.objects = [result_table(answers)]
    except (ValueError, UnitError, SymbolError) as exc:
        result.objects = [
            pn.pane.HTML(
                f'<div class="bkpi-error"><strong>Error:</strong> {escape(str(exc))}</div>'
            )
        ]
    result.styles = {}


example.param.watch(load_example, "value")
add.on_click(add_row)

app = pn.Column(
    pn.pane.HTML(
        '<div class="bkpi-banner">'
        '<div class="bkpi-banner-meta">Tim Colonius &middot; Caltech</div>'
        '<div class="bkpi-brand">'
        '<div class="bkpi-mark" aria-label="Pi"><span class="bkpi-pi">&Pi;</span></div>'
        '<div><h1>BuckPi</h1><p>Dimensional analysis</p></div>'
        '</div></div>'
    ),
    pn.pane.HTML(
        '<div class="bkpi-intro"><p>BuckPi reveals the dimensionless structure of a physical problem. '
        'It applies the Buckingham &Pi; theorem to your variables and dimensions, then lists every '
        'admissible independent set of &Pi; groups. Start from an example or build your own problem below.</p></div>'
    ),
    pn.Row(example),
    table,
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
