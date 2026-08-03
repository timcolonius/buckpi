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
  const env_spec = ['https://cdn.holoviz.org/panel/wheels/bokeh-3.4.3-py3-none-any.whl', 'https://cdn.holoviz.org/panel/1.4.5/dist/wheels/panel-1.4.5-py3-none-any.whl', 'pyodide-http==0.2.1', 'pint==0.24.4', './buckpi-0.1.0-155588d26b3-py3-none-any.whl']
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
  \nimport asyncio\n\nfrom panel.io.pyodide import init_doc, write_doc\n\ninit_doc()\n\nfrom html import escape\n\nimport panel as pn\n\nfrom buckpi import SymbolError, UnitError, analyze_options, symbol_latex\n\npn.extension("katex", sizing_mode="stretch_width")\n\npn.config.raw_css.append("""\n:root { --buck-ink: #17212b; --buck-blue: #176b87; }\nbody { background: #f7f8f6; }\n.bkpi-hero { padding: 22px 26px; border-left: 6px solid #d8a529; background: linear-gradient(120deg,#e7f2f3,#f8f5ea); border-radius: 10px; }\n.bkpi-hero h1 { color:#17212b; margin:0 0 4px; font-size:32px; }\n.bkpi-hero p { color:#53606a; margin:0; }\n.bkpi-card { background:white; border:1px solid #d9deda; border-radius:10px; padding:16px 18px; }\n.bkpi-error { background:#fff0ee; border-left:4px solid #b44335; padding:12px 16px; border-radius:6px; }\n""")\n\nUNIT_TIP = (\n    "Use any Pint-recognized unit name or abbreviation, including SI, US customary, and CGS. "\n    "Combine units with * or /, use ^ or ** for powers, and use parentheses for grouping. "\n    "Examples: kg/m^3, N/m, Pa*s, slug/ft^3, lbf, psi, and mph. Prefixes, plurals, and mixed "\n    "unit systems are allowed. BuckPi uses dimensionality only; it does not convert numerical values."\n)\n\nEDITED_EXAMPLE_STYLESHEET = """\nselect, .bk-input { color: #9ca3af !important; font-style: italic !important; }\n"""\nPREVIEW_STYLE = {\n    "color": "#176b87",\n    "padding": "7px 8px",\n    "min-height": "38px",\n}\nPREVIEW_ERROR_STYLE = {\n    "color": "#b44335",\n    "padding": "7px 8px",\n    "min-height": "38px",\n}\nHEADER_STYLE = {\n    "background": "#176b87",\n    "color": "white",\n    "padding": "10px 12px",\n    "border": "1px solid #cfd8d8",\n    "font-weight": "600",\n}\nOPTION_STYLE = {\n    "background": "#eef6f7",\n    "padding": "10px 12px",\n    "border": "1px solid #cfd8d8",\n    "font-weight": "600",\n}\nMATH_CELL_STYLE = {\n    "background": "white",\n    "padding": "10px 12px",\n    "border": "1px solid #cfd8d8",\n    "min-height": "48px",\n}\n\nEXAMPLES = {\n    "Sphere volume": [("V", "m^3"), ("R", "m")],\n    "Pendulum": [("T", "s"), ("L", "m"), ("g", "m/s^2")],\n    "Drag force": [\n        ("F", "N"), (r"\\rho", "kg/m^3"), ("U", "m/s"), ("L", "m"),\n        (r"\\mu", "Pa*s"),\n    ],\n    "Surface gravity waves": [\n        ("c_p", "m/s"), (r"\\lambda", "m"), ("g", "m/s^2"), ("h", "m"),\n        (r"\\rho", "kg/m^3"), (r"\\sigma", "N/m"),\n    ],\n}\n\nrows = []\nloading_example = False\n\nexample = pn.widgets.Select(\n    name="Load an example", options=list(EXAMPLES), value="Pendulum", width=280\n)\ncalculate = pn.widgets.Button(\n    name="Find dimensionless groups", button_type="primary", width=250\n)\nclear = pn.widgets.Button(name="Clear", button_type="light", width=90)\nadd = pn.widgets.Button(name="+ Add row", button_type="light", width=110)\ntable = pn.Column(sizing_mode="stretch_width")\nresult = pn.Column(sizing_mode="stretch_width")\n\n\ndef mark_example_edited(event=None):\n    if not loading_example:\n        example.stylesheets = [EDITED_EXAMPLE_STYLESHEET]\n\n\ndef update_preview(event, preview):\n    if not event.new.strip():\n        preview.object = r"$\\text{preview}$"\n        preview.styles = PREVIEW_STYLE | {"color": "#9ca3a7"}\n        return\n    try:\n        preview.object = "$" + symbol_latex(event.new) + "$"\n        preview.styles = PREVIEW_STYLE\n    except SymbolError:\n        preview.object = r"$\\text{invalid}$"\n        preview.styles = PREVIEW_ERROR_STYLE\n\n\ndef make_row(name_value="", unit_value=""):\n    index = len(rows) + 1\n    name = pn.widgets.TextInput(\n        name=f"Variable {index}", value=name_value, placeholder=r"e.g. \\rho", width=150\n    )\n    unit = pn.widgets.TextInput(\n        name="Dimensions / units",\n        value=unit_value,\n        placeholder="e.g. kg/m^3",\n        description=UNIT_TIP,\n        width=240,\n    )\n    require = pn.widgets.Checkbox(name="", value=False, width=165, align="center")\n    preview_text = "$" + symbol_latex(name_value) + "$" if name_value else r"$\\text{preview}$"\n    preview = pn.pane.LaTeX(\n        preview_text,\n        renderer="katex",\n        width=105,\n        height=42,\n        styles=PREVIEW_STYLE if name_value else PREVIEW_STYLE | {"color": "#9ca3a7"},\n    )\n    name.param.watch(lambda event, pane=preview: update_preview(event, pane), "value")\n    for widget in (name, unit, require):\n        widget.param.watch(mark_example_edited, "value")\n    row_layout = pn.Row(name, unit, require, preview, sizing_mode="stretch_width")\n    return name, unit, require, preview, row_layout\n\n\ndef refresh_table():\n    heading = pn.Row(\n        pn.pane.Markdown("**Variable**", width=150),\n        pn.pane.Markdown("**Dimensions / units**", width=240),\n        pn.pane.Markdown("**Require exponent = 1**", width=165),\n        pn.pane.Markdown("**Preview**", width=105),\n        sizing_mode="stretch_width",\n    )\n    table.objects = [heading, *[row[4] for row in rows], add]\n\n\ndef load_example(event=None):\n    global loading_example\n    loading_example = True\n    rows.clear()\n    for name_value, unit_value in EXAMPLES[example.value]:\n        rows.append(make_row(name_value, unit_value))\n    refresh_table()\n    example.stylesheets = []\n    loading_example = False\n    calculate_groups()\n\n\ndef add_row(event=None):\n    rows.append(make_row())\n    refresh_table()\n    mark_example_edited()\n\n\ndef result_table(answers):\n    answer = answers[0]\n    summary = pn.pane.HTML(\n        f'<h2>Result</h2><p>{len(answer.names)} variables, rank {answer.rank}: '\n        f'<strong>{answer.group_count} independent dimensionless group(s)</strong>, shown in '\n        f'<strong>{len(answers)} admissible form(s)</strong>.</p>'\n    )\n    header = pn.Row(\n        pn.pane.HTML("Option", width=80, styles=HEADER_STYLE),\n        *[\n            pn.pane.HTML(f"&Pi;<sub>{i}</sub>", width=220, styles=HEADER_STYLE)\n            for i in range(1, answer.group_count + 1)\n        ],\n    )\n    option_rows = []\n    for row_number, option in enumerate(answers, 1):\n        cells = [\n            pn.pane.LaTeX(\n                "$" + group.expression_latex(list(option.names)) + "$",\n                renderer="katex",\n                width=220,\n                height=52,\n                styles=MATH_CELL_STYLE,\n            )\n            for group in option.groups\n        ]\n        option_rows.append(\n            pn.Row(\n                pn.pane.HTML(str(row_number), width=80, styles=OPTION_STYLE),\n                *cells,\n            )\n        )\n    note = pn.pane.HTML(\n        "<small>Each row is a complete independent set. Equivalent rows differ only in the chosen basis.</small>"\n    )\n    grid = pn.Column(header, *option_rows, styles={"overflow-x": "auto"})\n    return pn.Column(summary, grid, note, styles={"background": "white", "border": "1px solid #d9deda", "border-radius": "10px", "padding": "16px 18px"})\n\n\ndef calculate_groups(event=None):\n    variables = [\n        (name.value, unit.value)\n        for name, unit, _, _, _ in rows\n        if name.value.strip() or unit.value.strip()\n    ]\n    preferred = [\n        name.value\n        for name, _, require, _, _ in rows\n        if require.value and name.value.strip()\n    ]\n    try:\n        if any(not name.strip() or not unit.strip() for name, unit in variables):\n            raise ValueError("Each row needs both a variable name and a unit expression")\n        answers = analyze_options(variables, preferred)\n        result.objects = [result_table(answers)]\n    except (ValueError, UnitError, SymbolError) as exc:\n        result.objects = [\n            pn.pane.HTML(\n                f'<div class="bkpi-error"><strong>Check the input:</strong> {escape(str(exc))}</div>'\n            )\n        ]\n\n\ndef clear_rows(event=None):\n    for name, unit, require, _, _ in rows:\n        name.value = ""\n        unit.value = ""\n        require.value = False\n    result.objects = []\n    mark_example_edited()\n\n\nexample.param.watch(load_example, "value")\ncalculate.on_click(calculate_groups)\nclear.on_click(clear_rows)\nadd.on_click(add_row)\n\napp = pn.Column(\n    pn.pane.HTML(\n        '<div class="bkpi-hero"><h1>BuckPi</h1><p>Dimensional analysis using the Buckingham &Pi; theorem</p></div>'\n    ),\n    pn.Row(example, pn.Spacer(width=12), clear),\n    pn.pane.HTML(\n        '<div class="bkpi-card"><p>Enter each variable using ordinary text or LaTeX-style notation such as '\n        '<code>\\\\rho</code>, <code>c_p</code>, <code>U_{\\\\infty}</code>, or <code>\\\\Delta p</code>. '\n        'Enter units separately using expressions such as <code>m/s</code>, <code>kg/m^3</code>, '\n        '<code>Pa*s</code>, or <code>N/m</code>. By default, every admissible set of &Pi; groups is shown.</p></div>'\n    ),\n    pn.pane.HTML(\n        '<details class="bkpi-card"><summary><strong>What unit inputs are accepted?</strong></summary>'\n        f'<p>{escape(UNIT_TIP)}</p></details>'\n    ),\n    table,\n    calculate,\n    result,\n    pn.pane.Markdown(\n        "Exact rational linear algebra runs locally in your browser. No data is uploaded.  \\n"\n        "Tim Colonius \xb7 California Institute of Technology"\n    ),\n    max_width=920,\n    margin=(20, 0),\n)\n\nload_example()\napp.servable(title="BuckPi \u2014 Dimensional Analysis")\n\n\nawait write_doc()
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