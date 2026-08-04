from html import escape
import re

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
.bkpi-variable-group {
  position: relative;
  border: 1px solid var(--buck-line);
  border-radius: 8px;
  padding: 18px 12px 10px;
  margin-top: 12px;
}
.bkpi-variable-group::before {
  position: absolute;
  top: -0.72em;
  left: 14px;
  padding: 0 7px;
  background: white;
  color: var(--buck-blue);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
}
.bkpi-output-group::before { content: "Output"; }
.bkpi-input-group::before { content: "Input"; }
.bkpi-math-chip { transition: background-color 120ms ease, border-color 120ms ease; }
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
MATH_CELL_STYLE = {
    "background": "white",
    "padding": "10px 12px",
    "border": "1px solid #b9d4e4",
    "box-sizing": "border-box",
}
CARD_STYLES = {
    "background": "white",
    "border": "2px solid #126a9c",
    "border-radius": "10px",
    "padding": "10px 14px",
}
CHOICE_CHIP_ACTIVE_STYLES = {
    "position": "relative",
    "background": "#126a9c",
    "border": "1px solid #126a9c",
    "border-radius": "6px",
    "color": "white",
    "cursor": "pointer",
}
CHOICE_CHIP_INACTIVE_STYLES = {
    "position": "relative",
    "background": "#e8f3f9",
    "border": "1px solid #b9d4e4",
    "border-radius": "6px",
    "color": "#0b2d4d",
    "cursor": "pointer",
}


def repeating_choice_width(names):
    """Estimate the rendered math width without counting LaTeX command text."""
    if not names:
        return 74
    width = 24 + 12 * (len(names) - 1)
    for name in names:
        latex = symbol_latex(name)
        glyphs = re.sub(r"\\[A-Za-z]+", "x", latex)
        glyphs = re.sub(r"[{}_^\\\s]", "", glyphs)
        width += max(20, 10 * len(glyphs) + 10)
    return max(74, min(230, width))

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
next_row_id = 0

example = pn.widgets.Select(
    name="Load an example", options=list(EXAMPLES), value="Pendulum", width=280
)
add = pn.widgets.Button(name="+ Add input", button_type="light", width=110)
table = pn.Column(sizing_mode="stretch_width", margin=(0, 10, 16, 10))
result = pn.Column(sizing_mode="stretch_width", margin=(0, 10))


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


def make_row(name_value="", unit_value="", is_output=False):
    global next_row_id
    next_row_id += 1
    row_id = str(next_row_id)
    name = pn.widgets.TextInput(
        name="Output variable" if is_output else "Input variable",
        description=VARIABLE_TIP,
        value=name_value,
        value_input=name_value,
        placeholder=r"e.g. \rho",
        width=150,
    )
    unit = pn.widgets.TextInput(
        name="Dimensions / units",
        description=UNIT_TIP,
        value=unit_value,
        value_input=unit_value,
        placeholder="e.g. kg/m^3",
        width=240,
    )
    remove = None if is_output else pn.widgets.Button(
        name="Remove", button_type="light", width=80, align="center"
    )
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
    row_objects = [name, unit, preview]
    if remove is not None:
        remove.on_click(lambda event, target=row_id: remove_row(target))
        row_objects.append(remove)
    row_layout = pn.Row(*row_objects, sizing_mode="stretch_width")
    return row_id, name, unit, preview, remove, row_layout

def refresh_table():
    if not rows:
        table.objects = []
        return
    output_group = pn.Column(
        rows[0][5],
        css_classes=["bkpi-variable-group", "bkpi-output-group"],
    )
    input_group = pn.Column(
        *[row[5] for row in rows[1:]],
        add,
        css_classes=["bkpi-variable-group", "bkpi-input-group"],
    )
    variables_box = pn.Column(
        pn.pane.HTML("<h2>Variables</h2>"),
        output_group,
        input_group,
        styles=CARD_STYLES,
    )
    table.objects = [variables_box]


def load_example(event=None):
    global loading_example
    loading_example = True
    rows.clear()
    for index, (name_value, unit_value) in enumerate(EXAMPLES[example.value]):
        rows.append(make_row(name_value, unit_value, is_output=(index == 0)))
    refresh_table()
    example.stylesheets = []
    loading_example = False
    calculate_groups()


