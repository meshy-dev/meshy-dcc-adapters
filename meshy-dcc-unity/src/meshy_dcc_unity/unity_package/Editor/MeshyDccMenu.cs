using System;
using UnityEditor;
using UnityEngine;

namespace MeshyDcc.Unity
{
    internal static class MeshyDccMenu
    {
        private const string AdapterVersion = "0.1.1";
        private const string ProjectUrl = "https://github.com/meshy-dev/meshy-dcc-adapters/tree/main/meshy-dcc-unity";
        private const string DefaultBridgeUrl = "ws://127.0.0.1:13852";

        [MenuItem("Meshy DCC/Copy Instance ID", false, 0)]
        private static void CopyInstanceId()
        {
            var instanceId = MeshyDccBridge.GetSessionInstanceId();
            GUIUtility.systemCopyBuffer = instanceId;
            Debug.Log("Meshy DCC: Instance ID copied to clipboard: " + instanceId);
        }

        [MenuItem("Meshy DCC/Server Info", false, 1)]
        private static void ShowServerInfo()
        {
            var instanceId = MeshyDccBridge.GetSessionInstanceId();
            var bridgeUrl = Environment.GetEnvironmentVariable("MESHY_DCC_UNITY_BRIDGE_URL");
            if (string.IsNullOrEmpty(bridgeUrl))
            {
                bridgeUrl = DefaultBridgeUrl;
            }

            var info = string.Join("\n", new[]
            {
                "Instance UUID: " + instanceId,
                "Unity: " + Application.unityVersion,
                "Project: " + Application.productName,
                "PID: " + System.Diagnostics.Process.GetCurrentProcess().Id,
                "Bridge URL: " + bridgeUrl,
                "Adapter: meshy-dcc-unity " + AdapterVersion,
            });

            EditorUtility.DisplayDialog("Meshy DCC — Server Info", info, "OK");
        }

        [MenuItem("Meshy DCC/About Meshy DCC", false, 12)]
        private static void ShowAbout()
        {
            var about = string.Join("\n", new[]
            {
                "meshy-dcc-unity v" + AdapterVersion,
                "Unity " + Application.unityVersion,
                "",
                "Meshy DCC — AI-driven DCC automation.",
                ProjectUrl,
            });

            EditorUtility.DisplayDialog("About Meshy DCC", about, "OK");
        }
    }
}
