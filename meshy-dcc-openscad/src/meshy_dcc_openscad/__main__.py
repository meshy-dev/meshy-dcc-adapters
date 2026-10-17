"""``meshy-dcc-openscad``: the adapter service, a project setup, or a lifecycle verb."""

from __future__ import annotations

import sys
from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["install-project"]:
        from .project import install_project

        return install_project(arguments[1:])
    if arguments[:1] == ["serve"]:
        from .project import serve

        return serve(arguments[1:])
    from .server import main as lifecycle_main

    return lifecycle_main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
