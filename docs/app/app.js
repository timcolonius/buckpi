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
  const env_spec = ['https://cdn.holoviz.org/panel/wheels/bokeh-3.4.3-py3-none-any.whl', 'https://cdn.holoviz.org/panel/1.4.5/dist/wheels/panel-1.4.5-py3-none-any.whl', 'pyodide-http==0.2.1', './buckpi-0.1.0-py3-none-any.whl']
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
  \nimport asyncio\n\nfrom panel.io.pyodide import init_doc, write_doc\n\ninit_doc()\n\nfrom html import escape\n\nimport panel as pn\n\nfrom buckpi import UnitError, analyze\n\npn.extension(sizing_mode="stretch_width")\n\nCOLORS = {"ink": "#17212b", "blue": "#176b87", "pale": "#eef6f7", "gold": "#d8a529"}\npn.config.raw_css.append("""\n:root { --buck-ink: #17212b; --buck-blue: #176b87; }\nbody { background: #f7f8f6; }\n.bkpi-hero { padding: 22px 26px; border-left: 6px solid #d8a529; background: linear-gradient(120deg,#e7f2f3,#f8f5ea); border-radius: 10px; }\n.bkpi-hero h1 { color:#17212b; margin:0 0 4px; font-size:32px; }\n.bkpi-hero p { color:#53606a; margin:0; }\n.bkpi-card { background:white; border:1px solid #d9deda; border-radius:10px; padding:16px 18px; }\n.bkpi-result { background:#eef6f7; border-left:4px solid #176b87; border-radius:6px; padding:10px 16px; margin:8px 0; font-size:18px; }\n.bkpi-error { background:#fff0ee; border-left:4px solid #b44335; padding:12px 16px; border-radius:6px; }\n""")\n\nEXAMPLES = {\n    "Sphere volume": [("V", "m^3"), ("R", "m")],\n    "Pendulum": [("T", "s"), ("L", "m"), ("g", "m/s^2")],\n    "Drag force": [("F", "N"), ("rho", "kg/m^3"), ("U", "m/s"), ("L", "m"), ("mu", "Pa*s")],\n    "Surface gravity waves": [("c_p", "m/s"), ("lambda", "m"), ("g", "m/s^2"), ("h", "m"), ("rho", "kg/m^3"), ("sigma", "N/m")],\n}\n\nrows = []\nfor index in range(10):\n    name = pn.widgets.TextInput(name=f"Variable {index + 1}", placeholder="e.g. U", width=150)\n    unit = pn.widgets.TextInput(name="Dimensions / units", placeholder="e.g. m/s", width=240)\n    repeat = pn.widgets.Checkbox(name="Prefer as repeating", width=165)\n    rows.append((name, unit, repeat))\n\nexample = pn.widgets.Select(name="Load an example", options=list(EXAMPLES), value="Pendulum", width=280)\ncalculate = pn.widgets.Button(name="Find dimensionless groups", button_type="primary", width=250)\nclear = pn.widgets.Button(name="Clear", button_type="light", width=90)\nresult = pn.pane.HTML("", sizing_mode="stretch_width")\n\n\ndef load_example(event=None):\n    values = EXAMPLES[example.value]\n    for index, (name, unit, repeat) in enumerate(rows):\n        name.value, unit.value, repeat.value = (values[index][0], values[index][1], False) if index < len(values) else ("", "", False)\n    calculate_groups()\n\n\ndef calculate_groups(event=None):\n    variables = [(name.value, unit.value) for name, unit, _ in rows if name.value.strip() or unit.value.strip()]\n    preferred = [name.value for name, _, repeat in rows if repeat.value and name.value.strip()]\n    try:\n        if any(not name.strip() or not unit.strip() for name, unit in variables):\n            raise ValueError("Each row needs both a variable name and a unit expression")\n        answer = analyze(variables, preferred)\n        group_html = "".join(\n            f'<div class="bkpi-result"><strong>&Pi;<sub>{i}</sub></strong> = {escape(group.expression(list(answer.names)))}</div>'\n            for i, group in enumerate(answer.groups, 1)\n        )\n        repeats = ", ".join(map(escape, answer.repeating_variables)) or "none"\n        result.object = (\n            f'<div class="bkpi-card"><h2>Result</h2><p>{len(answer.names)} variables, rank {answer.rank}: '\n            f'<strong>{answer.group_count} independent dimensionless group(s)</strong>.</p>{group_html}'\n            f'<p><small>Repeating variables used: {repeats}. Equivalent sets of &Pi; groups are possible.</small></p></div>'\n        )\n    except (ValueError, UnitError) as exc:\n        result.object = f'<div class="bkpi-error"><strong>Check the input:</strong> {escape(str(exc))}</div>'\n\n\ndef clear_rows(event=None):\n    for name, unit, repeat in rows:\n        name.value, unit.value, repeat.value = "", "", False\n    result.object = ""\n\n\nexample.param.watch(load_example, "value")\ncalculate.on_click(calculate_groups)\nclear.on_click(clear_rows)\n\ntable = pn.Column(\n    pn.Row(pn.pane.Markdown("**Variable**", width=150), pn.pane.Markdown("**Dimensions / units**", width=240), pn.pane.Markdown("**Repeating variable**", width=165)),\n    *[pn.Row(name, unit, repeat) for name, unit, repeat in rows],\n)\n\napp = pn.Column(\n    pn.pane.HTML('<div class="bkpi-hero"><h1>BuckPi</h1><p>Dimensional analysis using the Buckingham &Pi; theorem</p></div>'),\n    pn.Row(example, pn.Spacer(width=12), clear),\n    pn.pane.HTML('<div class="bkpi-card"><p>Enter each physical variable and its units. Use familiar expressions such as <code>m/s</code>, <code>kg/m^3</code>, <code>Pa*s</code>, or <code>N/m</code>. Optionally choose variables you prefer in the repeating set.</p></div>'),\n    table,\n    calculate,\n    result,\n    pn.pane.Markdown("Exact rational linear algebra runs locally in your browser. No data is uploaded.  \\nTim Colonius \xb7 California Institute of Technology"),\n    max_width=920,\n    margin=(20, 0),\n)\n\nload_example()\napp.servable(title="BuckPi \u2014 Dimensional Analysis")\n\n\nawait write_doc()
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