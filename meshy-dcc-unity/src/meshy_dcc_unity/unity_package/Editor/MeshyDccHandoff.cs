using System;
using System.IO;
using System.Diagnostics;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace MeshyDcc.Unity
{
    // Meshy additions to the bridge: project bootstrap, session, stop and model handoff.
    internal static class MeshyDccHandoff
    {
        // Point the sidecar launcher at the runtime `meshy-dcc install --project`
        // recorded for this project. A value already in the environment wins.
        internal static void Configure()
        {
            if (!string.IsNullOrEmpty(Environment.GetEnvironmentVariable("MESHY_DCC_UNITY_SIDECAR_PATH"))) return;
            var root = Path.GetDirectoryName(Application.dataPath);
            var file = Path.Combine(Path.Combine(root, ".meshy-dcc"), "unity.json");
            if (!File.Exists(file)) return;
            if ((File.GetAttributes(file) & FileAttributes.ReparsePoint) != 0 ||
                (File.GetAttributes(Path.GetDirectoryName(file)) & FileAttributes.ReparsePoint) != 0)
                throw new InvalidOperationException("Meshy DCC configuration cannot be a symlink.");
            var config = JObject.Parse(File.ReadAllText(file));
            if ((string)config["owner"] != "meshy-dcc-unity")
                throw new InvalidOperationException("Meshy DCC configuration has an unknown owner.");
            foreach (var key in new[] { "MESHY_DCC_UNITY_SIDECAR_PATH", "MESHY_DCC_UNITY_SIDECAR_SHA256" })
            {
                var value = (string)config["environment"]?[key];
                if (!string.IsNullOrEmpty(value)) Environment.SetEnvironmentVariable(key, value);
            }
        }

        private static void Ready()
        {
            if (EditorApplication.isCompiling || EditorApplication.isUpdating || EditorApplication.isPlayingOrWillChangePlaymode)
                throw new InvalidOperationException("Wait for the Editor to be idle in Edit Mode.");
        }

        internal static JObject Session()
        {
            var scene = SceneManager.GetActiveScene();
            bool dirty = false;
            for (int i = 0; i < SceneManager.sceneCount; i++) dirty |= SceneManager.GetSceneAt(i).isDirty;
            return new JObject { ["host_pid"] = Process.GetCurrentProcess().Id,
                ["workspace"] = Path.GetDirectoryName(Application.dataPath), ["scene"] = scene.path,
                ["dirty"] = dirty, ["is_playing"] = EditorApplication.isPlayingOrWillChangePlaymode,
                ["is_compiling"] = EditorApplication.isCompiling, ["is_updating"] = EditorApplication.isUpdating,
                ["is_paused"] = EditorApplication.isPaused, ["editor_focused"] = EditorApplication.isFocused,
                ["game_view_focused"] = Application.isFocused, ["run_in_background"] = Application.runInBackground,
                ["frame_count"] = Time.frameCount,
                ["source_writes"] = Environment.GetEnvironmentVariable("MESHY_DCC_UNITY_ALLOW_SOURCE_WRITES") == "1" };
        }

        internal static JObject InspectObject(JObject p)
        {
            Ready();
            var token = p?["instance_id"];
            if (token == null || (token.Type != JTokenType.String && token.Type != JTokenType.Integer))
                throw new InvalidOperationException("Provide a live GameObject instance_id as a decimal string or integer.");
            var id = token.ToString();
            if (id.Length > 20 || !Regex.IsMatch(id, @"^-?[1-9][0-9]*$"))
                throw new InvalidOperationException("instance_id must be a nonzero decimal object ID.");
            var target = MeshyDccObjectIdentity.Resolve(id) as GameObject;
            var scene = SceneManager.GetActiveScene();
            if (!target || EditorUtility.IsPersistent(target) || !scene.IsValid() || !scene.isLoaded || target.scene != scene)
                throw new InvalidOperationException("The GameObject is absent from the active loaded scene; rediscover its current instance ID.");
            var result = Session();
            result["object"] = new JObject
            {
                ["instance_id"] = MeshyDccObjectIdentity.GetId(target),
                ["name"] = target.name,
                ["parent_instance_id"] = target.transform.parent ? MeshyDccObjectIdentity.GetId(target.transform.parent.gameObject) : null,
                ["active"] = target.activeSelf,
                ["active_in_hierarchy"] = target.activeInHierarchy,
                ["child_count"] = target.transform.childCount,
                ["position"] = new JArray(target.transform.position.x, target.transform.position.y, target.transform.position.z),
                ["rotation_euler"] = new JArray(target.transform.eulerAngles.x, target.transform.eulerAngles.y, target.transform.eulerAngles.z),
                ["local_scale"] = new JArray(target.transform.localScale.x, target.transform.localScale.y, target.transform.localScale.z),
            };
            return result;
        }

        private static string HierarchyPath(Transform transform)
        {
            var names = new List<string>();
            while (transform) { names.Add(transform.name); transform = transform.parent; }
            names.Reverse();
            return string.Join("/", names.ToArray());
        }

        private static int InspectionLimit(JObject p, string key, int fallback, int minimum)
        {
            var value = p[key];
            if (value == null) return fallback;
            string message = key + " must be an integer from " + minimum + " to 100.";
            if (value.Type != JTokenType.Integer) throw new InvalidOperationException(message);
            long requested;
            try { requested = value.Value<long>(); }
            catch (Exception error) { throw new InvalidOperationException(message, error); }
            if (requested < minimum || requested > 100) throw new InvalidOperationException(message);
            return (int)requested;
        }

        private static JObject TextureBinding(Material material, string property)
        {
            var texture = material.GetTexture(property);
            if (!texture) return new JObject { ["property"] = property, ["assigned"] = false };
            var assetPath = AssetDatabase.GetAssetPath(texture);
            var importer = string.IsNullOrEmpty(assetPath) ? null : AssetImporter.GetAtPath(assetPath) as TextureImporter;
            return new JObject {
                ["property"] = property, ["assigned"] = true,
                ["texture_instance_id"] = texture.GetInstanceID().ToString(),
                ["texture_name"] = texture.name, ["asset_path"] = assetPath,
                ["width"] = texture.width, ["height"] = texture.height,
                ["importer"] = importer ? new JObject {
                    ["texture_type"] = importer.textureType.ToString(), ["srgb"] = importer.sRGBTexture
                } : null
            };
        }

        private static bool IsUniversalPipeline(RenderPipelineAsset pipeline)
        {
            return pipeline && pipeline.GetType().FullName == "UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset";
        }

        internal static JObject InspectRenderers(JObject p)
        {
            if (p == null) throw new InvalidOperationException("Renderer inspection requires an argument object.");
            int maxFindings = InspectionLimit(p, "max_findings", 20, 1);
            int maxMaterialSlots = InspectionLimit(p, "max_material_slots", 0, 0);
            if (EditorApplication.isCompiling || EditorApplication.isUpdating)
                throw new InvalidOperationException("Wait for Unity compilation and asset updates to finish before inspecting renderers.");
            var scene = SceneManager.GetActiveScene();
            if (!scene.IsValid() || !scene.isLoaded) throw new InvalidOperationException("Unity has no active loaded scene to inspect.");
            var pipeline = GraphicsSettings.currentRenderPipeline;
            bool urp = IsUniversalPipeline(pipeline);

            long rendererCount = 0, slotCount = 0, totalFindings = 0, activeFindings = 0;
            long nullMaterials = 0, missingShaders = 0, errorShaders = 0, unsupportedShaders = 0, pipelineMismatches = 0;
            var findings = new JArray();
            var materialSlots = new JArray();
            foreach (var root in scene.GetRootGameObjects())
            foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
            {
                rendererCount++;
                var materials = renderer.sharedMaterials;
                if (materials == null) continue;
                slotCount += materials.Length;
                for (int i = 0; i < materials.Length; i++)
                {
                    var material = materials[i];
                    var shader = material ? material.shader : null;
                    if (materialSlots.Count < maxMaterialSlots)
                        materialSlots.Add(new JObject {
                            ["object_instance_id"] = renderer.gameObject.GetInstanceID().ToString(),
                            ["hierarchy_path"] = HierarchyPath(renderer.transform),
                            ["renderer_instance_id"] = renderer.GetInstanceID().ToString(),
                            ["material_slot_index"] = i,
                            ["material_instance_id"] = material ? material.GetInstanceID().ToString() : null,
                            ["material_asset_path"] = material ? AssetDatabase.GetAssetPath(material) : null,
                            ["shader_name"] = shader ? shader.name : null,
                            ["standard_textures"] = shader && shader.name == "Standard" ? new JObject {
                                ["base_color"] = TextureBinding(material, "_MainTex"),
                                ["normal"] = TextureBinding(material, "_BumpMap"),
                                ["metallic_smoothness"] = TextureBinding(material, "_MetallicGlossMap")
                            } : null,
                            ["urp_textures"] = shader && shader.name == "Universal Render Pipeline/Lit" ? new JObject {
                                ["base_color"] = TextureBinding(material, "_BaseMap"),
                                ["normal"] = TextureBinding(material, "_BumpMap"),
                                ["metallic_smoothness"] = TextureBinding(material, "_MetallicGlossMap")
                            } : null
                        });
                    // ponytail: only the two handoff shaders; extend after native validation of another pipeline/shader pair.
                    bool mismatch = shader && ((urp && shader.name == "Standard") ||
                        (!pipeline && shader.name == "Universal Render Pipeline/Lit"));
                    string kind = !material ? "null_material" : !shader ? "missing_shader" :
                        shader.name == "Hidden/InternalErrorShader" ? "error_shader" : mismatch ? "pipeline_mismatch" :
                        !shader.isSupported ? "unsupported_shader" : null;
                    if (kind == null) continue;
                    totalFindings++;
                    if (renderer.enabled && renderer.gameObject.activeInHierarchy) activeFindings++;
                    if (kind == "null_material") nullMaterials++;
                    else if (kind == "missing_shader") missingShaders++;
                    else if (kind == "error_shader") errorShaders++;
                    else if (kind == "pipeline_mismatch") pipelineMismatches++;
                    else unsupportedShaders++;
                    if (findings.Count >= maxFindings) continue;
                    findings.Add(new JObject {
                        ["kind"] = kind,
                        ["object_instance_id"] = renderer.gameObject.GetInstanceID().ToString(),
                        ["hierarchy_path"] = HierarchyPath(renderer.transform),
                        ["renderer_instance_id"] = renderer.GetInstanceID().ToString(),
                        ["renderer_type"] = renderer.GetType().FullName,
                        ["renderer_enabled"] = renderer.enabled,
                        ["object_active"] = renderer.gameObject.activeInHierarchy,
                        ["object_active_self"] = renderer.gameObject.activeSelf,
                        ["material_slot_index"] = i,
                        ["material_name"] = material ? material.name : null,
                        ["material_instance_id"] = material ? material.GetInstanceID().ToString() : null,
                        ["shader_name"] = shader ? shader.name : null,
                        ["shader_instance_id"] = shader ? shader.GetInstanceID().ToString() : null,
                        ["shader_supported"] = shader ? new JValue(shader.isSupported) : JValue.CreateNull()
                    });
                }
            }
            var result = new JObject {
                ["scene_scope"] = "active_loaded_scene_roots",
                ["scene_name"] = scene.name,
                ["scene_path"] = scene.path,
                ["scene_handle"] = scene.handle.ToString(),
                ["is_playing"] = EditorApplication.isPlaying,
                ["render_pipeline"] = pipeline ? pipeline.GetType().FullName : "Built-in",
                ["renderer_count"] = rendererCount,
                ["material_slot_count"] = slotCount,
                ["null_material_count"] = nullMaterials,
                ["missing_shader_count"] = missingShaders,
                ["error_shader_count"] = errorShaders,
                ["unsupported_shader_count"] = unsupportedShaders,
                ["pipeline_mismatch_count"] = pipelineMismatches,
                ["total_findings"] = totalFindings,
                ["active_findings"] = activeFindings,
                ["truncated"] = totalFindings > findings.Count,
                ["findings"] = findings
            };
            if (maxMaterialSlots > 0) {
                result["material_slots"] = materialSlots;
                result["material_slots_truncated"] = slotCount > materialSlots.Count;
            }
            return result;
        }

        internal static JObject Quit(JObject p)
        {
            var session = Session();
            if ((int?)p["expected_pid"] != (int)session["host_pid"] || (string)p["workspace"] != (string)session["workspace"])
                throw new InvalidOperationException("Refusing to quit a different Editor process or project.");
            var discard = (bool?)p["discard_unsaved"] == true;
            Ready();
            if (!discard && (bool)session["dirty"]) throw new InvalidOperationException("Save dirty scenes before quitting.");
            // Let the bridge return its acknowledgement before Unity closes the sidecar.
            var after = EditorApplication.timeSinceStartup + 1;
            EditorApplication.CallbackFunction close = null;
            close = () => {
                if (EditorApplication.timeSinceStartup < after) return;
                EditorApplication.update -= close;
                if (!discard && (bool)Session()["dirty"]) {
                    UnityEngine.Debug.LogWarning("Meshy quit cancelled: the scene changed after the request.");
                    return;
                }
                EditorApplication.Exit(0);
            };
            EditorApplication.update += close;
            return new JObject { ["quit_requested"] = true, ["host_pid"] = session["host_pid"] };
        }

        private static string AssetPath(JObject p)
        {
            var relative = (string)p["path"];
            if (string.IsNullOrEmpty(relative) || !relative.StartsWith("Assets/", StringComparison.Ordinal) ||
                relative.Contains("\\") || relative.Split('/').Any(s => s == "." || s == ".." || s.Length == 0))
                throw new InvalidOperationException("Use a path below Assets without traversal.");
            var root = Path.GetDirectoryName(Application.dataPath);
            var current = root;
            foreach (var part in relative.Split('/'))
            {
                current = Path.Combine(current, part);
                if ((File.Exists(current) || Directory.Exists(current)) && (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                    throw new InvalidOperationException("Asset paths cannot contain symlinks.");
            }
            return relative;
        }

        private sealed class MaterialPlan
        {
            internal string Output;
            internal int Set;
            internal int SourceSlots;
            internal Dictionary<string, byte[]> Textures;
            internal Vector2Int PackedDimensions;
            internal int PackedImportMaxSize;
            internal RenderPipelineAsset Pipeline;
            internal Shader Shader;
            internal bool Urp;
        }

        private static string CanonicalTextureRole(string value)
        {
            switch (value.ToLowerInvariant())
            {
                case "base_color": return "base_color";
                case "normal": return "normal";
                case "metallic": return "metallic";
                case "roughness": return "roughness";
                default: return null;
            }
        }

        private static Dictionary<string, byte[]> ValidateTextureMapping(JObject p, string modelPath, out string root, out int set)
        {
            var mapping = p["material_textures"] as JObject;
            root = (string)p["material_root"];
            if (mapping == null || string.IsNullOrEmpty(root)) throw new InvalidOperationException("material_textures requires a material_root.");
            root = AssetPath(new JObject { ["path"] = root });
            if (Path.GetExtension(modelPath).ToLowerInvariant() != ".fbx" ||
                !modelPath.StartsWith(root + "/", StringComparison.Ordinal))
                throw new InvalidOperationException("A material set must belong to the FBX's staged Assets subtree.");
            foreach (var property in mapping.Properties())
                if (property.Name != "set" && !new[] { "base_color", "normal", "metallic", "roughness" }.Contains(property.Name))
                    throw new InvalidOperationException("Unsupported material role: " + property.Name);
            if (mapping["set"] == null || mapping["set"].Type != JTokenType.Integer)
                throw new InvalidOperationException("material_textures.set must be a non-negative integer.");
            var setValue = (long)mapping["set"];
            if (setValue < 0 || setValue > int.MaxValue) throw new InvalidOperationException("material_textures.set is out of range.");
            set = (int)setValue;
            if (!(mapping["base_color"] is JObject) || ((mapping["metallic"] == null) != (mapping["roughness"] == null)))
                throw new InvalidOperationException("A material set requires base_color and either both metallic/roughness maps or neither.");

            var inputs = new Dictionary<string, byte[]>();
            foreach (var role in new[] { "base_color", "normal", "metallic", "roughness" })
            {
                if (mapping[role] != null && !(mapping[role] is JObject))
                    throw new InvalidOperationException("Texture role " + role + " must be an object with key and path.");
                var entry = mapping[role] as JObject;
                if (entry == null) continue;
                if (entry.Properties().Any(property => property.Name != "key" && property.Name != "path" && property.Name != "bytes" && property.Name != "sha256"))
                    throw new InvalidOperationException("Texture records may contain only key, path, bytes and sha256.");
                var key = (string)entry["key"];
                var path = AssetPath(new JObject { ["path"] = (string)entry["path"] });
                var match = Regex.Match(key ?? "", @"^texture[._](\d+)[._]([A-Za-z0-9_.-]+)$", RegexOptions.IgnoreCase);
                if (!match.Success || match.Groups[1].Value != set.ToString() || CanonicalTextureRole(match.Groups[2].Value) != role)
                    throw new InvalidOperationException("Texture key does not match its explicit set and role: " + (key ?? "(missing)"));
                if (!path.StartsWith(root + "/", StringComparison.Ordinal) || !Path.GetExtension(path).Equals(".png", StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Every material texture must be a PNG in the same staged subtree as its FBX.");
                var absolute = Path.Combine(Path.GetDirectoryName(Application.dataPath), path.Replace('/', Path.DirectorySeparatorChar));
                if (!File.Exists(absolute)) throw new InvalidOperationException("Material texture does not exist: " + path);
                if (entry["bytes"] == null || entry["bytes"].Type != JTokenType.Integer ||
                    entry["sha256"] == null || !Regex.IsMatch((string)entry["sha256"], "^[0-9a-f]{64}$"))
                    throw new InvalidOperationException("Texture " + role + " requires its validated byte count and sha256.");
                long expectedBytes = (long)entry["bytes"];
                string expectedSha = (string)entry["sha256"];
                var bytes = File.ReadAllBytes(absolute);
                if (expectedBytes < 0 || bytes.LongLength != expectedBytes)
                    throw new InvalidOperationException("Staged texture byte count differs from its manifest: " + path);
                using (var hash = SHA256.Create())
                {
                    var actualSha = BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
                    if (actualSha != expectedSha) throw new InvalidOperationException("Staged texture sha256 differs from its manifest: " + path);
                }
                inputs.Add(role, bytes);
            }
            return inputs;
        }

        private static int ValidateSingleMaterial(GameObject model)
        {
            var renderers = model.GetComponentsInChildren<Renderer>(true);
            var materialIds = new HashSet<int>();
            int slots = 0;
            foreach (var renderer in renderers)
                foreach (var material in renderer.sharedMaterials)
                {
                    slots++;
                    if (!material) throw new InvalidOperationException("The FBX has an empty material slot; refusing an ambiguous texture assignment.");
                    materialIds.Add(material.GetInstanceID());
                }
            if (slots == 0 || materialIds.Count != 1)
                throw new InvalidOperationException("Unity material delivery requires exactly one unambiguous FBX material across all renderer slots.");
            return slots;
        }

        private static Vector2Int ValidatePng(byte[] bytes, bool requireOpaque)
        {
            var probe = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
            try
            {
                if (!ImageConversion.LoadImage(probe, bytes, false) || probe.width < 1 || probe.height < 1)
                    throw new InvalidOperationException("Unity could not decode a material PNG.");
                if (requireOpaque && probe.GetPixels32().Any(pixel => pixel.a != 255))
                    throw new InvalidOperationException("Transparent base_color PNGs are unsupported; refusing to infer a Standard shader transparency mode.");
                return new Vector2Int(probe.width, probe.height);
            }
            finally { UnityEngine.Object.DestroyImmediate(probe); }
        }

        private static Texture2D DecodeLinearPng(byte[] bytes)
        {
            var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
            try
            {
                if (!ImageConversion.LoadImage(texture, bytes, false))
                    throw new InvalidOperationException("Unity could not decode a linear material PNG.");
                return texture;
            }
            catch
            {
                UnityEngine.Object.DestroyImmediate(texture);
                throw;
            }
        }

        private static int PackedImportMaxTextureSize(Vector2Int size)
        {
            // ponytail: Unity supports imported textures up to 16384; reject larger maps instead of silently reducing them.
            int limit = Math.Min(16384, SystemInfo.maxTextureSize);
            int largest = Math.Max(size.x, size.y);
            if (largest < 1 || largest > limit) throw new InvalidOperationException("Metallic/roughness dimensions exceed Unity's supported texture size.");
            int maxSize = 32;
            while (maxSize < largest && maxSize < limit) maxSize *= 2;
            if (maxSize > limit) throw new InvalidOperationException("Metallic/roughness dimensions exceed Unity's supported texture size.");
            return maxSize;
        }

        private static MaterialPlan PrepareMaterialPlan(JObject p, string modelPath, GameObject model)
        {
            string root;
            int set;
            var textures = ValidateTextureMapping(p, modelPath, out root, out set);
            var pipeline = GraphicsSettings.currentRenderPipeline;
            bool urp = IsUniversalPipeline(pipeline);
            if (pipeline && !urp)
                throw new InvalidOperationException("Manifest-driven material delivery supports Built-in Standard and Universal Render Pipeline Lit only.");
            var shader = Shader.Find(urp ? "Universal Render Pipeline/Lit" : "Standard");
            if (!shader || !shader.isSupported) throw new InvalidOperationException("The active pipeline's supported material shader is unavailable.");
            int slots = ValidateSingleMaterial(model);
            var sizes = new Dictionary<string, Vector2Int>();
            foreach (var pair in textures) sizes[pair.Key] = ValidatePng(pair.Value, pair.Key == "base_color");
            if (textures.ContainsKey("metallic") && sizes["metallic"] != sizes["roughness"])
                throw new InvalidOperationException("Metallic and roughness PNG dimensions must match before packing.");
            var packedDimensions = textures.ContainsKey("metallic") ? sizes["metallic"] : Vector2Int.zero;
            int packedMaxSize = textures.ContainsKey("metallic") ? PackedImportMaxTextureSize(packedDimensions) : 0;
            var output = root + "/MeshyMaterials";
            var outputPath = AssetPath(new JObject { ["path"] = output });
            var outputAbsolute = Path.Combine(Path.GetDirectoryName(Application.dataPath), outputPath.Replace('/', Path.DirectorySeparatorChar));
            if (File.Exists(outputAbsolute) || Directory.Exists(outputAbsolute))
                throw new InvalidOperationException("Refusing to overwrite the existing MeshyMaterials output folder.");
            return new MaterialPlan { Output = output, Set = set, SourceSlots = slots, Textures = textures,
                PackedDimensions = packedDimensions, PackedImportMaxSize = packedMaxSize, Pipeline = pipeline, Shader = shader, Urp = urp };
        }

        private static Texture2D ImportOwnedTexture(MaterialPlan plan, string role, string filename, TextureImporterType type, bool srgb, bool readable)
        {
            var assetPath = plan.Output + "/" + filename;
            AssetPath(new JObject { ["path"] = assetPath });
            var project = Path.GetDirectoryName(Application.dataPath);
            var absolute = Path.Combine(project, assetPath.Replace('/', Path.DirectorySeparatorChar));
            using (var stream = new FileStream(absolute, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                var bytes = plan.Textures[role];
                stream.Write(bytes, 0, bytes.Length);
            }
            AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceSynchronousImport);
            var importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
            if (!importer) throw new InvalidOperationException("Unity did not create a TextureImporter for " + assetPath);
            importer.textureType = type;
            importer.sRGBTexture = srgb;
            importer.isReadable = readable;
            importer.SaveAndReimport();
            importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
            if (!importer || importer.textureType != type || importer.sRGBTexture != srgb || importer.isReadable != readable)
                throw new InvalidOperationException("Unity texture importer readback did not match the requested settings for " + assetPath);
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
            if (!texture) throw new InvalidOperationException("Unity could not import generated texture " + assetPath);
            return texture;
        }

        private static JObject ApplyMaterial(MaterialPlan plan, GameObject created)
        {
            if (GraphicsSettings.currentRenderPipeline != plan.Pipeline)
                throw new InvalidOperationException("The active render pipeline changed after material preflight; inspect the created object before continuing.");
            var project = Path.GetDirectoryName(Application.dataPath);
            var outputAbsolute = Path.Combine(project, plan.Output.Replace('/', Path.DirectorySeparatorChar));
            if (File.Exists(outputAbsolute) || Directory.Exists(outputAbsolute))
                throw new InvalidOperationException("Refusing to overwrite the existing MeshyMaterials output folder.");
            Directory.CreateDirectory(outputAbsolute);
            var baseColor = ImportOwnedTexture(plan, "base_color", "base_color.png", TextureImporterType.Default, true, false);
            Texture2D normal = null;
            if (plan.Textures.ContainsKey("normal")) normal = ImportOwnedTexture(plan, "normal", "normal.png", TextureImporterType.NormalMap, false, false);
            Texture2D packed = null;
            string packedPath = null;
            if (plan.Textures.ContainsKey("metallic"))
            {
                var metallic = DecodeLinearPng(plan.Textures["metallic"]);
                Texture2D roughness = null;
                Texture2D packedImage = null;
                try
                {
                    roughness = DecodeLinearPng(plan.Textures["roughness"]);
                    if (metallic.width != plan.PackedDimensions.x || metallic.height != plan.PackedDimensions.y ||
                        roughness.width != plan.PackedDimensions.x || roughness.height != plan.PackedDimensions.y)
                        throw new InvalidOperationException("Decoded metallic/roughness dimensions changed before packing.");
                    var metalPixels = metallic.GetPixels32();
                    var roughPixels = roughness.GetPixels32();
                    var packedPixels = new Color32[metalPixels.Length];
                    for (int i = 0; i < packedPixels.Length; i++) packedPixels[i] = new Color32(metalPixels[i].r, 0, 0, (byte)(255 - roughPixels[i].r));
                    packedImage = new Texture2D(metallic.width, metallic.height, TextureFormat.RGBA32, false, true);
                    packedImage.SetPixels32(packedPixels);
                    packedImage.Apply(false, false);
                    packedPath = plan.Output + "/metallic_roughness.png";
                    AssetPath(new JObject { ["path"] = packedPath });
                    var absolute = Path.Combine(project, packedPath.Replace('/', Path.DirectorySeparatorChar));
                    using (var stream = new FileStream(absolute, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                    {
                        var png = ImageConversion.EncodeToPNG(packedImage);
                        if (png == null || png.Length == 0) throw new InvalidOperationException("Unity could not encode the packed metallic/roughness PNG.");
                        stream.Write(png, 0, png.Length);
                    }
                }
                finally
                {
                    UnityEngine.Object.DestroyImmediate(metallic);
                    if (roughness) UnityEngine.Object.DestroyImmediate(roughness);
                    if (packedImage) UnityEngine.Object.DestroyImmediate(packedImage);
                }
                AssetDatabase.ImportAsset(packedPath, ImportAssetOptions.ForceSynchronousImport);
                var packedImporter = AssetImporter.GetAtPath(packedPath) as TextureImporter;
                if (!packedImporter) throw new InvalidOperationException("Unity did not create a packed-map TextureImporter.");
                packedImporter.textureType = TextureImporterType.Default;
                packedImporter.sRGBTexture = false;
                packedImporter.npotScale = TextureImporterNPOTScale.None;
                packedImporter.maxTextureSize = plan.PackedImportMaxSize;
                packedImporter.textureCompression = TextureImporterCompression.Uncompressed;
                packedImporter.SaveAndReimport();
                packedImporter = AssetImporter.GetAtPath(packedPath) as TextureImporter;
                if (!packedImporter || packedImporter.textureType != TextureImporterType.Default || packedImporter.sRGBTexture ||
                    packedImporter.textureCompression != TextureImporterCompression.Uncompressed ||
                    packedImporter.npotScale != TextureImporterNPOTScale.None || packedImporter.maxTextureSize != plan.PackedImportMaxSize)
                    throw new InvalidOperationException("Packed-map importer readback did not remain linear and uncompressed.");
                packed = AssetDatabase.LoadAssetAtPath<Texture2D>(packedPath);
                if (!packed) throw new InvalidOperationException("Unity could not import the packed metallic/roughness map.");
                if (packed.width != plan.PackedDimensions.x || packed.height != plan.PackedDimensions.y)
                    throw new InvalidOperationException("Unity resized the packed metallic/roughness map; refusing material assignment.");
            }

            var materialPath = plan.Output + "/meshy_material.mat";
            AssetPath(new JObject { ["path"] = materialPath });
            var material = new Material(plan.Shader) { name = plan.Urp ? "Meshy URP Lit" : "Meshy Standard" };
            string baseMapProperty = plan.Urp ? "_BaseMap" : "_MainTex";
            string smoothnessProperty = plan.Urp ? "_Smoothness" : "_GlossMapScale";
            string metallicKeyword = plan.Urp ? "_METALLICSPECGLOSSMAP" : "_METALLICGLOSSMAP";
            material.SetColor(plan.Urp ? "_BaseColor" : "_Color", Color.white);
            material.SetTexture(baseMapProperty, baseColor);
            if (plan.Urp) material.SetFloat("_WorkflowMode", 1f);
            if (normal)
            {
                material.SetTexture("_BumpMap", normal);
                material.SetFloat("_BumpScale", 1f);
                material.EnableKeyword("_NORMALMAP");
            }
            if (packed)
            {
                material.SetTexture("_MetallicGlossMap", packed);
                material.SetFloat("_Metallic", 1f);
                if (!plan.Urp) material.SetFloat("_Glossiness", 1f);
                material.SetFloat(smoothnessProperty, 1f);
                material.SetFloat("_SmoothnessTextureChannel", 0f);
                material.EnableKeyword(metallicKeyword);
            }
            AssetDatabase.CreateAsset(material, materialPath);

            var renderers = created.GetComponentsInChildren<Renderer>(true);
            int slots = 0;
            foreach (var renderer in renderers)
            {
                var materials = renderer.sharedMaterials;
                for (int i = 0; i < materials.Length; i++)
                {
                    slots++;
                    materials[i] = material;
                }
                Undo.RecordObject(renderer, "Meshy material assignment");
                renderer.sharedMaterials = materials;
                PrefabUtility.RecordPrefabInstancePropertyModifications(renderer);
            }
            if (slots != plan.SourceSlots || slots == 0) throw new InvalidOperationException("Instantiated renderer slots changed after material preflight.");
            EditorSceneManager.MarkSceneDirty(created.scene);

            var readRoles = new JArray("base_color");
            if (normal) readRoles.Add("normal");
            if (packed) { readRoles.Add("metallic"); readRoles.Add("roughness"); }
            foreach (var renderer in renderers)
                foreach (var assigned in renderer.sharedMaterials)
                    if (assigned != material || assigned.shader != plan.Shader || assigned.GetTexture(baseMapProperty) != baseColor ||
                        (plan.Urp && !Mathf.Approximately(assigned.GetFloat("_WorkflowMode"), 1f)) ||
                        (normal && assigned.GetTexture("_BumpMap") != normal) || (packed && (assigned.GetTexture("_MetallicGlossMap") != packed ||
                            !Mathf.Approximately(assigned.GetFloat(smoothnessProperty), 1f) ||
                            !Mathf.Approximately(assigned.GetFloat("_SmoothnessTextureChannel"), 0f) || !assigned.IsKeywordEnabled(metallicKeyword))))
                        throw new InvalidOperationException("Fresh instantiated material readback did not match the requested pipeline texture slots.");
            var baseImporter = AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(baseColor)) as TextureImporter;
            if (!baseImporter || baseImporter.textureType != TextureImporterType.Default || !baseImporter.sRGBTexture)
                throw new InvalidOperationException("Fresh base_color importer readback did not remain sRGB.");
            var textureReadback = new JObject {
                ["base_color"] = new JObject { ["path"] = AssetDatabase.GetAssetPath(baseColor), ["texture_type"] = baseImporter.textureType.ToString(), ["srgb"] = baseImporter.sRGBTexture },
            };
            if (normal)
            {
                var normalImporter = AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(normal)) as TextureImporter;
                if (!normalImporter || normalImporter.textureType != TextureImporterType.NormalMap || normalImporter.sRGBTexture)
                    throw new InvalidOperationException("Fresh normal importer readback did not remain linear NormalMap.");
                textureReadback["normal"] = new JObject { ["path"] = AssetDatabase.GetAssetPath(normal), ["texture_type"] = normalImporter.textureType.ToString(), ["srgb"] = normalImporter.sRGBTexture };
            }
            if (packed)
            {
                var packedImporter = AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(packed)) as TextureImporter;
                if (!packedImporter || packedImporter.sRGBTexture || packedImporter.textureType != TextureImporterType.Default ||
                    packedImporter.npotScale != TextureImporterNPOTScale.None || packedImporter.maxTextureSize != plan.PackedImportMaxSize ||
                    packed.width != plan.PackedDimensions.x || packed.height != plan.PackedDimensions.y)
                    throw new InvalidOperationException("Fresh packed-map importer readback changed its linear settings or dimensions.");
                textureReadback["metallic_roughness"] = new JObject { ["path"] = AssetDatabase.GetAssetPath(packed),
                    ["channels"] = "metallic_red_roughness_inverted_alpha", ["srgb"] = packedImporter.sRGBTexture,
                    ["width"] = packed.width, ["height"] = packed.height, ["max_texture_size"] = packedImporter.maxTextureSize,
                    ["npot_scale"] = packedImporter.npotScale.ToString() };
            }
            return new JObject { ["status"] = "verified", ["set"] = plan.Set, ["shader"] = material.shader.name,
                ["material_asset"] = AssetDatabase.GetAssetPath(material), ["material_slots"] = slots,
                ["roles"] = readRoles, ["textures"] = textureReadback };
        }

        internal static JObject Model(JObject p, bool instantiate)
        {
            Ready();
            var relative = AssetPath(p);
            var ext = Path.GetExtension(relative).ToLowerInvariant();
            if (ext != ".fbx" && ext != ".obj") throw new InvalidOperationException("The native model handoff supports FBX and OBJ; convert GLB first.");
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(relative);
            // Inspection already imported this asset. Instantiation must not force a second import.
            if (!instantiate || !model)
            {
                AssetDatabase.ImportAsset(relative, ImportAssetOptions.ForceSynchronousImport);
                model = AssetDatabase.LoadAssetAtPath<GameObject>(relative);
            }
            if (!model) throw new InvalidOperationException("Unity could not load a model from " + relative);
            MaterialPlan materialPlan = null;
            if (instantiate && p["material_textures"] != null) materialPlan = PrepareMaterialPlan(p, relative, model);
            else if (instantiate && p["material_root"] != null)
                throw new InvalidOperationException("material_root is valid only with an explicit material_textures mapping.");
            var all = AssetDatabase.LoadAllAssetsAtPath(relative);
            var meshes = all.OfType<Mesh>().ToArray();
            if (meshes.Length == 0) throw new InvalidOperationException("Imported asset contains no meshes.");
            var result = new JObject { ["path"] = relative, ["guid"] = AssetDatabase.AssetPathToGUID(relative),
                ["meshes"] = meshes.Length, ["vertices"] = meshes.Sum(m => m.vertexCount),
                ["materials"] = new JArray(all.OfType<Material>().Select(m => m.name)),
                ["animations"] = new JArray(all.OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__")).Select(c => c.name)),
                ["dependencies"] = new JArray(AssetDatabase.GetDependencies(relative)) };
            if (instantiate)
            {
                var created = (GameObject)PrefabUtility.InstantiatePrefab(model, SceneManager.GetActiveScene());
                Undo.RegisterCreatedObjectUndo(created, "Meshy import model");
                EditorSceneManager.MarkSceneDirty(created.scene);
                result["instance_id"] = created.GetInstanceID().ToString();
                result["name"] = created.name;
                result["renderers"] = created.GetComponentsInChildren<Renderer>(true).Length;
                result["material_delivery"] = materialPlan == null
                    ? new JObject { ["status"] = "geometry_only", ["reason"] = "No keyed texture set was supplied." }
                    : ApplyMaterial(materialPlan, created);
            }
            return result;
        }

        internal static JObject SaveScene(JObject p)
        {
            Ready();
            var relative = AssetPath(p);
            if (Path.GetExtension(relative) != ".unity") throw new InvalidOperationException("Scene destination must end in .unity.");
            var scene = SceneManager.GetActiveScene();
            var absolute = Path.Combine(Path.GetDirectoryName(Application.dataPath), relative);
            if (File.Exists(absolute) && scene.path != relative) throw new InvalidOperationException("Refusing to overwrite another scene.");
            Directory.CreateDirectory(Path.GetDirectoryName(absolute));
            if (!EditorSceneManager.SaveScene(scene, relative)) throw new InvalidOperationException("Scene save failed.");
            return new JObject { ["path"] = scene.path, ["dirty"] = scene.isDirty };
        }

        internal static JObject OpenScene(JObject p)
        {
            Ready();
            var relative = AssetPath(p);
            if (Path.GetExtension(relative) != ".unity" || !File.Exists(Path.Combine(Path.GetDirectoryName(Application.dataPath), relative)))
                throw new InvalidOperationException("Select an existing .unity scene below Assets.");
            if ((bool)Session()["dirty"]) throw new InvalidOperationException("Save dirty scenes before opening another scene.");
            var scene = EditorSceneManager.OpenScene(relative, OpenSceneMode.Single);
            return new JObject { ["path"] = scene.path, ["dirty"] = scene.isDirty };
        }
    }
}