def add_row(event=None):
    rows.append(make_row())
    refresh_table()
    mark_example_edited()


def remove_row(target):
    if rows and rows[0][0] == target:
        return
    rows[:] = [row for row in rows if row[0] != target]
    refresh_table()
    mark_example_edited()


RESULT_CARD_STYLES = {
    "background": "white",
    "border": "2px solid #126a9c",
    "border-radius": "10px",
    "padding": "16px 18px",
}
RELATIONSHIP_SECTION_STYLES = {
    "background": "#f6fafc",
    "border": "1px solid #c9deea",
    "border-radius": "8px",
    "padding": "10px 14px",
}


def split_relationship_groups(answer, output_name):
    output_index = list(answer.names).index(output_name)
    output_group_index = next(
        index
        for index, group in enumerate(answer.groups)
        if group.exponents[output_index] == 1
    )
    output_group = answer.groups[output_group_index]
    input_groups = tuple(
        group for index, group in enumerate(answer.groups) if index != output_group_index
    )
    return output_group, input_groups


def relationship_latex(answer, output_name):
    output_group, input_groups = split_relationship_groups(answer, output_name)
    lines = [
        r"\Pi_{0} &= " + output_group.expression_latex(list(answer.names))
    ]
    lines.extend(
        rf"\Pi_{{{index}}} &= " + group.expression_latex(list(answer.names))
        for index, group in enumerate(input_groups, 1)
    )
    return r"\begin{aligned}" + "\n" + (r" \\" + "\n").join(lines) + "\n" + r"\end{aligned}"


def centered_math(expression):
    return pn.FlexBox(
        pn.pane.LaTeX(
            r"$\displaystyle " + expression + "$",
            renderer="katex",
            sizing_mode="stretch_width",
            margin=0,
            styles={"font-size": "20px", "text-align": "center"},
        ),
        height=82,
        sizing_mode="stretch_width",
        margin=0,
        align_items="center",
        justify_content="center",
        styles=MATH_CELL_STYLE,
    )


def relationship_view(answer, output_name):
    output_group, input_groups = split_relationship_groups(answer, output_name)
    output_section = pn.Column(
        pn.pane.HTML("<h3>Output group</h3>"),
        centered_math(r"\Pi_{0} = " + output_group.expression_latex(list(answer.names))),
        styles=RELATIONSHIP_SECTION_STYLES,
    )
    sections = [output_section]
    if input_groups:
        input_formulas = pn.Row(
            *[
                centered_math(
                    rf"\Pi_{{{index}}} = " + group.expression_latex(list(answer.names))
                )
                for index, group in enumerate(input_groups, 1)
            ],
            sizing_mode="stretch_width",
        )
        sections.append(
            pn.Column(
                pn.pane.HTML("<h3>Input groups</h3>"),
                input_formulas,
                styles=RELATIONSHIP_SECTION_STYLES,
            )
        )
    return pn.Column(*sections, sizing_mode="stretch_width")


def no_relationship_result(answer):
    return pn.Column(
        pn.pane.HTML(
            "<h2>Result</h2><p><strong>The hypothesized dimensionless relationship "
            "does not exist</strong> for the specified output, inputs, and dimensions.</p>"
        ),
        sizing_mode="stretch_width",
        styles=RESULT_CARD_STYLES,
    )


