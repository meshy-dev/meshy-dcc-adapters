-- Meshy DCC for Roblox Studio 0.1.1 (installed by meshy-dcc; edits are overwritten)
--!nonstrict
--[[
Connects this Studio place to a Meshy DCC sidecar on this computer (127.0.0.1
only) and runs the scene requests of the agent working through it. The
sidecar was started for one place and refuses every other, so a request never
reaches a different place. Running Luau sent by the agent stays off until the
user turns on "Allow Luau" in the Meshy DCC toolbar.
]]

local AssetService = game:GetService("AssetService")
local ChangeHistoryService = game:GetService("ChangeHistoryService")
local EncodingService = game:GetService("EncodingService")
local HttpService = game:GetService("HttpService")
local RunService = game:GetService("RunService")

local VERSION = "0.1.1"
-- Keep in step with PORTS in meshy_dcc_roblox/bridge.py.
local PORTS = { 13890, 13891, 13892, 13893 }
local SCAN_SECONDS = 5
local HELLO_TIMEOUT = 10
local REFUSED_SECONDS = 30
local LUAU_SETTING = "MeshyDccAllowLuau"
local OFF_SETTING = "MeshyDccOff"
local MAX_OUTPUT = 200000
local YIELD_EVERY = 2000
local MAP_KEYS = { color = "ColorMap", normal = "NormalMap", metalness = "MetalnessMap", roughness = "RoughnessMap" }
local INSPECT_PROPERTIES = {
	"Position", "Orientation", "Size", "Anchored", "CanCollide", "Transparency", "Color",
	"Material", "Shape", "Locked", "DoubleSided", "WorldPivot", "Brightness", "Range", "Text",
}

-- Play-test DataModels load plugins too; only the edit DataModel serves the agent.
if not RunService:IsEdit() then
	return
end

local handlers = {}

----------------------------------------------------------------------------- paths and values

local function pathOf(instance: Instance): string
	local names = {}
	local node = instance
	while node and node ~= game do
		table.insert(names, 1, node.Name)
		node = node.Parent
	end
	return table.concat(names, "/")
end

-- "Workspace/Model/Part": names from the DataModel down. A name shared by two
-- siblings is ambiguous and refused rather than guessed.
local function resolve(path: string): Instance
	if type(path) ~= "string" or path == "" then
		error("path is required")
	end
	local node: Instance = game
	for name in string.gmatch(path, "[^/]+") do
		local match = nil
		for _, child in node:GetChildren() do
			if child.Name == name then
				if match then
					error(`ambiguous path {path}: more than one child of {pathOf(node)} is named {name}`)
				end
				match = child
			end
		end
		if not match then
			error(`no instance at {path}`)
		end
		node = match
	end
	return node
end

local function assertEditable(instance: Instance)
	if instance == game or instance.Parent == game then
		error(`{pathOf(instance)} is a service and cannot be changed this way`)
	end
	if instance == workspace.Terrain or instance == workspace.CurrentCamera then
		error(`{pathOf(instance)} belongs to Studio and cannot be changed this way`)
	end
end

local function fromValue(value)
	local kind = typeof(value)
	if kind == "Vector3" then
		return { value.X, value.Y, value.Z }
	elseif kind == "Vector2" then
		return { value.X, value.Y }
	elseif kind == "Color3" then
		return { value.R, value.G, value.B }
	elseif kind == "CFrame" then
		local rx, ry, rz = value:ToOrientation()
		return { position = { value.X, value.Y, value.Z }, orientation = { math.deg(rx), math.deg(ry), math.deg(rz) } }
	elseif kind == "EnumItem" or kind == "BrickColor" then
		return value.Name
	elseif kind == "Instance" then
		return pathOf(value)
	elseif kind == "number" or kind == "string" or kind == "boolean" then
		return value
	end
	return tostring(value)
end

