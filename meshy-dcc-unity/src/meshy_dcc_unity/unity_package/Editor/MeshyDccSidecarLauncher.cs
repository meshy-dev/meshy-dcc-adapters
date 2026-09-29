using System;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace MeshyDcc.Unity
{
    internal static class MeshyDccSidecarLauncher
    {
        internal static void StartIfConfigured()
        {
            if (MeshyDccBridge.IsImportWorkerOrBatchMode())
            {
                return;
            }
            var path = Environment.GetEnvironmentVariable("MESHY_DCC_UNITY_SIDECAR_PATH");
            if (string.IsNullOrEmpty(path))
            {
                return;
            }

            try
            {
                path = Path.GetFullPath(path);
                if (!File.Exists(path))
                {
                    UnityEngine.Debug.LogWarning("Meshy DCC Unity sidecar was not found: " + path);
                    return;
                }

                var expected = Environment.GetEnvironmentVariable("MESHY_DCC_UNITY_SIDECAR_SHA256");
                if (!string.IsNullOrEmpty(expected) && !string.Equals(
                        expected.Trim(), ComputeSha256(path), StringComparison.OrdinalIgnoreCase))
                {
                    UnityEngine.Debug.LogError("Meshy DCC Unity sidecar SHA-256 validation failed.");
                    return;
                }

                var bridgePort = Environment.GetEnvironmentVariable("MESHY_DCC_UNITY_BRIDGE_PORT") ?? "13852";
                var pidFile = Path.Combine(
                    Path.GetTempPath(),
                    "meshy-dcc-unity-" + ComputeProjectHash(Application.dataPath) + ".pid");
                var arguments = "--bridge-port " + bridgePort + " --watch-pid " +
                    Process.GetCurrentProcess().Id + " --pid-file \"" + pidFile + "\"";
                var startInfo = new ProcessStartInfo
                {
                    FileName = path,
                    Arguments = arguments,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WorkingDirectory = Path.GetDirectoryName(path) ?? Environment.CurrentDirectory,
                };
                Process.Start(startInfo);
                UnityEngine.Debug.Log("Meshy DCC Unity standalone sidecar started.");
            }
            catch (Exception exception)
            {
                MeshyDccBootstrapErrors.Capture("sidecar-launch", exception);
                UnityEngine.Debug.LogWarning("Meshy DCC Unity sidecar failed to start: " + exception.Message);
            }
        }

        private static string ComputeSha256(string path)
        {
            using (var sha256 = SHA256.Create())
            using (var stream = File.OpenRead(path))
            {
                return BitConverter.ToString(sha256.ComputeHash(stream)).Replace("-", string.Empty)
                    .ToLowerInvariant();
            }
        }

        private static string ComputeProjectHash(string path)
        {
            using (var sha256 = SHA256.Create())
            {
                var bytes = Encoding.UTF8.GetBytes(Path.GetFullPath(path).ToLowerInvariant());
                return BitConverter.ToString(sha256.ComputeHash(bytes), 0, 8)
                    .Replace("-", string.Empty).ToLowerInvariant();
            }
        }
    }
}
