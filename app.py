from html import escape
from io import BytesIO
import re

import panel as pn

from buckpi import (
    SymbolError, UnitError, analyze_options, decode_case, distinct_options,
    encode_case, symbol_latex,
)

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
.bkpi-rank {
  display: inline-block;
  background: var(--buck-soft);
  border: 1px solid var(--buck-line);
  border-radius: 999px;
  color: var(--buck-navy);
  padding: 6px 12px;
  white-space: nowrap;
}
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
ISOLATE_TIP = (
    "Require this variable to be non-repeating and normalized to exponent 1 in one Pi group. "
    "At most n minus the dimension-matrix rank variables can be isolated."
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
CHOICE_LABEL_ACTIVE_STYLES = {
    "display": "flex",
    "align-items": "center",
    "justify-content": "center",
    "font-size": "16px",
    "line-height": "1",
    "text-align": "center",
    "color": "white",
    "pointer-events": "none",
}
CHOICE_LABEL_INACTIVE_STYLES = {
    "display": "flex",
    "align-items": "center",
    "justify-content": "center",
    "font-size": "16px",
    "line-height": "1",
    "text-align": "center",
    "color": "#0b2d4d",
    "pointer-events": "none",
}


def repeating_choice_width(names):
    """Estimate rendered math width without counting LaTeX command text."""
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
updating_isolates = False
next_row_id = 0
selected_repeating_variables = ()

example = pn.widgets.Select(
    name="Load an example", options=list(EXAMPLES), value="Pendulum", width=280
)
add = pn.widgets.Button(name="+ Add variable", button_type="light", width=120)
save_case = pn.widgets.FileDownload(
    name="Save case",
    filename="buckpi-case.json",
    button_type="primary",
    width=110,
)
load_case = pn.widgets.FileInput(name="Load case", accept=".json,application/json", width=170)
case_status = pn.pane.HTML("", width=150, margin=(8, 0, 0, 0))
rank_indicator = pn.pane.HTML(
    '<div class="bkpi-rank"><strong>Dimension-matrix rank:</strong> &mdash;</div>',
    margin=(5, 0),
)
table = pn.Column(sizing_mode="stretch_width", margin=(0, 10, 16, 10))
result = pn.Column(sizing_mode="stretch_width", margin=(0, 10))


def mark_example_edited(event=None):
    if not loading_example:
        case_status.object = ""
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


def isolate_changed(event=None):
    if not updating_isolates:
        mark_example_edited()


def update_isolate_controls(limit=None):
    global updating_isolates
    selected = [row[3] for row in rows if row[3].value]
    if limit is not None and len(selected) > limit:
        updating_isolates = True
        for checkbox in selected[limit:]:
            checkbox.value = False
        updating_isolates = False
        selected = selected[:limit]
    at_limit = limit is not None and len(selected) >= limit
    for row in rows:
        checkbox = row[3]
        checkbox.disabled = at_limit and not checkbox.value


def make_row(name_value="", unit_value=""):
    global next_row_id
    next_row_id += 1
    row_id = str(next_row_id)
    name = pn.widgets.TextInput(
        name="Variable",
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
    isolate = pn.widgets.Checkbox(name="Isolate", value=False, width=72, margin=0)
    isolate_cell = pn.Row(
        isolate,
        pn.widgets.TooltipIcon(value=ISOLATE_TIP, width=20, margin=0),
        width=105,
        height=38,
        margin=(23, 10, 0, 10),
        styles={"display": "flex", "align-items": "center", "justify-content": "center"},
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
    isolate.param.watch(isolate_changed, "value")
    remove.on_click(lambda event, target=row_id: remove_row(target))
    row_objects = [name, unit, isolate_cell, preview, remove]
    row_layout = pn.Row(*row_objects, sizing_mode="stretch_width")
    return row_id, name, unit, isolate, preview, remove, row_layout

def refresh_table():
    heading = pn.Row(
        pn.pane.HTML("<h2>Variables</h2>"),
        pn.Spacer(sizing_mode="stretch_width"),
        rank_indicator,
        sizing_mode="stretch_width",
        align="center",
    )
    variables_box = pn.Column(
        heading,
        *[row[6] for row in rows],
        add,
        styles=CARD_STYLES,
    )
    table.objects = [variables_box]


def load_example(event=None):
    global loading_example, selected_repeating_variables
    loading_example = True
    selected_repeating_variables = ()
    rows.clear()
    for name_value, unit_value in EXAMPLES[example.value]:
        rows.append(make_row(name_value, unit_value))
    refresh_table()
    example.stylesheets = []
    case_status.object = ""
    loading_example = False
    calculate_groups()


def add_row(event=None):
    rows.append(make_row())
    refresh_table()
    mark_example_edited()


def remove_row(target):
    rows[:] = [row for row in rows if row[0] != target]
    refresh_table()
    mark_example_edited()


def case_download():
    variables = [
        (name.value_input, unit.value_input, isolate.value)
        for _, name, unit, isolate, _, _, _ in rows
    ]
    return BytesIO(encode_case(variables, selected_repeating_variables))


def load_saved_case(event):
    global loading_example, selected_repeating_variables
    if not event.new:
        return
    try:
        saved = decode_case(event.new)
        variables = [(item.name, item.unit) for item in saved.variables]
        isolated = [item.name for item in saved.variables if item.isolate]
        analyze_options(variables, isolated)

        loading_example = True
        try:
            new_rows = []
            for item in saved.variables:
                row = make_row(item.name, item.unit)
                row[3].value = item.isolate
                new_rows.append(row)
        finally:
            loading_example = False

        rows[:] = new_rows
        selected_repeating_variables = saved.repeating_variables
        refresh_table()
        example.stylesheets = [EDITED_EXAMPLE_STYLESHEET]
        calculate_groups()
        case_status.object = '<span style="color:#126a9c">Case loaded.</span>'
    except (ValueError, UnitError, SymbolError) as exc:
        case_status.object = (
            '<span style="color:#b42318"><strong>Error:</strong> '
            f'{escape(str(exc))}</span>'
        )
    finally:
        load_case.value = None
        load_case.filename = None


RESULT_CARD_STYLES = {
    "background": "white",
    "border": "2px solid #126a9c",
    "border-radius": "10px",
    "padding": "16px 18px",
}
FORM_SECTION_STYLES = {
    "background": "#f6fafc",
    "border": "1px solid #c9deea",
    "border-radius": "8px",
    "padding": "10px 14px",
}


def form_latex(answer):
    lines = [
        rf"\Pi_{{{index}}} &= " + group.expression_latex(list(answer.names))
        for index, group in enumerate(answer.groups, 1)
    ]
    return r"\begin{aligned}" + "\n" + (r" \\" + "\n").join(lines) + "\n" + r"\end{aligned}"


def form_view(answer):
    pi_width = min(360, max(250, 820 // max(answer.group_count, 1)))
    formulas = pn.Row(
        *[
            pn.FlexBox(
                pn.pane.LaTeX(
                    r"$\displaystyle \Pi_{"
                    + str(index)
                    + "} = "
                    + group.expression_latex(list(answer.names))
                    + "$",
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
            for index, group in enumerate(answer.groups, 1)
        ],
        width=answer.group_count * pi_width,
        sizing_mode=None,
        margin=0,
    )
    return pn.Column(
        pn.pane.HTML("<h3>Dimensionless groups</h3>"),
        formulas,
        sizing_mode="stretch_width",
        styles=FORM_SECTION_STYLES | {"overflow-x": "auto"},
    )


def result_panel(answers):
    global selected_repeating_variables
    answer = answers[0]
    if answer.group_count == 0:
        return pn.Column(
            pn.pane.HTML(
                "<h2>Result</h2><p><strong>No nontrivial dimensionless groups exist</strong> "
                "for the specified variables and dimensions.</p>"
            ),
            sizing_mode="stretch_width",
            styles=RESULT_CARD_STYLES,
        )

    group_word = "group" if answer.group_count == 1 else "groups"
    form_word = "form" if len(answers) == 1 else "forms"
    summary = pn.pane.HTML(
        f'<h2>Result</h2><p>{len(answer.names)} variables, rank {answer.rank}: '
        f'<strong>{answer.group_count} independent dimensionless {group_word}</strong> and '
        f'<strong>{len(answers)} distinct &Pi;-group {form_word}</strong>.</p>'
    )
    clipboard_source = pn.widgets.TextAreaInput(visible=False)
    copy_button = pn.widgets.Button(name="Copy LaTeX", button_type="primary", width=110)
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
    choice_labels = []

    def update_form(index=0):
        global selected_repeating_variables
        selected = answers[index]
        selected_repeating_variables = selected.repeating_variables
        active.objects = [form_view(selected)]
        clipboard_source.value = form_latex(selected)
        for choice_index, chip in enumerate(choice_chips):
            chip.styles = (
                CHOICE_CHIP_ACTIVE_STYLES
                if choice_index == index
                else CHOICE_CHIP_INACTIVE_STYLES
            )
            choice_labels[choice_index].styles = (
                CHOICE_LABEL_ACTIVE_STYLES
                if choice_index == index
                else CHOICE_LABEL_INACTIVE_STYLES
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
        button.on_click(lambda event, selected=index: update_form(selected))
        choice_buttons.append(button)
        math_pane = pn.pane.LaTeX(
            "$" + math_label + "$",
            renderer="katex",
            width=chip_width,
            height=38,
            sizing_mode="fixed",
            margin=0,
            styles=CHOICE_LABEL_INACTIVE_STYLES,
        )
        choice_labels.append(math_pane)
        choice_chips.append(
            pn.Column(
                pn.FlexBox(
                    math_pane,
                    width=chip_width,
                    height=38,
                    sizing_mode="fixed",
                    margin=0,
                    align_items="center",
                    justify_content="center",
                    styles={"pointer-events": "none"},
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
        pn.pane.Markdown("**Choose Repeating Variables**", margin=(0, 0, 4, 0)),
        pn.FlexBox(
            *choice_chips,
            flex_wrap="wrap",
            gap="8px",
            sizing_mode="stretch_width",
        ),
        sizing_mode="stretch_width",
        margin=0,
    )
    initial_index = next(
        (
            index for index, option in enumerate(answers)
            if option.repeating_variables == selected_repeating_variables
        ),
        0,
    )
    update_form(initial_index)
    controls = pn.Row(
        repeating,
        copy_status,
        copy_button,
        sizing_mode="stretch_width",
        align="center",
        margin=(0, 0, 12, 0),
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
        for _, name, unit, _, _, _, _ in rows
        if name.value_input.strip() or unit.value_input.strip()
    ]
    try:
        if any(not name.strip() or not unit.strip() for name, unit in variables):
            raise ValueError("Each row needs both a variable name and a unit expression")
        if not variables:
            raise ValueError("Enter at least one variable and unit expression")
        baseline = distinct_options(analyze_options(variables))
        answer = baseline[0]
        limit = answer.group_count
        update_isolate_controls(limit)
        isolated = [
            name.value_input.strip()
            for _, name, _, isolate, _, _, _ in rows
            if isolate.value and name.value_input.strip()
        ]
        rank_indicator.object = (
            '<div class="bkpi-rank"><strong>Dimension-matrix rank:</strong> '
            f'{answer.rank} &middot; <strong>Isolation limit:</strong> {limit}</div>'
        )
        answers = (
            distinct_options(analyze_options(variables, isolated))
            if isolated else baseline
        )
        save_case.disabled = False
        result.objects = [result_panel(answers)]
    except (ValueError, UnitError, SymbolError) as exc:
        rank_indicator.object = (
            '<div class="bkpi-rank"><strong>Dimension-matrix rank:</strong> &mdash;</div>'
        )
        update_isolate_controls()
        save_case.disabled = True
        result.objects = [
            pn.pane.HTML(
                f'<div class="bkpi-error"><strong>Error:</strong> {escape(str(exc))}</div>'
            )
        ]
    result.styles = {}


example.param.watch(load_example, "value")
add.on_click(add_row)
save_case.callback = case_download
load_case.param.watch(load_saved_case, "value")

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
        'Enter its variables and dimensions to find every admissible independent set of dimensionless '
        'groups using the Buckingham &Pi; theorem.</p></div>'
    ),
    pn.Row(
        example,
        pn.Spacer(sizing_mode="stretch_width"),
        save_case,
        load_case,
        case_status,
        sizing_mode="stretch_width",
        align="end",
    ),
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