local function toValue(current, value, property: string)
	local kind = typeof(current)
	if kind == "Vector3" then
		return Vector3.new(value[1], value[2], value[3])
	elseif kind == "Vector2" then
		return Vector2.new(value[1], value[2])
	elseif kind == "Color3" then
		if type(value) == "string" then
			return Color3.fromHex(value)
		end
		return Color3.new(value[1], value[2], value[3])
	elseif kind == "CFrame" then
		return CFrame.new(table.unpack(value))
	elseif kind == "EnumItem" then
		return current.EnumType[value]
	elseif kind == "BrickColor" then
		return BrickColor.new(value)
	elseif kind == "number" or kind == "string" or kind == "boolean" then
		if type(value) ~= kind then
			error(`{property} takes a {kind}`)
		end
		return value
	end
	error(`{property} is a {kind}; this tool cannot set it`)
end

local function applyProperties(instance: Instance, properties)
	for property, value in properties or {} do
		if property == "Parent" or property == "Name" then
			error(`set {property} with the dedicated parameter instead`)
		end
		local readable, current = pcall(function()
			return instance[property]
		end)
		if not readable then
			error(`{instance.ClassName} has no property {property}`)
		end
		instance[property] = toValue(current, value, property)
	end
end

local function describe(instance: Instance)
	local node = { path = pathOf(instance), name = instance.Name, class = instance.ClassName, children = #instance:GetChildren() }
	if instance:IsA("BasePart") then
		node.position = fromValue(instance.Position)
		node.size = fromValue(instance.Size)
	elseif instance:IsA("Model") and instance.Parent ~= game then
		node.position = fromValue(instance:GetPivot().Position)
		local ok, size = pcall(instance.GetExtentsSize, instance)
		if ok then
			node.size = fromValue(size)
		end
	end
	return node
end

local function inspect(instance: Instance)
	local result = describe(instance)
	local properties = {}
	for _, property in INSPECT_PROPERTIES do
		local ok, value = pcall(function()
			return instance[property]
		end)
		if ok and value ~= nil then
			properties[property] = fromValue(value)
		end
	end
	if instance:IsA("PVInstance") and instance.Parent ~= game then
		properties.Pivot = fromValue(instance:GetPivot())
	end
	result.properties = properties
	local attributes = {}
	for name, value in instance:GetAttributes() do
		attributes[name] = fromValue(value)
	end
	result.attributes = attributes
	return result
end

-- One undo step per agent change; a failed change is rolled back.
local function record(label: string, change)
	local recording = ChangeHistoryService:TryBeginRecording("Meshy DCC: " .. label)
	local ok, result = pcall(change)
	if recording then
		ChangeHistoryService:FinishRecording(
			recording,
			if ok then Enum.FinishRecordingOperation.Commit else Enum.FinishRecordingOperation.Cancel
		)
	end
	if not ok then
		error(result, 0)
	end
	return result
end

local function placeInfo()
	return { name = game.Name, place_id = game.PlaceId, game_id = game.GameId }
end

----------------------------------------------------------------------------- scene tools

handlers.session = function()
	return {
		studio_version = version(),
		plugin_version = VERSION,
		place = placeInfo(),
		luau_allowed = plugin:GetSetting(LUAU_SETTING) == true,
		can_undo = ChangeHistoryService:GetCanUndo(),
	}
end

handlers.get_scene_tree = function(params)
	local root = resolve(params.root or "Workspace")
	local depth = params.depth or 3
	local limit = params.max_nodes or 500
	local nodes, truncated = {}, false
	local function walk(instance: Instance, level: number)
		for _, child in instance:GetChildren() do
			if #nodes >= limit then
				truncated = true
				return
			end
			table.insert(nodes, describe(child))
			if level < depth then
				walk(child, level + 1)
			end
		end
	end
	walk(root, 1)
	return { root = pathOf(root), nodes = nodes, truncated = truncated }
end

handlers.inspect_instance = function(params)
	return inspect(resolve(params.path))
end

handlers.create_instance = function(params)
	local parent = resolve(params.parent or "Workspace")
	local ok, instance = pcall(Instance.new, params.class_name)
	if not ok then
		error(`cannot create a {params.class_name}: {instance}`)
	end
	if params.name then
		instance.Name = params.name
	end
	if parent:FindFirstChild(instance.Name) then
		instance:Destroy()
		error(`{pathOf(parent)} already has a child named {params.name or params.class_name}; pick another name`)
	end
	return record("Create " .. instance.Name, function()
		applyProperties(instance, params.properties)
		instance.Parent = parent
		return inspect(instance)
	end)
end

handlers.set_properties = function(params)
	local instance = resolve(params.path)
	assertEditable(instance)
	return record("Set properties of " .. instance.Name, function()
		applyProperties(instance, params.properties)
		return inspect(instance)
	end)
end

handlers.move_instance = function(params)
	local instance = resolve(params.path)
	assertEditable(instance)
	if not instance:IsA("PVInstance") then
		error(`{pathOf(instance)} is a {instance.ClassName}, which has no position`)
	end
	local position = params.position
	local target = CFrame.new(position[1], position[2], position[3])
	if params.rotation then
		local r = params.rotation
		target *= CFrame.fromOrientation(math.rad(r[1]), math.rad(r[2]), math.rad(r[3]))
	else
		target *= instance:GetPivot().Rotation
	end
	return record("Move " .. instance.Name, function()
		instance:PivotTo(target)
		return { path = pathOf(instance), pivot = fromValue(instance:GetPivot()) }
	end)
end

handlers.delete_instance = function(params)
	local instance = resolve(params.path)
	assertEditable(instance)
	local path = pathOf(instance)
	record("Delete " .. instance.Name, function()
		instance.Parent = nil -- Studio's own Delete does the same, so Undo restores it
	end)
	return { deleted = path, exists = pcall(resolve, path) }
end

handlers.execute_luau = function(params)
	if plugin:GetSetting(LUAU_SETTING) ~= true then
		error(
			"Running Luau is off in this Studio. Only the user can turn it on: "
				.. "Plugins tab > Meshy DCC > Allow Luau (it stays on until they click it again)."
		)
	end
	local chunk, compileError = loadstring(params.code, "=meshy-dcc")
	if not chunk then
		error(compileError, 0)
	end
	local lines, size = {}, 0
	local function capture(prefix: string, ...)
		local values = table.pack(...)
		for i = 1, values.n do
			values[i] = tostring(values[i])
		end
		local line = prefix .. table.concat(values, "\t", 1, values.n)
		size += #line + 1
		if size <= MAX_OUTPUT then
			table.insert(lines, line)
		end
	end
	setfenv(chunk, setmetatable({
		print = function(...)
			capture("", ...)
		end,
		warn = function(...)
			capture("[warn] ", ...)
		end,
	}, { __index = getfenv() }))
	local results = record("Run Luau", function()
		return table.pack(chunk())
	end)
	local returned = {}
	for i = 1, results.n do
		returned[i] = fromValue(results[i])
	end
	return { output = table.concat(lines, "\n"), output_truncated = size > MAX_OUTPUT, returned = returned }
end

----------------------------------------------------------------------------- Meshy import

-- The sidecar sends a model as base64 pieces (begin, data..., finish); only
-- the latest import is staged.
local staging = nil

handlers["meshy.import_begin"] = function(params)
	staging = { id = params.import_id, pieces = {} }
	return { import_id = params.import_id }
end

handlers["meshy.import_data"] = function(params)
	if not staging or staging.id ~= params.import_id then
		error("unknown import; call meshy.import_begin first")
	end
	local list = staging.pieces[params.key]
	if not list then
		list = {}
		staging.pieces[params.key] = list
	end
	list[params.index] = params.data
	return { key = params.key, index = params.index }
end

local function takeBlob(key: string): buffer
	local list = staging.pieces[key]
	if not list then
		error(`import data {key} is missing`)
	end
	staging.pieces[key] = nil
	return EncodingService:Base64Decode(buffer.fromstring(table.concat(list)))
end

local function readVector3(data: buffer, index: number): Vector3
	local offset = index * 12
	return Vector3.new(buffer.readf32(data, offset), buffer.readf32(data, offset + 4), buffer.readf32(data, offset + 8))
end

local function buildMesh(chunk): EditableMesh
	local positions = takeBlob(chunk.positions)
	local indices = takeBlob(chunk.indices)
	local normals = if chunk.normals then takeBlob(chunk.normals) else nil
	local uvs = if chunk.uvs then takeBlob(chunk.uvs) else nil
	local mesh = AssetService:CreateEditableMesh()
	if not mesh then
		error("Studio has no memory left for an editable mesh")
	end
	local vertexIds, normalIds, uvIds = {}, {}, {}
	for i = 0, chunk.vertex_count - 1 do
		vertexIds[i + 1] = mesh:AddVertex(readVector3(positions, i))
		if normals then
			normalIds[i + 1] = mesh:AddNormal(readVector3(normals, i))
		end
		if uvs then
			uvIds[i + 1] = mesh:AddUV(Vector2.new(buffer.readf32(uvs, i * 8), buffer.readf32(uvs, i * 8 + 4)))
		end
		if i % YIELD_EVERY == YIELD_EVERY - 1 then
			task.wait()
		end
	end
	for t = 0, chunk.triangle_count - 1 do
		local a = buffer.readu32(indices, t * 12) + 1
		local b = buffer.readu32(indices, t * 12 + 4) + 1
		local c = buffer.readu32(indices, t * 12 + 8) + 1
		local face = mesh:AddTriangle(vertexIds[a], vertexIds[b], vertexIds[c])
		if normals then
			mesh:SetFaceNormals(face, { normalIds[a], normalIds[b], normalIds[c] })
		end
		if uvs then
			mesh:SetFaceUVs(face, { uvIds[a], uvIds[b], uvIds[c] })
		end
		if t % YIELD_EVERY == YIELD_EVERY - 1 then
			task.wait()
		end
	end
	mesh:RemoveUnused()
	return mesh
end

local function buildImage(texture): EditableImage
	local pixels = takeBlob(texture.key)
	local image = AssetService:CreateEditableImage({ Size = Vector2.new(texture.width, texture.height) })
	if not image then
		error("Studio has no memory left for an editable image")
	end
	image:WritePixelsBuffer(Vector2.zero, image.Size, pixels)
	return image
end

-- Uploads to the logged-in Studio user's Roblox inventory, without a prompt.
local function upload(object, assetType, name: string): number
	local result, idOrError = AssetService:CreateAssetAsync(
		object,
		assetType,
		{ Name = name, Description = "Imported with Meshy DCC" }
	)
	if result ~= Enum.CreateAssetResult.Success then
		error(`upload of {name} failed: {result} {idOrError}`)
	end
	return idOrError
end

local function surfaceAppearance(maps, published: boolean): SurfaceAppearance
	if published then
		local appearance = Instance.new("SurfaceAppearance")
		for role, id in maps do
			appearance[MAP_KEYS[role]] = `rbxassetid://{id}`
		end
		return appearance
	end
	local content = {}
	for role, image in maps do
		content[MAP_KEYS[role]] = Content.fromObject(image)
	end
	return AssetService:CreateSurfaceAppearanceAsync(content)
end

local function inspectModel(root: Instance)
	local parts = {}
	local list = if root:IsA("BasePart") then { root } else root:GetDescendants()
	for _, instance in list do
		if instance:IsA("MeshPart") then
			local info = {
				path = pathOf(instance),
				size = fromValue(instance.Size),
				position = fromValue(instance.Position),
				double_sided = instance.DoubleSided,
				anchored = instance.Anchored,
			}
			local content = instance.MeshContent
			info.mesh_source = content.SourceType.Name
			if content.Uri then
				info.mesh_uri = content.Uri
			end
			local mesh = content.Object
			if mesh and mesh:IsA("EditableMesh") then
				info.vertices = #mesh:GetVertices()
				info.triangles = #mesh:GetFaces()
			end
			local appearance = instance:FindFirstChildOfClass("SurfaceAppearance")
			if appearance then
				local maps = {}
				for role, key in MAP_KEYS do
					local map = appearance[key .. "Content"]
					if map.SourceType ~= Enum.ContentSourceType.None then
						maps[role] = map.SourceType.Name
					end
				end
				info.maps = maps
			end
			table.insert(parts, info)
		end
	end
	local result = { path = pathOf(root), class = root.ClassName, mesh_parts = parts }
	if root:IsA("Model") then
		local frame, size = root:GetBoundingBox()
		result.bounds = { center = fromValue(frame.Position), size = fromValue(size) }
		result.pivot = fromValue(root:GetPivot())
	end
	return result
end

handlers["meshy.import_finish"] = function(params)
	if not staging or staging.id ~= params.import_id then
		error("unknown import; call meshy.import_begin first")
	end
	local meta = params.meta
	local parent = resolve(meta.parent or "Workspace")
	if parent:FindFirstChild(meta.name) then
		staging = nil
		error(`{pathOf(parent)} already has a child named {meta.name}; pick another name`)
	end
	local ok, built = pcall(function()
		local maps, uploaded = {}, { meshes = {}, images = {} }
		for role, texture in meta.textures or {} do
			local image = buildImage(texture)
			if meta.publish then
				maps[role] = upload(image, Enum.AssetType.Image, `{meta.name}_{role}`)
				table.insert(uploaded.images, maps[role])
			else
				maps[role] = image
			end
		end
		local parts = {}
		for index, chunk in meta.chunks do
			local mesh = buildMesh(chunk)
			local content
			if meta.publish then
				local id = upload(mesh, Enum.AssetType.Mesh, `{meta.name}_{index}`)
				table.insert(uploaded.meshes, id)
				content = Content.fromAssetId(id)
			else
				content = Content.fromObject(mesh)
			end
			local part = AssetService:CreateMeshPartAsync(content)
			part.Name = if #meta.chunks == 1 then meta.name else `{meta.name}_{index}`
			part.Anchored = true
			part.DoubleSided = meta.double_sided == true
			part.CFrame = CFrame.new(chunk.center[1], chunk.center[2], chunk.center[3])
			if next(maps) then
				surfaceAppearance(maps, meta.publish == true).Parent = part
			end
			parts[index] = part
		end
		return { parts = parts, uploaded = uploaded }
	end)
	staging = nil
	if not ok then
		error(built, 0)
	end
	local origin = if meta.position then Vector3.new(meta.position[1], meta.position[2], meta.position[3]) else Vector3.zero
	return record("Import " .. meta.name, function()
		local model = Instance.new("Model")
		model.Name = meta.name
		for _, part in built.parts do
			part.CFrame += origin
			part.Parent = model
		end
		model.WorldPivot = CFrame.new(origin)
		model.Parent = parent
		local result = inspectModel(model)
		result.persistent = meta.publish == true
		if meta.publish then
			result.uploaded = built.uploaded
		end
		return result
	end)
end

handlers.inspect_model = function(params)
	return inspectModel(resolve(params.path))
end

----------------------------------------------------------------------------- connection

local enabled = plugin:GetSetting(OFF_SETTING) ~= true
local alive = true
local client = nil -- the WebStreamClient being opened or in use
local bound = false -- the sidecar accepted this place
local refusedUntil = {}

local toolbar = plugin:CreateToolbar("Meshy DCC")
local connectButton = toolbar:CreateButton("MeshyDccConnect", "Let a local Meshy DCC agent work in this place", "", "Meshy DCC")
local luauButton = toolbar:CreateButton("MeshyDccLuau", "Allow the agent to run Luau code in Studio (off by default)", "", "Allow Luau")
connectButton.ClickableWhenViewportHidden = true
luauButton.ClickableWhenViewportHidden = true

local function refreshButtons()
	connectButton:SetActive(enabled and bound)
	luauButton:SetActive(plugin:GetSetting(LUAU_SETTING) == true)
end

local function closeClient(ws)
	if client == ws then
		client = nil
		if bound then
			bound = false
			print("Meshy DCC: disconnected from the agent session.")
		end
		refreshButtons()
	end
	pcall(ws.Close, ws)
end

local function send(ws, message)
	ws:Send(HttpService:JSONEncode(message))
end

local function handleRequest(ws, message)
	local handler = handlers[message.method]
	local ok, result
	if handler then
		ok, result = pcall(handler, message.params or {})
	else
		ok, result = false, `unknown method {message.method}`
	end
	local reply = { type = "response", jsonrpc = "2.0", id = message.id }
	if ok then
		reply.result = result
	else
		reply.error = { code = -32000, message = tostring(result) }
	end
	if client == ws then
		send(ws, reply)
	end
end

local function onMessage(ws, port: number, text: string)
	local ok, message = pcall(HttpService.JSONDecode, HttpService, text)
	if not ok or type(message) ~= "table" then
		return
	end
	if message.type == "hello_ack" then
		bound = true
		refreshButtons()
		print(`Meshy DCC: connected; the agent can now work in {game.Name}.`)
	elseif message.type == "hello_reject" then
		refusedUntil[port] = os.time() + REFUSED_SECONDS
		closeClient(ws)
	elseif message.type == "request" and bound then
		task.spawn(handleRequest, ws, message)
	end
end

local function tryPort(port: number)
	-- A plain GET first: a closed port fails here quietly, without a socket error.
	local reached, response = pcall(HttpService.RequestAsync, HttpService, { Url = `http://127.0.0.1:{port}/`, Method = "GET" })
	if not reached or response.StatusCode ~= 200 then
		return
	end
	local decoded, probe = pcall(HttpService.JSONDecode, HttpService, response.Body)
	if not decoded or type(probe) ~= "table" or probe.server ~= "meshy-dcc-roblox" or not probe.accepting then
		return
	end
	local created, ws = pcall(
		HttpService.CreateWebStreamClient,
		HttpService,
		Enum.WebStreamClientType.WebSocket,
		{ Url = `ws://127.0.0.1:{port}/` }
	)
	if not created then
		return
	end
	client = ws
	ws.Opened:Connect(function()
		send(ws, { type = "hello", client = "roblox-studio", version = version(), plugin_version = VERSION, place = placeInfo() })
	end)
	ws.MessageReceived:Connect(function(text)
		onMessage(ws, port, text)
	end)
	ws.Error:Connect(function()
		closeClient(ws)
	end)
	ws.Closed:Connect(function()
		closeClient(ws)
	end)
	task.delay(HELLO_TIMEOUT, function()
		if client == ws and not bound then
			closeClient(ws)
		end
	end)
end

connectButton.Click:Connect(function()
	enabled = not enabled
	plugin:SetSetting(OFF_SETTING, not enabled)
	if not enabled and client then
		closeClient(client)
	end
	print(if enabled then "Meshy DCC: on; waiting for an agent session." else "Meshy DCC: off for every place until clicked again.")
	refreshButtons()
end)

luauButton.Click:Connect(function()
	local allow = plugin:GetSetting(LUAU_SETTING) ~= true
	plugin:SetSetting(LUAU_SETTING, allow)
	print(if allow then "Meshy DCC: the agent may run Luau in Studio." else "Meshy DCC: Luau from the agent is off.")
	refreshButtons()
end)

plugin.Unloading:Connect(function()
	alive = false
	if client then
		closeClient(client)
	end
end)

refreshButtons()
task.spawn(function()
	while alive do
		if enabled and client == nil then
			for _, port in PORTS do
				if client ~= nil or not enabled then
					break
				end
				if (refusedUntil[port] or 0) <= os.time() then
					tryPort(port)
				end
			end
		end
		task.wait(SCAN_SECONDS)
	end
end)
