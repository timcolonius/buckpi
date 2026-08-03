from html import escape

import panel as pn

from buckpi import SymbolError, UnitError, analyze_options, symbol_html

pn.extension(sizing_mode="stretch_width")

COLORS = {"ink": "#17212b", "blue": "#176b87", "pale": "#eef6f7", "gold": "#d8a529"}
pn.config.raw_css.append("""
:root { --buck-ink: #17212b; --buck-blue: #176b87; }
body { background: #f7f8f6; }
.bkpi-hero { padding: 22px 26px; border-left: 6px solid #d8a529; background: linear-gradient(120deg,#e7f2f3,#f8f5ea); border-radius: 10px; }
.bkpi-hero h1 { color:#17212b; margin:0 0 4px; font-size:32px; }
.bkpi-hero p { color:#53606a; margin:0; }
.bkpi-card { background:white; border:1px solid #d9deda; border-radius:10px; padding:16px 18px; }
.bkpi-result { background:#eef6f7; border-left:4px solid #176b87; border-radius:6px; padding:10px 16px; margin:8px 0; font-size:18px; }
.bkpi-error { background:#fff0ee; border-left:4px solid #b44335; padding:12px 16px; border-radius:6px; }
.bkpi-table { width:100%; border-collapse:collapse; background:white; }
.bkpi-table th,.bkpi-table td { border:1px solid #cfd8d8; padding:10px 12px; text-align:left; white-space:nowrap; }
.bkpi-table thead th { background:#176b87; color:white; }
.bkpi-table tbody th { background:#eef6f7; color:#17212b; }
.bkpi-table .math-symbol { font:18px Georgia,"Times New Roman",serif; }
.symbol-preview { min-height:34px; padding:7px 8px; font:20px Georgia,"Times New Roman",serif; color:#176b87; }
.symbol-preview .hint { color:#9aa3a7; font:13px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.symbol-preview .error { color:#b44335; font:12px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.fraction { display:inline-flex; flex-direction:column; vertical-align:middle; text-align:center; line-height:1.15; }
.fraction > span:first-child { border-bottom:1px solid currentColor; padding:0 3px 2px; }
.fraction > span:last-child { padding:2px 3px 0; }
""")

EXAMPLES = {
    "Sphere volume": [("V", "m^3"), ("R", "m")],
    "Pendulum": [("T", "s"), ("L", "m"), ("g", "m/s^2")],
    "Drag force": [("F", "N"), (r"\rho", "kg/m^3"), ("U", "m/s"), ("L", "m"), (r"\mu", "Pa*s")],
    "Surface gravity waves": [("c_p", "m/s"), (r"\lambda", "m"), ("g", "m/s^2"), ("h", "m"), (r"\rho", "kg/m^3"), (r"\sigma", "N/m")],
}

rows = []
for index in range(10):
    name = pn.widgets.TextInput(name=f"Variable {index + 1}", placeholder="e.g. U", width=150)
    unit = pn.widgets.TextInput(name="Dimensions / units", placeholder="e.g. m/s", width=240)
    repeat = pn.widgets.Checkbox(name="Require unit power", width=165)
    preview = pn.pane.HTML('<div class="symbol-preview"><span class="hint">preview</span></div>', width=105)
    rows.append((name, unit, repeat, preview))

example = pn.widgets.Select(name="Load an example", options=list(EXAMPLES), value="Pendulum", width=280)
calculate = pn.widgets.Button(name="Find dimensionless groups", button_type="primary", width=250)
clear = pn.widgets.Button(name="Clear", button_type="light", width=90)
result = pn.pane.HTML("", sizing_mode="stretch_width")


def load_example(event=None):
    values = EXAMPLES[example.value]
    for index, (name, unit, repeat, _) in enumerate(rows):
        name.value, unit.value, repeat.value = (values[index][0], values[index][1], False) if index < len(values) else ("", "", False)
    calculate_groups()


