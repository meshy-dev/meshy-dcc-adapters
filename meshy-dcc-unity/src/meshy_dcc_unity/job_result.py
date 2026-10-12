import math
import os
import time
from datetime import datetime, timezone
from typing import Any

from meshy_dcc_core import DeferredToolResult
from meshy_dcc_core.bridge import BridgeConnectionError, BridgeRpcError, BridgeTimeoutError
from meshy_dcc_core.skill import skill_error, skill_success

from meshy_dcc_unity.bridge import call_host, host_unresponsive_since


def _unresponsive_limit_secs() -> float:
    # A domain reload or script compile stalls the main thread for seconds to about a
    # minute, and one bridge call may wait 60 s; 120 s is past both and far below the
    # 600 s CLI wait and the 3600 s job timeout.
    value = float(os.environ.get("MESHY_DCC_UNITY_UNRESPONSIVE_SECS", "120"))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("MESHY_DCC_UNITY_UNRESPONSIVE_SECS must be a positive number of seconds")
    return value


def _host_unresponsive_result(action: str, request_id: Any, error: Exception):
    """End the wait: Unity's main thread has not answered for too long."""
    since = host_unresponsive_since()
    if since is None:
        return None
    silent = time.time() - since
    if silent < _unresponsive_limit_secs():
        return None
    return skill_error(
        f"{action} stopped waiting: the Unity Editor main thread "
        f"has not answered for {silent:.0f} s.",
        str(error),
        prompt=(
            "Unity may be showing a modal dialog or be stuck in a long import. The Unity job may "
            "still finish. When Unity answers again, call unity_diagnostics__inspect_job with the "
            "same request_id instead of submitting the job again."
        ),
        reason="host_unresponsive",
        request_id=request_id,
        host_unresponsive_since=datetime.fromtimestamp(since, timezone.utc).isoformat(),
    )


def job_state_result(action: str, result: dict[str, Any]):
    state = result.get("state")
    if state not in {"queued", "running", "succeeded", "failed"}:
        context = dict(result)
        error = str(context.pop("error", repr(state)))
        context["returned_state"] = context.pop("state", None)
        return skill_error(
            f"{action} returned an invalid job state.",
            error,
            **context,
        )
    if state in {"queued", "running"}:
        request_id = result.get("request_id")

        def check_is_finished():
            try:
                snapshot = call_host("jobs.inspect", {"request_id": request_id})
            except (BridgeConnectionError, BridgeTimeoutError) as exception:
                # Also frees the sidecar's main lane, which this wait occupies.
                return _host_unresponsive_result(action, request_id, exception)
            except BridgeRpcError as exception:
                if (
                    exception.code == -32000
                    and exception.message == f"Unity job was not found for request_id: {request_id}"
                ):
                    return None
                raise
            if snapshot.get("state") in {"queued", "running"}:
                return None
            return job_state_result(action, snapshot)

        return DeferredToolResult(
            check_is_finished=check_is_finished,
            timeout_secs=3600,
            poll_interval_secs=0.25,
        )
    message = f"{action} job state returned: {state}."
    if state == "failed":
        context = dict(result)
        error = str(context.pop("error", "Unity job failed without an error message."))
        return skill_error(message, error, **context)
    return skill_success(message, **result)
