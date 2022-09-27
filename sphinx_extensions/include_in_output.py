#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Include In Output Sphinx Extension

This extension allows you to include relatively referenced files in the output
directory.

Usage with MyST:

```markdown
{include-in-output}`v1-maiden-6-9-21.bin`

Dear readers, please download the [provided binary file](v1-maiden-6-9-21.bin).
```

Including in jupyter-book:
```python
# _config.yml

...

sphinx:
  extra_extensions:
    - include_in_output
...

```
"""

from pathlib import Path
import shutil
from docutils.nodes import reference


def resolve_asset_path(asset_path: Path, source_path: Path, src_dir: Path, out_dir: Path):
    if not asset_path.is_absolute():
        asset_path = source_path.parent / asset_path
        asset_path_relative = asset_path.relative_to(src_dir)
    else:
        asset_path_relative = str(asset_path).removeprefix('/')
    asset_path_src = src_dir / asset_path_relative
    asset_path_out = out_dir / asset_path_relative
    return (asset_path_src, asset_path_out)


def include_in_output_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    app = inliner.document.settings.env.app
    asset_path_src, asset_path_out = resolve_asset_path(
        Path(text), Path(inliner.document.attributes["source"]),
        Path(app.srcdir), Path(app.outdir)
    )
    
    print(f"Copying {asset_path_src} to {asset_path_out}")
    print(f"Creating {asset_path_out.parent}")
    asset_path_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(asset_path_src, asset_path_out)
    inliner.reporter.info(f"Included {asset_path_src} in output")
    return [], []


def missing_reference_handler(app, env, node, contnode):
    _asset_path_src, asset_path_out = resolve_asset_path(
        Path(node["reftarget"]), Path(contnode.source),
        Path(app.srcdir), Path(app.outdir)
    )
    
    if not asset_path_out.exists():
        return None

    return reference(node.rawsource, "", contnode, internal=True, refuri=node["reftarget"])


def setup(app):
    app.connect("missing-reference", missing_reference_handler)
    app.add_role("include-in-output", include_in_output_role)