def calculate_groups(event=None):
    variables = [(name.value, unit.value) for name, unit, _, _ in rows if name.value.strip() or unit.value.strip()]
    preferred = [name.value for name, _, repeat, _ in rows if repeat.value and name.value.strip()]
    try:
        if any(not name.strip() or not unit.strip() for name, unit in variables):
            raise ValueError("Each row needs both a variable name and a unit expression")
        answers = analyze_options(variables, preferred)
        answer = answers[0]
        headings = "".join(f'<th>&Pi;<sub>{i}</sub></th>' for i in range(1, answer.group_count + 1))
        rows_html = ""
        for row_number, option in enumerate(answers, 1):
            cells = "".join(f'<td class="math-symbol">{group.expression_html(list(option.names))}</td>' for group in option.groups)
            rows_html += f'<tr><th>{row_number}</th>{cells}</tr>'
        result.object = (
            f'<div class="bkpi-card"><h2>Result</h2><p>{len(answer.names)} variables, rank {answer.rank}: '
            f'<strong>{answer.group_count} independent dimensionless group(s)</strong>, shown in '
            f'<strong>{len(answers)} admissible form(s)</strong>.</p>'
            f'<div style="overflow-x:auto"><table class="bkpi-table"><thead><tr><th>Option</th>{headings}</tr></thead>'
            f'<tbody>{rows_html}</tbody></table></div>'
            f'<p><small>Each row is a complete independent set. Equivalent rows differ only in the chosen basis.</small></p></div>'
        )
    except (ValueError, UnitError, SymbolError) as exc:
        result.object = f'<div class="bkpi-error"><strong>Check the input:</strong> {escape(str(exc))}</div>'


def clear_rows(event=None):
    for name, unit, repeat, _ in rows:
        name.value, unit.value, repeat.value = "", "", False
    result.object = ""


example.param.watch(load_example, "value")
calculate.on_click(calculate_groups)
clear.on_click(clear_rows)

def update_preview(event, preview):
    if not event.new.strip():
        preview.object = '<div class="symbol-preview"><span class="hint">preview</span></div>'
        return
    try:
        preview.object = f'<div class="symbol-preview">{symbol_html(event.new)}</div>'
    except SymbolError as exc:
        preview.object = f'<div class="symbol-preview"><span class="error">{escape(str(exc))}</span></div>'


for name, _, _, preview in rows:
    name.param.watch(lambda event, pane=preview: update_preview(event, pane), "value")

table = pn.Column(
    pn.Row(pn.pane.Markdown("**Variable**", width=150), pn.pane.Markdown("**Dimensions / units**", width=240), pn.pane.Markdown("**Unit power = 1**", width=165), pn.pane.Markdown("**Preview**", width=105)),
    *[pn.Row(name, unit, repeat, preview) for name, unit, repeat, preview in rows],
)

app = pn.Column(
    pn.pane.HTML('<div class="bkpi-hero"><h1>BuckPi</h1><p>Dimensional analysis using the Buckingham &Pi; theorem</p></div>'),
    pn.Row(example, pn.Spacer(width=12), clear),
    pn.pane.HTML('<div class="bkpi-card"><p>Enter each variable using ordinary text or LaTeX-style notation such as <code>\\rho</code>, <code>c_p</code>, <code>U_{\\infty}</code>, or <code>\\Delta p</code>. Enter units separately using expressions such as <code>m/s</code>, <code>kg/m^3</code>, <code>Pa*s</code>, or <code>N/m</code>. By default, every admissible set of &Pi; groups is shown.</p></div>'),
    table,
    calculate,
    result,
    pn.pane.Markdown("Exact rational linear algebra runs locally in your browser. No data is uploaded.  \nTim Colonius · California Institute of Technology"),
    max_width=920,
    margin=(20, 0),
)

load_example()
app.servable(title="BuckPi — Dimensional Analysis")