def relationship_result(answers, output_name):
    answer = answers[0]
    group_word = "group" if answer.group_count == 1 else "groups"
    choice_word = "choice" if len(answers) == 1 else "choices"
    summary = pn.pane.HTML(
        f'<h2>Result</h2><p>{len(answer.names)} variables, rank {answer.rank}: '
        f'<strong>{answer.group_count} independent dimensionless {group_word}</strong> and '
        f'<strong>{len(answers)} repeating-variable {choice_word}</strong>.</p>'
    )
    clipboard_source = pn.widgets.TextAreaInput(visible=False)
    copy_button = pn.widgets.Button(
        name="Copy LaTeX", button_type="primary", width=110
    )
    copy_status = pn.pane.HTML("", width=65, margin=(12, 0, 0, 0))
    copy_button.js_on_click(
        args={"source": clipboard_source, "status": copy_status},
        code="""
const copied = () => {
  status.text = "<span style='color:#126a9c'>Copied!</span>";
  setTimeout(() => { status.text = ""; }, 1400);
};
if (navigator.clipboard && navigator.clipboard.writeText) {
  navigator.clipboard.writeText(source.value).then(copied);
} else {
  const area = document.createElement("textarea");
  area.value = source.value;
  document.body.appendChild(area);
  area.select();
  document.execCommand("copy");
  area.remove();
  copied();
}
""",
    )
    active = pn.Column(sizing_mode="stretch_width")
    choice_buttons = []
    choice_chips = []

    def update_relationship(index=0):
        selected = answers[index]
        active.objects = [relationship_view(selected, output_name)]
        clipboard_source.value = relationship_latex(selected, output_name)
        for choice_index, chip in enumerate(choice_chips):
            chip.styles = (
                CHOICE_CHIP_ACTIVE_STYLES
                if choice_index == index
                else CHOICE_CHIP_INACTIVE_STYLES
            )

    for index, option in enumerate(answers):
        label = ", ".join(option.repeating_variables) or "None"
        math_label = (
            r",\;".join(symbol_latex(name) for name in option.repeating_variables)
            or r"\mathrm{None}"
        )
        chip_width = repeating_choice_width(option.repeating_variables)
        button = pn.widgets.Button(
            name=label,
            button_type="light",
            width=chip_width,
            height=38,
            sizing_mode="fixed",
            margin=0,
            styles={
                "position": "absolute",
                "inset": "0",
                "z-index": "2",
                "opacity": "0",
                "cursor": "pointer",
            },
        )
        button.on_click(lambda event, selected=index: update_relationship(selected))
        choice_buttons.append(button)
        choice_chips.append(
            pn.Column(
                pn.pane.LaTeX(
                    "$" + math_label + "$",
                    renderer="katex",
                    width=chip_width,
                    height=38,
                    sizing_mode="fixed",
                    margin=0,
                    styles={
                        "font-size": "16px",
                        "text-align": "center",
                        "padding": "7px 10px",
                        "box-sizing": "border-box",
                        "pointer-events": "none",
                    },
                ),
                button,
                width=chip_width,
                height=38,
                sizing_mode="fixed",
                margin=0,
                styles=CHOICE_CHIP_INACTIVE_STYLES,
                css_classes=["bkpi-math-chip"],
            )
        )

    repeating = pn.Column(
        pn.pane.Markdown("**Repeating variables**", margin=(0, 0, 4, 0)),
        pn.FlexBox(
            *choice_chips,
            flex_wrap="wrap",
            gap="8px",
            sizing_mode="stretch_width",
        ),
        sizing_mode="stretch_width",
        margin=0,
    )
    update_relationship()
    controls = pn.Row(
        repeating,
        copy_status,
        copy_button,
        sizing_mode="stretch_width",
        align="center",
    )
    return pn.Column(
        summary,
        controls,
        active,
        clipboard_source,
        sizing_mode="stretch_width",
        styles=RESULT_CARD_STYLES,
    )


def calculate_groups(event=None):
    variables = [
        (name.value_input, unit.value_input)
        for _, name, unit, _, _, _ in rows
        if name.value_input.strip() or unit.value_input.strip()
    ]
    try:
        if any(not name.strip() or not unit.strip() for name, unit in variables):
            raise ValueError("Each row needs both a variable name and a unit expression")
        output_row = rows[0] if rows else None
        if output_row is None or not output_row[1].value_input.strip():
            raise ValueError("Enter a name for the output variable")
        output_name = output_row[1].value_input.strip()
        baseline = analyze_options(variables)
        if baseline[0].group_count == 0:
            result.objects = [no_relationship_result(baseline[0])]
        else:
            try:
                answers = analyze_options(variables, [output_name])
            except ValueError as exc:
                if str(exc).startswith("No independent Pi-group set"):
                    result.objects = [no_relationship_result(baseline[0])]
                else:
                    raise
            else:
                result.objects = [relationship_result(answers, output_name)]
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
        '<div class="bkpi-intro"><p>BuckPi expresses a physical input-output relation in terms of '
        'dimensionless groups using the Buckingham &Pi; theorem. Enter the output first, followed by its '
        'inputs, then explore equivalent representations based on different repeating variables.</p></div>'
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
