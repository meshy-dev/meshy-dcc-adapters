"""Control structured PIE playtest episode lifetime."""

from __future__ import annotations

from _playtest_runtime import episode_summary, finish_episode, get_episode, start_episode
from meshy_dcc_core.skill import skill_entry

from meshy_dcc_unreal.api import missing_param_error, unreal_error, unreal_from_exception, unreal_success
from meshy_dcc_unreal.pie_session import PieSessionUnavailableError, pie_session_error


@skill_entry
def playtest_episode_control(action: str = "", episode_id: str = "", **kwargs) -> dict:
    if not action:
        return missing_param_error("action")
    try:
        normalized = str(action).strip().lower()
        if normalized == "start":
            context = start_episode(**kwargs)
            return unreal_success("Structured PIE playtest episode started", **context)
        if normalized == "current":
            if not episode_id:
                return missing_param_error("episode_id")
            return unreal_success(
                "Structured PIE playtest episode is active", **episode_summary(get_episode(episode_id))
            )
        if normalized == "finish":
            if not episode_id:
                return missing_param_error("episode_id")
            return unreal_success("Structured PIE playtest episode finished", **finish_episode(episode_id))
        return unreal_error("Unsupported episode action: {}".format(action))
    except PieSessionUnavailableError as exc:
        return pie_session_error(exc)
    except Exception as exc:
        return unreal_from_exception(exc, "Failed to control the structured PIE playtest episode")
