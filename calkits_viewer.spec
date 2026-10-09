# Compatibility spec: use the maintained packaging/calkits_viewer.spec.
from pathlib import Path
spec = Path(SPECPATH) / 'packaging' / 'calkits_viewer.spec'
SPECPATH = str(spec.parent)
exec(compile(spec.read_text(encoding='utf-8'), str(spec), 'exec'))
