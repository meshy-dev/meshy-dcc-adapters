"""Policy for tools that run caller-supplied code.

``MESHY_DCC_MAYA_DISABLE_ARBITRARY_SCRIPT=1`` refuses every tool listed in
:data:`CODE_BEARING_TOOLS`: a caller-supplied string reaches a Maya code
evaluator (``cmds.expression``, ``cmds.scriptNode``, ``exec``/``eval``,
``mel.eval``), or a tool runs or imports project code or loads a plug-in. A MEL
expression can embed ``python(...)``, so the check is at the tool boundary
rather than a filter on the string.

This is a tool-surface policy for operators, not a sandbox: code already in the
session (loaded plug-ins, scene script nodes, ``userSetup.py``) is out of scope.
Typed and read-only tools stay available. ``attach_project``, ``unload_plugin``
and ``list_plugins`` run no code and are not gated.

To add a code-bearing tool, list it here and call
:func:`arbitrary_script_refusal` at the start of its function.
``tests/test_arbitrary_script_policy.py`` scans the shipped catalog for tools
that use a code-evaluation primitive without being listed.
"""

from __future__ import annotations

from typing import Optional

from meshy_dcc_core.skill import skill_error

from meshy_dcc_maya._env import ENV_DISABLE_ARBITRARY_SCRIPT, resolve_arbitrary_script_disabled

#: ``get_script_node`` is code-bearing for ``action="create"`` only.
CODE_BEARING_TOOLS = (
    "create_expression",
    "edit_expression",
    "execute_mel",
    "execute_python",
    "get_script_node",
    "introspect_eval",
    "load_plugin",
    "reload_modules",
    "run_check",
    "run_entrypoint",
    "run_script",
    "start_debugpy",
    "write_module",
)


def arbitrary_script_refusal(tool_name: str) -> Optional[dict]:
    """Return a refusal when the policy blocks ``tool_name``, else ``None``.

    The environment is read on every call, so no state is cached.
    """
    if tool_name not in CODE_BEARING_TOOLS or not resolve_arbitrary_script_disabled():
        return None
    return skill_error(
        "{} is disabled by operator policy".format(tool_name),
        "Unset {} to re-enable code-bearing tools in this Maya adapter. "
        "This flag is a tool policy, not a host sandbox.".format(ENV_DISABLE_ARBITRARY_SCRIPT),
        possible_solutions=[
            "Use search_skills -> load_skill -> typed tools instead.",
            "Read-only tools such as list_expressions remain available.",
        ],
        tool_name=tool_name,
    )
