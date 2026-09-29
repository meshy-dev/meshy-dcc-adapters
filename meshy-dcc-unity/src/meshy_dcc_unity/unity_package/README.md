# Meshy DCC Unity Editor package

This embedded UPM package connects Unity Editor to the loopback Meshy DCC bridge. It exposes only
the typed operations implemented in `MeshyDccCommands`; it does not evaluate arbitrary C#.

The bridge URL defaults to `ws://127.0.0.1:13852` and can be overridden with the
`MESHY_DCC_UNITY_BRIDGE_URL` environment variable before Unity starts.

Long or domain-reloading mutations use one `SessionState` job ledger. Callers provide a UUID
`request_id`, receive a real queued/running/succeeded/failed snapshot, and inspect the same ID after
reconnect. Only one mutating job runs at a time, and an ID cannot be reused with different inputs.

UTF-8 source writes are off unless the Unity process inherits
`MESHY_DCC_UNITY_ALLOW_SOURCE_WRITES=1`. They are limited to allowlisted files below `Assets`, 256 KiB,
JSON-safe text, compare-and-swap, atomic replacement, and non-reparse paths. Windows builds switch
target when needed and use saved, non-dirty enabled Build Settings scenes in new directories below
`Builds/MeshyDcc`; Game View PNG capture requires active, unpaused Play Mode and is decoded within
fixed file, dimension, and pixel limits before success is reported.

The per-asset lock is cooperative between Meshy DCC writers. A same-user process that ignores it or
swaps a junction or symlink between validation and operating-system path resolution is outside the
in-process boundary. Detected replacement races never trigger automatic rollback: displaced bytes
remain in a unique `.meshydcc-*.backup` conflict backup, and the target is not written again after
detection. A conflict failure is ambiguous, so inspect both files before submitting another write.
