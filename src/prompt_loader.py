from __future__ import annotations

import re
from pathlib import Path


def render_prompt(template_path: Path, variables: dict[str, str]) -> str:
    template = template_path.read_text(encoding="utf-8")
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace(f"{{{key}}}", value)

    # Detect unresolved placeholder-like tokens such as {title}.
    unresolved = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", rendered)
    if unresolved:
        missing = sorted(set(unresolved))
        raise ValueError(f"Prompt template missing variables: {', '.join(missing)}")

    return rendered.strip()
