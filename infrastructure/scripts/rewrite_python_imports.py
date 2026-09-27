"""One-shot import rewriter for ai-service package migration."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "apps" / "ai-service"
PACKAGES = [
    "agents",
    "analysis",
    "api",
    "evidence",
    "graph",
    "prompts",
    "providers",
    "rag",
    "schemas",
    "storage",
    "tools",
    "utils",
    "evaluation",
]


def rewrite(text: str) -> str:
    out = text
    # config module
    out = re.sub(r"\bfrom config(\b|\.)", r"from app.config\1", out)
    out = re.sub(r"\bimport config\b(?!\s+as)", "import app.config as config", out)

    for pkg in PACKAGES:
        out = re.sub(rf"\bfrom {pkg}(\b|\.)", rf"from app.{pkg}\1", out)
        out = re.sub(rf"\bimport {pkg}\b(?!\s+as)", rf"import app.{pkg} as {pkg}", out)

    # undo double-prefix
    out = out.replace("from app.app.", "from app.")
    out = out.replace("import app.app.", "import app.")
    return out


def main() -> None:
    changed: list[str] = []
    for path in ROOT.rglob("*.py"):
        if any(p in path.parts for p in (".venv", "__pycache__", "node_modules")):
            continue
        original = path.read_text(encoding="utf-8")
        updated = rewrite(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed.append(str(path.relative_to(ROOT)))
    print(f"Updated {len(changed)} files")
    for c in changed:
        print(" ", c)


if __name__ == "__main__":
    main()
