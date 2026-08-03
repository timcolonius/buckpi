from pathlib import Path
import hashlib
import re
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
app_dir = root / "docs" / "app"

dist = root / "dist"
dist.mkdir(exist_ok=True)
subprocess.run(
    [sys.executable, "-m", "pip", "wheel", ".", "-w", str(dist), "--no-deps"],
    cwd=root,
    check=True,
)
wheel = sorted(dist.glob("buckpi-*.whl"))[-1]
wheel_digest = hashlib.sha256(wheel.read_bytes()).hexdigest()[:10]
wheel_parts = wheel.name.split("-")
versioned_wheel_name = "-".join(wheel_parts[:2] + [f"1{wheel_digest}"] + wheel_parts[2:])
for old_wheel in app_dir.glob("buckpi-*.whl"):
    old_wheel.unlink()
target_wheel = app_dir / versioned_wheel_name
shutil.copy2(wheel, target_wheel)

worker = app_dir / "app.js"
text = worker.read_text()
wheel_ref = f"'./{versioned_wheel_name}'"
if wheel_ref not in text:
    match = re.search(r"const env_spec = \[(.*?)\]", text, flags=re.DOTALL)
    if match is not None:
        current = match.group(1).rstrip()
        replacement = current + (", " if current else "") + wheel_ref
        worker.write_text(text[:match.start(1)] + replacement + text[match.end(1):])
    else:
        match = re.search(r"await micropip\.install\(\[(.*?)\]\);", text, flags=re.DOTALL)
        if match is None:
            raise RuntimeError("Could not find the worker dependency list")
        current = match.group(1).rstrip()
        replacement = current + (", " if current else "") + wheel_ref
        worker.write_text(text[:match.start(1)] + replacement + text[match.end(1):])

app_html = app_dir / "app.html"
if not app_html.exists():
    raise FileNotFoundError("Panel did not generate docs/app/app.html")
worker_digest = hashlib.sha256(worker.read_bytes()).hexdigest()[:10]
html_text = app_html.read_text()
html_text = html_text.replace('./app.js', f'./app.js?v={worker_digest}')
app_html.write_text(html_text)
shutil.copy2(app_html, app_dir / "index.html")

(root / "docs" / ".nojekyll").touch()
