using System;
using System.IO;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace MeshyDcc.Unity
{
    internal static class MeshyDccBootstrapErrors
    {
        internal static void Capture(string stage, Exception exception)
        {
            try
            {
                var projectPath = Path.GetDirectoryName(Application.dataPath) ?? string.Empty;
                var directory = Path.Combine(projectPath, "Library", "MeshyDcc");
                Directory.CreateDirectory(directory);
                var payload = new JObject
                {
                    ["schema_version"] = "1",
                    ["timestamp_utc"] = DateTime.UtcNow.ToString("O"),
                    ["stage"] = stage,
                    ["exception_type"] = exception.GetType().FullName,
                    ["message"] = exception.Message,
                };
                File.AppendAllText(
                    Path.Combine(directory, "bootstrap-errors.jsonl"),
                    payload.ToString(Formatting.None) + Environment.NewLine);
            }
            catch (Exception captureException)
            {
                Debug.LogWarning(
                    "Meshy DCC Unity could not persist its bootstrap diagnostic: "
                    + captureException.Message);
            }
        }
    }
}
