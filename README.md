# BuckPi

BuckPi is a Python implementation of the Buckingham Pi dimensional-analysis
tool, with an interactive Panel app that runs entirely in the browser through
Pyodide.

## Python use

```python
from buckpi import analyze_options

options = analyze_options([
    ("T", "s"),
    ("L", "m"),
    ("g", "m/s^2"),
])

for option in options:
    print([group.expression(list(option.names)) for group in option.groups])
```

By default, `analyze_options` returns every admissible basis, matching the table
produced by `Buck.nb`. Unit expressions may use `*`, `/`, parentheses, and
powers—for example `m/s`, `kg/m^3`, `Pa*s`, and `N/m`. Calculations use exact
rational arithmetic.

## Local development

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/panel serve app.py --dev --show
```

Run the tests with:

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

## GitHub Pages

GitHub Pages serves this project from `docs/`:

- Landing page: `/`
- Interactive app: `/app/`

Build the browser version with `scripts/build_static.sh`, commit `docs/app/`,
then configure the repository's Pages source as the `main` branch `/docs`
folder.
