importScripts("https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js");

function sendPatch(patch, buffers, msg_id) {
  self.postMessage({
    type: 'patch',
    patch: patch,
    buffers: buffers
  })
}

async function startApplication() {
  console.log("Loading pyodide!");
  self.postMessage({type: 'status', msg: 'Loading pyodide'})
  self.pyodide = await loadPyodide();
  self.pyodide.globals.set("sendPatch", sendPatch);
  console.log("Loaded!");
  await self.pyodide.loadPackage("micropip");
  const env_spec = ['https://cdn.holoviz.org/panel/wheels/bokeh-3.4.3-py3-none-any.whl', 'https://cdn.holoviz.org/panel/1.4.5/dist/wheels/panel-1.4.5-py3-none-any.whl', 'pyodide-http==0.2.1', 'pint==0.24.4', './buckpi-0.1.0-1ecc20f238a-py3-none-any.whl']
  for (const pkg of env_spec) {
    let pkg_name;
    if (pkg.endsWith('.whl')) {
      pkg_name = pkg.split('/').slice(-1)[0].split('-')[0]
    } else {
      pkg_name = pkg
    }
    self.postMessage({type: 'status', msg: `Installing ${pkg_name}`})
    try {
      await self.pyodide.runPythonAsync(`
        import micropip
        await micropip.install('${pkg}');
      `);
    } catch(e) {
      console.log(e)
      self.postMessage({
	type: 'status',
	msg: `Error while installing ${pkg_name}`
      });
    }
  }
  console.log("Packages loaded!");
  self.postMessage({type: 'status', msg: 'Executing code'})
  const code = `
  \nimport asyncio\n\nfrom panel.io.pyodide import init_doc, write_doc\n\ninit_doc()\n\nfrom html import escape\n\nimport panel as pn\n\nfrom buckpi import SymbolError, UnitError, analyze_options, symbol_latex\n\npn.extension("katex", sizing_mode="stretch_width")\n\npn.config.raw_css.append("""\n:root {\n  --buck-navy: #0b2d4d;\n  --buck-blue: #126a9c;\n  --buck-mid: #4e91b8;\n  --buck-soft: #dcecf5;\n  --buck-pale: #f3f4f6;\n  --buck-line: #b9d4e4;\n}\nbody { background: var(--buck-pale); color: var(--buck-navy); }\n.bkpi-banner {\n  overflow: hidden;\n  border: 1px solid var(--buck-line);\n  border-radius: 8px;\n  background: white;\n  box-shadow: 0 5px 18px rgba(11, 45, 77, 0.10);\n}\n.bkpi-banner-meta {\n  padding: 6px 20px;\n  background: var(--buck-soft);\n  color: #416b86;\n  font-size: 11px;\n  letter-spacing: 0.05em;\n  text-align: right;\n}\n.bkpi-brand {\n  display: flex;\n  align-items: center;\n  gap: 20px;\n  padding: 18px 24px 20px;\n}\n.bkpi-mark { display: flex; align-items: center; gap: 8px; padding-left: 24px; position: relative; }\n.bkpi-mark::before {\n  content: "";\n  position: absolute;\n  left: 0;\n  width: 18px;\n  height: 22px;\n  border-top: 2px solid var(--buck-mid);\n  border-bottom: 2px solid var(--buck-mid);\n  box-shadow: 0 -8px 0 -6px var(--buck-mid), 0 8px 0 -6px var(--buck-mid);\n}\n.bkpi-mark span {\n  display: block;\n  width: 22px;\n  height: 22px;\n  transform: rotate(45deg);\n  border-radius: 3px;\n}\n.bkpi-mark span:nth-child(1) { background: #8bc0dc; }\n.bkpi-mark span:nth-child(2) { background: #3f8db7; }\n.bkpi-mark span:nth-child(3) { background: #0e5f91; }\n.bkpi-brand h1 { color: var(--buck-navy); margin: 0; font-size: 34px; line-height: 1; }\n.bkpi-brand p { color: #52738a; margin: 5px 0 0; font-size: 14px; }\n.bkpi-intro {\n  background: #e8f3f9;\n  border-left: 5px solid var(--buck-blue);\n  border-radius: 7px;\n  color: #244f6b;\n  line-height: 1.55;\n  padding: 13px 18px;\n}\n.bkpi-intro p { margin: 0; }\n.bkpi-error { background:#fff5f5; border-left:4px solid #b42318; color:#b42318; padding:12px 16px; border-radius:6px; }\n@media (max-width: 620px) {\n  .bkpi-brand { gap: 14px; padding: 16px; }\n  .bkpi-mark { transform: scale(0.86); transform-origin: left center; margin-right: -8px; }\n  .bkpi-brand h1 { font-size: 29px; }\n}\n""")\n\nUNIT_TIP = (\n    "Use any Pint-recognized unit name or abbreviation, including SI, US customary, and CGS. "\n    "Combine units with * or /, use ^ or ** for powers, and use parentheses for grouping. "\n    "Examples: kg/m^3, N/m, Pa*s, slug/ft^3, lbf, psi, and mph. Prefixes, plurals, and mixed "\n    "unit systems are allowed. BuckPi uses dimensionality only; it does not convert numerical values."\n)\nVARIABLE_TIP = (\n    r"Enter ordinary text or LaTeX-style notation. Examples: U, \\rho, c_p, U_{\\infty}, and \\Delta p. "\n    "Greek commands, subscripts, and superscripts are supported."\n)\nREQUIRE_TIP = (\n    "By default BuckPi shows every admissible basis of independent Pi groups. Check one or more "\n    "boxes to restrict the table to bases in which each selected variable appears with exponent 1 "\n    "in a separate Pi group."\n)\n\nEDITED_EXAMPLE_STYLESHEET = """\nselect, .bk-input { color: #7794a8 !important; font-style: italic !important; }\n"""\nPREVIEW_STYLE = {\n    "color": "#126a9c",\n    "padding": "7px 8px",\n    "min-height": "38px",\n}\nPREVIEW_ERROR_STYLE = {\n    "color": "#174f75",\n    "padding": "7px 8px",\n    "min-height": "38px",\n}\nHEADER_STYLE = {\n    "background": "#126a9c",\n    "color": "white",\n    "padding": "10px 12px",\n    "border": "1px solid #a9cadc",\n    "font-weight": "600",\n    "display": "flex",\n    "align-items": "center",\n    "justify-content": "center",\n}\nOPTION_STYLE = {\n    "background": "#e3f0f7",\n    "padding": "10px 12px",\n    "border": "1px solid #b9d4e4",\n    "font-weight": "600",\n    "display": "flex",\n    "align-items": "center",\n    "justify-content": "center",\n}\nMATH_CELL_STYLE = {\n    "background": "white",\n    "padding": "10px 12px",\n    "border": "1px solid #b9d4e4",\n    "min-height": "72px",\n    "display": "flex",\n    "align-items": "center",\n    "justify-content": "center",\n}\n\nEXAMPLES = {\n    "Sphere volume": [("V", "m^3"), ("R", "m")],\n    "Pendulum": [("T", "s"), ("L", "m"), ("g", "m/s^2")],\n    "Drag force": [\n        ("F", "N"), (r"\\rho", "kg/m^3"), ("U", "m/s"), ("L", "m"),\n        (r"\\mu", "Pa*s"),\n    ],\n    "Surface gravity waves": [\n        ("c_p", "m/s"), (r"\\lambda", "m"), ("g", "m/s^2"), ("h", "m"),\n        (r"\\rho", "kg/m^3"), (r"\\sigma", "N/m"),\n    ],\n}\n\nrows = []\nloading_example = False\n\nexample = pn.widgets.Select(\n    name="Load an example", options=list(EXAMPLES), value="Pendulum", width=280\n)\ncalculate = pn.widgets.Button(\n    name="Find dimensionless groups", button_type="primary", width=250\n)\nadd = pn.widgets.Button(name="+ Add row", button_type="light", width=110)\ntable = pn.Column(sizing_mode="stretch_width")\nresult = pn.Column(sizing_mode="stretch_width")\n\n\ndef mark_example_edited(event=None):\n    if not loading_example:\n        example.stylesheets = [EDITED_EXAMPLE_STYLESHEET]\n        if result.objects:\n            result.styles = {\n                "opacity": "0.35",\n                "transition": "opacity 120ms ease",\n            }\n            calculate.name = "Recalculate dimensionless groups"\n            calculate.button_type = "primary"\n\n\ndef update_preview(event, preview):\n    if not event.new.strip():\n        preview.object = r"$\\text{preview}$"\n        preview.styles = PREVIEW_STYLE | {"color": "#7794a8"}\n        return\n    try:\n        preview.object = "$" + symbol_latex(event.new) + "$"\n        preview.styles = PREVIEW_STYLE\n    except SymbolError:\n        preview.object = r"$\\text{invalid}$"\n        preview.styles = PREVIEW_ERROR_STYLE\n\n\ndef make_row(name_value="", unit_value=""):\n    index = len(rows) + 1\n    name = pn.widgets.TextInput(\n        name=f"Variable {index}", value=name_value, placeholder=r"e.g. \\rho", width=150\n    )\n    unit = pn.widgets.TextInput(\n        name="Dimensions / units",\n        value=unit_value,\n        placeholder="e.g. kg/m^3",\n        width=240,\n    )\n    require = pn.widgets.Checkbox(name="", value=False, width=20, margin=0)\n    require_cell = pn.Row(\n        require,\n        width=165,\n        height=42,\n        margin=(5, 10),\n        styles={"display": "flex", "justify-content": "center", "align-items": "center"},\n    )\n    remove = pn.widgets.Button(name="Remove", button_type="light", width=80, align="center")\n    preview_text = "$" + symbol_latex(name_value) + "$" if name_value else r"$\\text{preview}$"\n    preview = pn.pane.LaTeX(\n        preview_text,\n        renderer="katex",\n        width=105,\n        height=42,\n        styles=PREVIEW_STYLE if name_value else PREVIEW_STYLE | {"color": "#7794a8"},\n    )\n    name.param.watch(lambda event, pane=preview: update_preview(event, pane), "value")\n    for widget in (name, unit, require):\n        widget.param.watch(mark_example_edited, "value")\n    remove.on_click(lambda event, target=name: remove_row(target))\n    row_layout = pn.Row(name, unit, require_cell, preview, remove, sizing_mode="stretch_width")\n    return name, unit, require, preview, remove, row_layout\n\n\ndef refresh_table():\n    variable_heading = pn.Row(\n        pn.pane.Markdown("**Variable**", width=120, margin=0),\n        pn.widgets.TooltipIcon(value=VARIABLE_TIP, width=20, margin=0),\n        width=150,\n        margin=(5, 10),\n    )\n    unit_heading = pn.Row(\n        pn.pane.Markdown("**Dimensions / units**", width=210, margin=0),\n        pn.widgets.TooltipIcon(value=UNIT_TIP, width=20, margin=0),\n        width=240,\n        margin=(5, 10),\n    )\n    exponent_heading = pn.Row(\n        pn.pane.Markdown("**Require exponent = 1**", width=135, margin=0),\n        pn.widgets.TooltipIcon(value=REQUIRE_TIP, width=20, margin=0),\n        width=165,\n        margin=(5, 10),\n    )\n    heading = pn.Row(\n        variable_heading,\n        unit_heading,\n        exponent_heading,\n        pn.pane.Markdown("**Preview**", width=105),\n        pn.Spacer(width=80, margin=(5, 10)),\n        sizing_mode="stretch_width",\n    )\n    table.objects = [heading, *[row[5] for row in rows], add]\n\n\ndef load_example(event=None):\n    global loading_example\n    loading_example = True\n    rows.clear()\n    for name_value, unit_value in EXAMPLES[example.value]:\n        rows.append(make_row(name_value, unit_value))\n    refresh_table()\n    example.stylesheets = []\n    loading_example = False\n    calculate_groups()\n\n\ndef add_row(event=None):\n    rows.append(make_row())\n    refresh_table()\n    mark_example_edited()\n\n\ndef remove_row(target):\n    rows[:] = [row for row in rows if row[0] is not target]\n    refresh_table()\n    mark_example_edited()\n\n\ndef result_table(answers):\n    answer = answers[0]\n    summary = pn.pane.HTML(\n        f'<h2>Result</h2><p>{len(answer.names)} variables, rank {answer.rank}: '\n        f'<strong>{answer.group_count} independent dimensionless group(s)</strong>, shown in '\n        f'<strong>{len(answers)} admissible form(s)</strong>.</p>'\n    )\n    header = pn.Row(\n        pn.pane.HTML("Option", width=80, styles=HEADER_STYLE),\n        *[\n            pn.pane.HTML(\n                f"&Pi;<sub>{i}</sub>", sizing_mode="stretch_width", styles=HEADER_STYLE\n            )\n            for i in range(1, answer.group_count + 1)\n        ],\n        sizing_mode="stretch_width",\n    )\n    option_rows = []\n    for row_number, option in enumerate(answers, 1):\n        cells = [\n            pn.pane.LaTeX(\n                r"$\\displaystyle " + group.expression_latex(list(option.names)) + "$",\n                renderer="katex",\n                height=76,\n                sizing_mode="stretch_width",\n                styles=MATH_CELL_STYLE,\n            )\n            for group in option.groups\n        ]\n        option_rows.append(\n            pn.Row(\n                pn.pane.HTML(str(row_number), width=80, height=76, styles=OPTION_STYLE),\n                *cells,\n                sizing_mode="stretch_width",\n            )\n        )\n    note = pn.pane.HTML(\n        "<small>Each row is a complete independent set. Equivalent rows differ only in the chosen basis.</small>"\n    )\n    grid = pn.Column(\n        header,\n        *option_rows,\n        sizing_mode="stretch_width",\n        styles={"overflow-x": "auto"},\n    )\n    return pn.Column(summary, grid, note, styles={"background": "white", "border": "1px solid #b9d4e4", "border-radius": "10px", "padding": "16px 18px"})\n\n\ndef calculate_groups(event=None):\n    variables = [\n        (name.value, unit.value)\n        for name, unit, _, _, _, _ in rows\n        if name.value.strip() or unit.value.strip()\n    ]\n    preferred = [\n        name.value\n        for name, _, require, _, _, _ in rows\n        if require.value and name.value.strip()\n    ]\n    try:\n        if any(not name.strip() or not unit.strip() for name, unit in variables):\n            raise ValueError("Each row needs both a variable name and a unit expression")\n        answers = analyze_options(variables, preferred)\n        result.objects = [result_table(answers)]\n    except (ValueError, UnitError, SymbolError) as exc:\n        result.objects = [\n            pn.pane.HTML(\n                f'<div class="bkpi-error"><strong>Check the input:</strong> {escape(str(exc))}</div>'\n            )\n        ]\n    result.styles = {}\n    calculate.name = "Find dimensionless groups"\n    calculate.button_type = "primary"\n\n\nexample.param.watch(load_example, "value")\ncalculate.on_click(calculate_groups)\nadd.on_click(add_row)\n\napp = pn.Column(\n    pn.pane.HTML(\n        '<div class="bkpi-banner">'\n        '<div class="bkpi-banner-meta">Tim Colonius &middot; Caltech</div>'\n        '<div class="bkpi-brand">'\n        '<div class="bkpi-mark" aria-hidden="true"><span></span><span></span><span></span></div>'\n        '<div><h1>BuckPi</h1><p>Dimensional analysis</p></div>'\n        '</div></div>'\n    ),\n    pn.pane.HTML(\n        '<div class="bkpi-intro"><p>BuckPi reveals the dimensionless structure of a physical problem. '\n        'It applies the Buckingham &Pi; theorem to your variables and dimensions, then lists every '\n        'admissible independent set of &Pi; groups. Start from an example or build your own problem below.</p></div>'\n    ),\n    pn.Row(example),\n    table,\n    calculate,\n    result,\n    pn.pane.Markdown(\n        "Exact rational linear algebra runs locally in your browser. No data is uploaded.  \\n"\n        "Tim Colonius \xb7 California Institute of Technology"\n    ),\n    max_width=920,\n    margin=(20, 0),\n)\n\nload_example()\napp.servable(title="BuckPi \u2014 Dimensional Analysis")\n\n\nawait write_doc()
  `

  try {
    const [docs_json, render_items, root_ids] = await self.pyodide.runPythonAsync(code)
    self.postMessage({
      type: 'render',
      docs_json: docs_json,
      render_items: render_items,
      root_ids: root_ids
    })
  } catch(e) {
    const traceback = `${e}`
    const tblines = traceback.split('\n')
    self.postMessage({
      type: 'status',
      msg: tblines[tblines.length-2]
    });
    throw e
  }
}

self.onmessage = async (event) => {
  const msg = event.data
  if (msg.type === 'rendered') {
    self.pyodide.runPythonAsync(`
    from panel.io.state import state
    from panel.io.pyodide import _link_docs_worker

    _link_docs_worker(state.curdoc, sendPatch, setter='js')
    `)
  } else if (msg.type === 'patch') {
    self.pyodide.globals.set('patch', msg.patch)
    self.pyodide.runPythonAsync(`
    from panel.io.pyodide import _convert_json_patch
    state.curdoc.apply_json_patch(_convert_json_patch(patch), setter='js')
    `)
    self.postMessage({type: 'idle'})
  } else if (msg.type === 'location') {
    self.pyodide.globals.set('location', msg.location)
    self.pyodide.runPythonAsync(`
    import json
    from panel.io.state import state
    from panel.util import edit_readonly
    if state.location:
        loc_data = json.loads(location)
        with edit_readonly(state.location):
            state.location.param.update({
                k: v for k, v in loc_data.items() if k in state.location.param
            })
    `)
  }
}

startApplication()