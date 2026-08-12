--[[
================================================================================
  Palversation - step 6: settings (ipc folder, chat prefix, gift command)
  moved to an external config.txt file instead of hardcoded constants, plus
  a dedicated gift-check command.
  Version: 0.6.0

  New in this step:
    - config.txt (key=value per line) holds ipc_dir, chat_prefix and
      gift_command. Only CONFIG_PATH itself stays hardcoded in this file.
    - A separate command (default "!palgift") triggers a "gift_check"
      event, checked before the general chat prefix so a command that
      starts with the same letters (e.g. "!palgift" vs "!pal") is matched
      correctly.

  UE4SS/Palworld API used (verified by reading ChickNomad / PalChatter's
  source code):
    - StaticFindObject("/Script/Pal.Default__PalUtility")
    - UEHelpers.GetWorld() / UEHelpers.GetPlayerController()
    - cdo:SendSystemToPlayerChat(World, FString, {})
    - cdo:GetLocalPalPlayerController(World) -> cdo:GetOtomoHolderComponent(pc)
    - holder:TryGetSpawnedOtomoHandle()
    - handle:TryGetIndividualParameter():GetNickNameByCheckBlockedUser()/GetCharacterID()
    - handle:TryGetIndividualActor():GetCharacterParameterComponent()
        .ElementType1, :GetFullStomach(), :GetMaxFullStomach()
    - actor.ActionComponent:GetCurrentAction():GetWazaID() > 0 means an
      attack is happening right now (used only as a boolean signal here,
      not to name the specific move -- that needs ChickNomad's own
      compiled 392-move ID table, which we're intentionally not
      reproducing).
    - RegisterHook("/Script/Pal.PalGameStateInGame:BroadcastChatMessage", fn)
    - RegisterHook on these 4 paths (deploy/recall: they only set a dirty
      flag, the actual change is detected by comparing state between ticks):
        "/Script/Pal.PalGliderComponent:OnUpdateOtomoHolderSlot"
        "/Script/Pal.PalGliderComponent:OnUpdateOtomoHolderInitialized"
        "/Script/Pal.PalPassiveSkillBase:OnUpdateOtomoHolder"
        "/Script/Pal.PalPartnerSkillPassiveSkill:OnUpdateOtomoHolder"
    - pc:IsRiding() / pc:IsRidingFlyPal() / pc:IsSwimming() -> PLAYER's ride
      state (confirmed, unambiguous).
    - FindFirstOf("PalBodyTemperatureComponent"):GetTemperatureInfo().CurrentBodyState
      (0 Default / 1 Cold / 2 Heat). NOTE: ChickNomad itself admits there is
      no clean global getter for this, it's best-effort (first component
      found in the world). The least certain of the events.
    - os.clock()-based random interval timer for idle chatter (same pattern
      ChickNomad uses for its own AutoChatter feature).
    - LoopAsync(ms, fn) / ExecuteInGameThread(fn)

  File protocol (our own design, 7 lines):
    Line 1: Pal name
    Line 2: Pal element
    Line 3: Pal key (stable per-individual: CharacterID#InstanceId)
    Line 4: Pal passive skill IDs -- DISABLED, always empty (see
            GetPalPassiveIds's own comment: confirmed UE4SS use-after-free
            bug on TArray return values caused a real game crash)
    Line 5: Pal friendship, "rank,point" (confirmed real GetFriendshipRank()/
            GetFriendshipPoint() -- simple scalar returns, not affected by
            the TArray bug above), or empty if unavailable
    Line 6: event type (chat, deploy, recall, hunger, cold, heat,
            ride_start, ride_end, combat, idle, gift_check, vision_check)
    Line 7 onward: content (player's message if event_type is "chat",
            empty or extra detail otherwise)
================================================================================
]]

local UEHelpers = require("UEHelpers")

local MOD_NAME = "Palversation"
local VERSION  = "0.13.1"
local TAG = "[" .. MOD_NAME .. " v" .. VERSION .. "]"

-- ============================================================================
-- CONFIG FILE - auto-detects the mod's own root folder (one level above
-- Scripts/, where this file lives) using debug.getinfo, a standard Lua
-- feature (not UE4SS-specific). This is NOT confirmed to work inside
-- UE4SS itself (ChickNomad solves this differently, with a list of fixed
-- candidate paths instead), so there's a manual fallback below in case it
-- doesn't resolve correctly on your setup.
-- ============================================================================
local FALLBACK_MOD_ROOT = "D:\\PUT_THE_ABSOLUTE_PATH_TO_YOUR_MOD_FOLDER_HERE"

local function GetModRootDir()
    local ok, info = pcall(function() return debug.getinfo(1, "S") end)
    if not ok or not info or not info.source then return nil end
    local source = info.source
    if source:sub(1, 1) == "@" then source = source:sub(2) end
    -- Strips the last two path segments (Scripts\main.lua) to get the
    -- folder that CONTAINS Scripts, i.e. the mod's own root.
    return source:match("^(.*)[/\\][^/\\]+[/\\][^/\\]+$")
end

local MOD_ROOT = GetModRootDir()
if MOD_ROOT then
    print("[Palversation] Auto-detected mod root: " .. MOD_ROOT)
else
    MOD_ROOT = FALLBACK_MOD_ROOT
    print("[Palversation] Could not auto-detect the mod root, using FALLBACK_MOD_ROOT instead.")
end

local CONFIG_PATH = MOD_ROOT .. "\\config.txt"

local function ToBool(s, default)
    if s == nil then return default end
    local lowered = tostring(s):lower()
    if lowered == "true" or lowered == "1" then return true end
    if lowered == "false" or lowered == "0" then return false end
    return default
end

local function LoadConfig()
    local values = {
        ipc_dir = "",
        chat_prefix = "!pal",
        gift_command = "!palgift",
        vision_command = "!palook",

        hunger_threshold = "0.3",
        idle_min_seconds = "300",
        idle_max_seconds = "900",
        ambient_gift_min_seconds = "1200",
        ambient_gift_max_seconds = "2400",
        ambient_gift_chance = "0.3",
        response_timeout_seconds = "30",

        enable_deploy_recall_comments = "true",
        enable_hunger_comments = "true",
        enable_temperature_comments = "true",
        enable_ride_comments = "true",
        enable_combat_comments = "true",
        enable_idle_comments = "true",
        enable_gift_system = "true",
    }
    local f = io.open(CONFIG_PATH, "r")
    if not f then
        print(TAG .. " Could not open config file at " .. CONFIG_PATH .. ", using defaults.")
        return values
    end
    for line in f:lines() do
        local key, value = line:match("^%s*([%w_]+)%s*=%s*(.-)%s*$")
        if key and value and value ~= "" then
            values[key] = value
        end
    end
    f:close()
    return values
end

local CONFIG = LoadConfig()

local IPC_DIR       = CONFIG.ipc_dir
local REQUEST_PATH  = IPC_DIR .. "request.txt"
local RESPONSE_PATH = IPC_DIR .. "response.txt"
local SPECIES_NAMES_PATH = IPC_DIR .. "pal_species_names.txt"
local PREFIX        = CONFIG.chat_prefix
local GIFT_PREFIX   = CONFIG.gift_command
local VISION_PREFIX = CONFIG.vision_command
local POLL_MS = 500

if IPC_DIR == "" then
    print(TAG .. " WARNING: 'ipc_dir' is not set in config.txt. File exchange will not work.")
end

-- Real species display names, e.g. "WoolFox" -> "Cremis". Exported by the
-- launcher into the IPC folder from the user's own pal_data.json (a
-- static, user-compiled reference file -- not read live from the game).
-- Same simple key=value format as config.txt, so no JSON parsing needed
-- here either. Optional: if the launcher hasn't written this file yet
-- (or the user never set up pal_data.json), we just keep using the raw
-- CharacterID as before.
local function LoadSpeciesNames()
    local values = {}
    local f = io.open(SPECIES_NAMES_PATH, "r")
    if not f then return values end
    for line in f:lines() do
        local key, value = line:match("^%s*([%w_]+)%s*=%s*(.-)%s*$")
        if key and value and value ~= "" then
            values[key] = value
        end
    end
    f:close()
    return values
end

local SPECIES_NAMES = LoadSpeciesNames()
do
    local count = 0
    for _ in pairs(SPECIES_NAMES) do count = count + 1 end
    print(TAG .. " Loaded " .. count .. " species display names from " .. SPECIES_NAMES_PATH)
end

-- Hunger ratio (0-1) below which the Pal is considered "hungry".
local HUNGER_THRESHOLD = tonumber(CONFIG.hunger_threshold) or 0.3

-- Per-feature on/off switches, all editable from config.txt (and later,
-- from the GUI launcher).
local ENABLE_DEPLOY_RECALL = ToBool(CONFIG.enable_deploy_recall_comments, true)
local ENABLE_HUNGER        = ToBool(CONFIG.enable_hunger_comments, true)
local ENABLE_TEMPERATURE   = ToBool(CONFIG.enable_temperature_comments, true)
local ENABLE_RIDE          = ToBool(CONFIG.enable_ride_comments, true)
local ENABLE_COMBAT        = ToBool(CONFIG.enable_combat_comments, true)
local ENABLE_IDLE          = ToBool(CONFIG.enable_idle_comments, true)
local ENABLE_GIFTS         = ToBool(CONFIG.enable_gift_system, true)

-- ============================================================================
-- FILE HELPERS
-- ============================================================================

local function WriteEntireFile(path, content)
    local f = io.open(path, "w")
    if not f then
        print(TAG .. " ERROR: could not write to " .. path)
        return false
    end
    f:write(content)
    f:close()
    return true
end

local function ReadEntireFile(path)
    local f = io.open(path, "r")
    if not f then return nil end
    local content = f:read("*a")
    f:close()
    return content
end

local function FileExists(path)
    local f = io.open(path, "r")
    if f then f:close(); return true end
    return false
end

local function DeleteFile(path)
    os.remove(path)
end

-- ============================================================================
-- BASIC CHAT / WORLD HELPERS
-- ============================================================================

local _palUtilityCDO = nil
local function GetPalUtilityCDO()
    if _palUtilityCDO ~= nil then
        local ok = false
        pcall(function() ok = _palUtilityCDO:IsValid() end)
        if ok then return _palUtilityCDO end
        _palUtilityCDO = nil
    end
    pcall(function()
        _palUtilityCDO = StaticFindObject("/Script/Pal.Default__PalUtility")
    end)
    return _palUtilityCDO
end

local _world = nil
local function GetWorld()
    if _world ~= nil then
        local ok = false
        pcall(function() ok = _world:IsValid() end)
        if ok then return _world end
        _world = nil
    end
    pcall(function() _world = UEHelpers.GetWorld() end)
    return _world
end

local _playerController = nil
local function GetPlayerController()
    if _playerController ~= nil then
        local ok = false
        pcall(function() ok = _playerController:IsValid() end)
        if ok then return _playerController end
        _playerController = nil
    end
    pcall(function() _playerController = UEHelpers.GetPlayerController() end)
    return _playerController
end

local function SendChat(text)
    local cdo = GetPalUtilityCDO()
    local world = GetWorld()
    if not cdo then
        print(TAG .. " SendChat: no PalUtility CDO, cannot send.")
        return false
    end
    if not world then
        print(TAG .. " SendChat: no World, cannot send.")
        return false
    end
    if not text then
        return false
    end
    local ok, err = pcall(function()
        cdo:SendSystemToPlayerChat(world, text, {})
    end)
    if not ok then
        print(TAG .. " SendChat: SendSystemToPlayerChat errored: " .. tostring(err))
        -- The cached references might have gone stale without IsValid()
        -- catching it; force a fresh fetch on the next attempt.
        _palUtilityCDO = nil
        _world = nil
        return false
    end
    return true
end

-- ============================================================================
-- INVENTORY / REAL ITEM DELIVERY
-- Confirmed API: cdo:GetLocalInventoryData(world), invData:CountItemNum(FName),
-- invData:AddItem_ServerInternal(FName, count, false, 0.0). Success is
-- confirmed by comparing the count before and after (the ONLY reliable
-- signal -- the call itself does not tell you whether it worked).
-- ============================================================================

local _cachedInvData = nil
local function GetLocalInventoryData()
    if _cachedInvData then
        local ok = false
        pcall(function() ok = _cachedInvData:IsValid() end)
        if ok then return _cachedInvData end
        _cachedInvData = nil
    end
    local cdo = GetPalUtilityCDO()
    local world = GetWorld()
    if not cdo or not world then
        print(TAG .. " [gift debug] GetLocalInventoryData: missing cdo or world.")
        return nil
    end
    local invData
    local okCall, errCall = pcall(function() invData = cdo:GetLocalInventoryData(world) end)
    if not okCall then
        print(TAG .. " [gift debug] GetLocalInventoryData call errored: " .. tostring(errCall))
    end
    if not invData then
        print(TAG .. " [gift debug] GetLocalInventoryData returned nil.")
        return nil
    end
    local ok = false
    pcall(function() ok = invData:IsValid() end)
    if not ok then
        print(TAG .. " [gift debug] invData:IsValid() is false.")
        return nil
    end
    _cachedInvData = invData
    return invData
end

-- Returns true ONLY if the item count actually increased. This is how we
-- avoid promising an item the player never really received (e.g. a full
-- inventory silently rejecting the add).
local function GiveItem(itemId, count)
    local invData = GetLocalInventoryData()
    if not invData then
        print(TAG .. " [gift debug] GiveItem(" .. tostring(itemId) .. "): no inventory data, aborting.")
        return false
    end

    local before, after
    local okBefore = pcall(function() before = invData:CountItemNum(FName(itemId)) end)
    if not before then before = 0 end
    print(TAG .. " [gift debug] GiveItem(" .. tostring(itemId) .. "): before=" .. tostring(before) .. " (call ok=" .. tostring(okBefore) .. ")")

    local ok, err = pcall(function()
        -- Confirmed real signature (via UE4SS CXX header dump):
        -- AddItem_ServerInternal(FName StaticItemId, int32 Count,
        --   bool IsAssignPassive, float LogDelay, bool bNotifyLog)
        invData:AddItem_ServerInternal(FName(itemId), count, false, 0.0, true)
    end)
    if not ok then
        print(TAG .. " [gift debug] AddItem_ServerInternal errored: " .. tostring(err))
        return false
    end

    pcall(function() after = invData:CountItemNum(FName(itemId)) end)
    print(TAG .. " [gift debug] GiveItem(" .. tostring(itemId) .. "): after=" .. tostring(after))
    if not after then return false end

    return after > before
end

-- ============================================================================
-- ACTIVE PAL DETECTION (name + element + hunger)
-- ============================================================================

local ELEMENT_NAME = {
    [0] = "None", [1] = "Normal", [2] = "Fire", [3] = "Water", [4] = "Leaf",
    [5] = "Electricity", [6] = "Ice", [7] = "Earth", [8] = "Dark", [9] = "Dragon",
}

local _cachedHolder = nil
local function GetOtomoHolder(world)
    if _cachedHolder then
        local ok = false
        pcall(function() ok = _cachedHolder:IsValid() end)
        if ok then return _cachedHolder end
        _cachedHolder = nil
    end
    local cdo = GetPalUtilityCDO()
    if not cdo then return nil end
    local pc, holder
    pcall(function() pc = cdo:GetLocalPalPlayerController(world) end)
    if not pc or not pc:IsValid() then return nil end
    pcall(function() holder = cdo:GetOtomoHolderComponent(pc) end)
    if not holder or not holder:IsValid() then return nil end
    _cachedHolder = holder
    return holder
end

local function GetActivePalHandle()
    local world = GetWorld()
    if not world then return nil end
    local holder = GetOtomoHolder(world)
    if not holder then return nil end
    local handle
    pcall(function() handle = holder:TryGetSpawnedOtomoHandle() end)
    -- Confirmed in ChickNomad's source: TryGetSpawnedOtomoHandle() can
    -- return a non-nil handle that is NOT actually valid (e.g. when no
    -- Pal has ever been deployed yet). Treat an invalid handle as "no Pal".
    if handle then
        local ok, valid = pcall(function() return handle:IsValid() end)
        if not ok or not valid then handle = nil end
    end
    return handle
end

local function FNameToString(fname)
    if fname == nil then return nil end
    local ok, s = pcall(function() return fname:ToString() end)
    if ok and type(s) == "string" and s ~= "" and s ~= "None" then
        return s
    end
    return nil
end

local function GetPalName(handle)
    if not handle then return nil end
    local indParam
    pcall(function() indParam = handle:TryGetIndividualParameter() end)
    if not indParam or not indParam:IsValid() then return nil end

    local nick
    pcall(function() nick = indParam:GetNickNameByCheckBlockedUser() end)
    local nickStr = FNameToString(nick)
    if nickStr then return nickStr end

    local cid
    pcall(function() cid = indParam:GetCharacterID() end)
    local cidStr = FNameToString(cid)
    if not cidStr then return "Pal" end

    -- No nickname set: prefer the real species display name (from the
    -- user's pal_data.json, exported by the launcher) over the raw
    -- internal CharacterID.
    return SPECIES_NAMES[cidStr] or cidStr
end

local function GetPalActor(handle)
    if not handle then return nil end
    local actor
    pcall(function() actor = handle:TryGetIndividualActor() end)
    if actor and actor:IsValid() then return actor end
    return nil
end

-- Stable per-individual key: CharacterID + InstanceId. Two Pals of the same
-- species have the same CharacterID but a different InstanceId, so this
-- tells them apart. Confirmed API: TryGetIndividualParameter():GetCharacterID()
-- and :GetInstanceId() (used by ChickNomad for the same purpose: bond
-- system and per-individual personality).
-- Confirmed via UE4SS CXX header dump: there is no GetInstanceId()
-- method (the old code was checking for one that never existed, which is
-- why the instance part was always empty). The real per-individual ID
-- lives in the IndividualId FIELD (FPalInstanceID, with PlayerUId and
-- InstanceId as FGuid sub-fields). We read it via direct field access
-- (not a function call), the same safe pattern already used for
-- comp.ElementType1 -- not a UFunction return value, so it isn't at risk
-- of the use-after-free bug that crashed the game with GetPassiveSkillList().
local function GetPalKey(handle)
    if not handle then return nil end
    local indParam
    pcall(function() indParam = handle:TryGetIndividualParameter() end)
    if not indParam or not indParam:IsValid() then return nil end

    local cid
    pcall(function() cid = indParam:GetCharacterID() end)
    local cidStr = FNameToString(cid) or "unknown"

    local iidStr = ""
    pcall(function()
        local guid = indParam.IndividualId.InstanceId
        iidStr = string.format("%08X%08X%08X%08X", guid.A or 0, guid.B or 0, guid.C or 0, guid.D or 0)
    end)

    return cidStr .. "#" .. iidStr
end

local function GetPalElement(handle)
    local actor = GetPalActor(handle)
    if not actor then return "None" end
    local comp
    pcall(function() comp = actor:GetCharacterParameterComponent() end)
    if not comp or not comp:IsValid() then return "None" end
    local e1
    pcall(function() e1 = comp.ElementType1 end)
    local val = tonumber(e1)
    if val and ELEMENT_NAME[val] then return ELEMENT_NAME[val] end
    return "None"
end

-- DISABLED after a full game crash was reported right after this call
-- returned a value (type=table, Num/Length=nil). A crash can bypass
-- pcall protection entirely if it happens at the native engine level,
-- so we're not risking guessing at this again -- it needs proper
-- investigation (likely UE4SS community input) before re-enabling.
-- Always returns "" for now; every caller already handles that safely
-- (falls back to no passive-based personality hint).
local function GetPalPassiveIds(handle)
    return ""
end

-- Confirmed via UE4SS CXX header dump: UPalIndividualCharacterParameter
-- has int32 GetFriendshipRank() and int32 GetFriendshipPoint() -- simple
-- scalar returns (not TArray/FString), so unlike GetPassiveSkillList()
-- these should NOT be affected by the confirmed UE4SS use-after-free bug
-- on complex return types (scalars are copied by value immediately, no
-- dangling pointer). This is the game's REAL trust/bond value, not
-- something we invented ourselves.
local function GetPalFriendship(handle)
    if not handle then return "" end
    local indParam
    pcall(function() indParam = handle:TryGetIndividualParameter() end)
    if not indParam or not indParam:IsValid() then return "" end

    local rank, point
    local ok1 = pcall(function() rank = indParam:GetFriendshipRank() end)
    local ok2 = pcall(function() point = indParam:GetFriendshipPoint() end)
    if not ok1 or not ok2 then
        print(TAG .. " [friendship debug] GetFriendshipRank/Point errored.")
        return ""
    end
    if rank == nil or point == nil then return "" end
    return tostring(rank) .. "," .. tostring(point)
end

-- The Pal's OWN hunger (not the player's): confirmed, read from the Pal's
-- actor via its CharacterParameterComponent.
local function GetPalHungerRatio(handle)
    local actor = GetPalActor(handle)
    if not actor then return nil end
    local comp
    pcall(function() comp = actor:GetCharacterParameterComponent() end)
    if not comp or not comp:IsValid() then return nil end
    local cur, max
    pcall(function() cur = tonumber(comp:GetFullStomach()) end)
    pcall(function() max = tonumber(comp:GetMaxFullStomach()) end)
    if not cur or not max or max <= 0 then return nil end
    local ratio = cur / max
    if ratio < 0 then ratio = 0 elseif ratio > 1 then ratio = 1 end
    return ratio
end

-- ============================================================================
-- SHARED EVENT TRIGGER: builds and writes the request for the launcher.
-- ============================================================================

local _waitingForResponse = false
local _requestStartedAt = nil
local _pendingPalName = nil
local RESPONSE_TIMEOUT_SECONDS = tonumber(CONFIG.response_timeout_seconds) or 30

local function TriggerEvent(eventType, palName, palElement, palKey, palPassives, palFriendship, content)
    if _waitingForResponse then
        print(TAG .. " Still waiting for a previous response, ignoring event '" .. eventType .. "'.")
        return
    end
    if not palName then palName = "Pal" end
    if not palElement then palElement = "None" end
    if not palKey then palKey = "unknown#" end
    if not palPassives then palPassives = "" end
    if not palFriendship then palFriendship = "" end
    if not content then content = "" end

    local body = palName .. "\n" .. palElement .. "\n" .. palKey .. "\n" .. palPassives .. "\n" .. palFriendship .. "\n" .. eventType .. "\n" .. content
    local written = WriteEntireFile(REQUEST_PATH, body)
    if written then
        _waitingForResponse = true
        _requestStartedAt = os.clock()
        _pendingPalName = palName
        print(TAG .. " Event '" .. eventType .. "' (" .. palName .. "/" .. palElement .. ") written to " .. REQUEST_PATH)
    end
end

-- ============================================================================
-- CHAT HOOK
-- ============================================================================

-- ============================================================================
-- GIFTS: small, generic whitelist (not per-species). Money/Leather/Wool/Bone
-- are confirmed real Palworld item IDs (verified in ChickNomad's own
-- comments against dumps/itemdata.lua). Berries is confirmed from a
-- separate, independent source (a public Palworld console-commands list
-- showing "DropItem Berries 1" as a real, distinct item from BerrySeeds).
-- Never inventing an ID here, since a wrong one shows up as a broken "?"
-- item in-game instead of failing safely.
-- ============================================================================

local GIFT_WHITELIST = { "Berries", "Money", "Leather", "Wool", "Bone" }

local function PickRandomGiftId()
    return GIFT_WHITELIST[math.random(1, #GIFT_WHITELIST)]
end

-- Decides an item, actually attempts to give it, and only then reports the
-- REAL outcome to the launcher (trigger:outcome:itemId), so the LLM never
-- narrates an item the player didn't actually receive.
local function AttemptGift(trigger)
    if not ENABLE_GIFTS then return end
    local handle = GetActivePalHandle()
    if not handle then return end

    local itemId = PickRandomGiftId()
    local success = GiveItem(itemId, 1)

    local content
    if success then
        content = trigger .. ":success:" .. itemId
    else
        content = trigger .. ":failure:"
    end

    TriggerEvent("gift_check", GetPalName(handle), GetPalElement(handle), GetPalKey(handle), GetPalPassiveIds(handle), GetPalFriendship(handle), content)
end

local function RegisterChatHook()
    local ok, err = pcall(function()
        RegisterHook("/Script/Pal.PalGameStateInGame:BroadcastChatMessage", function(ctx, chatMsg)
            pcall(function()
                local raw = chatMsg and chatMsg:get()
                local msg = raw and raw.Message and raw.Message:ToString()
                if not msg then return end

                local handle = GetActivePalHandle()

                if msg:sub(1, #GIFT_PREFIX) == GIFT_PREFIX then
                    if not handle then
                        print(TAG .. " No Pal is out of its sphere, ignoring the gift command.")
                        return
                    end
                    AttemptGift("requested")
                    return
                end

                if msg:sub(1, #VISION_PREFIX) == VISION_PREFIX then
                    if not handle then
                        print(TAG .. " No Pal is out of its sphere, ignoring the vision command.")
                        return
                    end
                    TriggerEvent("vision_check", GetPalName(handle), GetPalElement(handle), GetPalKey(handle), GetPalPassiveIds(handle), GetPalFriendship(handle), "")
                    return
                end

                if msg:sub(1, #PREFIX) == PREFIX then
                    local playerMessage = msg:sub(#PREFIX + 1):gsub("^%s+", "")

                    if not handle then
                        print(TAG .. " No Pal is out of its sphere, ignoring the message.")
                        return
                    end

                    local palName = GetPalName(handle)
                    local palElement = GetPalElement(handle)
                    local palKey = GetPalKey(handle)
                    local palPassives = GetPalPassiveIds(handle)
                    local palFriendship = GetPalFriendship(handle)
                    TriggerEvent("chat", palName, palElement, palKey, palPassives, palFriendship, playerMessage)
                end
            end)
        end)
    end)
    if ok then
        print(TAG .. " Chat hook registered successfully.")
    else
        print(TAG .. " ERROR registering the hook: " .. tostring(err))
    end
end

-- ============================================================================
-- DEPLOY / RECALL
-- Checked every tick by comparing state (handle present or not) between
-- ticks, a simplified single-Pal version (not a full party scan). We
-- tried gating this on 4 "OnUpdateOtomoHolder*" hooks first (like
-- ChickNomad does), but they didn't fire reliably in practice -- a real
-- deploy went undetected -- so this just polls directly instead, same as
-- every other Check* function already does.
-- ============================================================================

local _wasDeployed = false
local _lastPalName = nil
local _lastPalElement = nil
local _lastPalKey = nil
local _lastPalPassives = nil
local _lastPalFriendship = nil

local function CheckDeployRecall()
    if not ENABLE_DEPLOY_RECALL then return end

    local handle = GetActivePalHandle()
    local isDeployed = (handle ~= nil)

    if isDeployed then
        _lastPalName = GetPalName(handle)
        _lastPalElement = GetPalElement(handle)
        _lastPalKey = GetPalKey(handle)
        _lastPalPassives = GetPalPassiveIds(handle)
        _lastPalFriendship = GetPalFriendship(handle)
    end

    if isDeployed and not _wasDeployed then
        TriggerEvent("deploy", _lastPalName, _lastPalElement, _lastPalKey, _lastPalPassives, _lastPalFriendship, "")
    elseif not isDeployed and _wasDeployed then
        TriggerEvent("recall", _lastPalName, _lastPalElement, _lastPalKey, _lastPalPassives, _lastPalFriendship, "")
    end

    _wasDeployed = isDeployed
end

-- ============================================================================
-- HUNGER (the Pal's own)
-- ============================================================================

local _wasHungry = false

local function CheckHunger()
    if not ENABLE_HUNGER then return end
    local handle = GetActivePalHandle()
    if not handle then _wasHungry = false; return end

    local ratio = GetPalHungerRatio(handle)
    if not ratio then return end

    local isHungry = (ratio < HUNGER_THRESHOLD)
    if isHungry and not _wasHungry then
        TriggerEvent("hunger", GetPalName(handle), GetPalElement(handle), GetPalKey(handle), GetPalPassiveIds(handle), GetPalFriendship(handle), "")
    end
    _wasHungry = isHungry
end

-- ============================================================================
-- TEMPERATURE (best-effort, see note above: no clean global getter)
-- ============================================================================

local _tempComp = nil
local _lastTempState = nil

local function GetBodyTempState()
    if _tempComp ~= nil then
        local ok = false
        pcall(function() ok = _tempComp:IsValid() end)
        if not ok then _tempComp = nil end
    end
    if _tempComp == nil then
        pcall(function() _tempComp = FindFirstOf("PalBodyTemperatureComponent") end)
    end
    if not _tempComp then return nil end

    -- UNCONFIRMED attempt: the real signature is
    -- GetTemperatureInfo(FPalTemperatureInfo& OutInfo), an output-by-
    -- reference struct parameter, not a return value like we assumed
    -- before. Passing an empty table is a common UE4SS pattern for this
    -- kind of parameter, but it's not verified to work for this specific
    -- struct -- the debug log below will tell us quickly if it doesn't.
    local outInfo = {}
    local ok, err = pcall(function()
        _tempComp:GetTemperatureInfo(outInfo)
    end)
    if not ok then
        print(TAG .. " [temp debug] GetTemperatureInfo errored: " .. tostring(err))
        return nil
    end

    local state
    pcall(function() state = tonumber(outInfo.CurrentBodyState) end)
    if state == nil then
        print(TAG .. " [temp debug] Call succeeded but CurrentBodyState was not readable from the output table.")
    end
    return state
end

local function CheckTemperature()
    if not ENABLE_TEMPERATURE then return end
    local handle = GetActivePalHandle()
    if not handle then return end

    local state = GetBodyTempState()
    if state == nil then return end
    if state == _lastTempState then return end
    _lastTempState = state

    if state == 1 then
        TriggerEvent("cold", GetPalName(handle), GetPalElement(handle), GetPalKey(handle), GetPalPassiveIds(handle), GetPalFriendship(handle), "")
    elseif state == 2 then
        TriggerEvent("heat", GetPalName(handle), GetPalElement(handle), GetPalKey(handle), GetPalPassiveIds(handle), GetPalFriendship(handle), "")
    end
end

-- ============================================================================
-- RIDING (the player's, unambiguous)
-- ============================================================================

local _wasRiding = false

local function CheckRiding()
    if not ENABLE_RIDE then return end
    local handle = GetActivePalHandle()
    if not handle then _wasRiding = false; return end

    local riding, flying, swimming = false, false, false
    pcall(function()
        local pc = GetPlayerController()
        if not pc then return end
        if pc.IsRiding then riding = (pc:IsRiding() == true) end
        if riding and pc.IsRidingFlyPal then flying = (pc:IsRidingFlyPal() == true) end
        if riding and pc.IsSwimming then swimming = (pc:IsSwimming() == true) end
    end)

    if riding and not _wasRiding then
        local detail = flying and "flying" or (swimming and "swimming" or "ground")
        TriggerEvent("ride_start", GetPalName(handle), GetPalElement(handle), GetPalKey(handle), GetPalPassiveIds(handle), GetPalFriendship(handle), detail)
    elseif not riding and _wasRiding then
        TriggerEvent("ride_end", GetPalName(handle), GetPalElement(handle), GetPalKey(handle), GetPalPassiveIds(handle), GetPalFriendship(handle), "")
    end
    _wasRiding = riding
end

-- ============================================================================
-- COMBAT (simple signal: "attacking right now" or not, no specific move
-- name -- that would need ChickNomad's own compiled 392-move ID table,
-- which we're intentionally not copying).
-- ============================================================================

-- Confirmed API: actor.ActionComponent:GetCurrentAction():GetWazaID().
-- A WazaID > 0 means a real attack is in progress; work/idle actions
-- return 0 or nil (per ChickNomad's own comment on this mechanism).
local function IsPalAttacking(handle)
    local actor = GetPalActor(handle)
    if not actor then return false end
    local comp
    pcall(function() comp = actor.ActionComponent end)
    if not comp then return false end
    local action
    pcall(function() action = comp:GetCurrentAction() end)
    if not action then return false end
    -- GetCurrentAction() can return a non-nil wrapper around an invalid
    -- UObject (e.g. when the Pal isn't doing anything right now). Calling
    -- a method on that throws "UObject instance is nullptr" even inside
    -- pcall's protected call, so we must check IsValid() first, same as
    -- with GetActivePalHandle().
    local validOk, isValid = pcall(function() return action:IsValid() end)
    if not validOk or not isValid then return false end
    local wid
    pcall(function()
        if action.GetWazaID then wid = tonumber(action:GetWazaID()) end
    end)
    return (wid ~= nil and wid > 0)
end

local _wasFighting = false

local function CheckCombat()
    if not ENABLE_COMBAT then return end
    local handle = GetActivePalHandle()
    if not handle then _wasFighting = false; return end

    local isFighting = IsPalAttacking(handle)
    if isFighting and not _wasFighting then
        TriggerEvent("combat", GetPalName(handle), GetPalElement(handle), GetPalKey(handle), GetPalPassiveIds(handle), GetPalFriendship(handle), "")
    end
    _wasFighting = isFighting
end

-- ============================================================================
-- IDLE CHATTER: says something on its own every once in a while, even if
-- nothing in particular happened. Same random-interval pattern confirmed
-- in ChickNomad's own AutoChatter feature.
-- ============================================================================

local IDLE_MIN_SECONDS = tonumber(CONFIG.idle_min_seconds) or 300
local IDLE_MAX_SECONDS = tonumber(CONFIG.idle_max_seconds) or 900

local function RandomBetween(minVal, maxVal)
    return minVal + math.random() * (maxVal - minVal)
end

local _nextIdleAt = os.clock() + RandomBetween(IDLE_MIN_SECONDS, IDLE_MAX_SECONDS)

local function CheckIdleChatter()
    if not ENABLE_IDLE then return end
    local handle = GetActivePalHandle()
    if not handle then return end

    if os.clock() < _nextIdleAt then return end
    _nextIdleAt = os.clock() + RandomBetween(IDLE_MIN_SECONDS, IDLE_MAX_SECONDS)

    TriggerEvent("idle", GetPalName(handle), GetPalElement(handle), GetPalKey(handle), GetPalPassiveIds(handle), GetPalFriendship(handle), "")
end

-- ============================================================================
-- AMBIENT GIFT: rare, unprompted -- most of the time the timer fires and
-- nothing happens (AMBIENT_GIFT_CHANCE), to keep it a genuine surprise
-- instead of a predictable clock.
-- ============================================================================

local AMBIENT_GIFT_MIN_SECONDS = tonumber(CONFIG.ambient_gift_min_seconds) or 1200
local AMBIENT_GIFT_MAX_SECONDS = tonumber(CONFIG.ambient_gift_max_seconds) or 2400
local AMBIENT_GIFT_CHANCE = tonumber(CONFIG.ambient_gift_chance) or 0.3

local _nextAmbientGiftAt = os.clock() + RandomBetween(AMBIENT_GIFT_MIN_SECONDS, AMBIENT_GIFT_MAX_SECONDS)

local function CheckAmbientGift()
    local handle = GetActivePalHandle()
    if not handle then return end

    if os.clock() < _nextAmbientGiftAt then return end
    _nextAmbientGiftAt = os.clock() + RandomBetween(AMBIENT_GIFT_MIN_SECONDS, AMBIENT_GIFT_MAX_SECONDS)

    if math.random() > AMBIENT_GIFT_CHANCE then return end
    AttemptGift("ambient")
end

-- ============================================================================
-- MAIN LOOP: launcher response polling + the spontaneous event checks.
-- ============================================================================

local function RegisterMainLoop()
    LoopAsync(POLL_MS, function()
        ExecuteInGameThread(function()
            CheckDeployRecall()
            CheckHunger()
            CheckTemperature()
            CheckRiding()
            CheckCombat()
            CheckIdleChatter()
            CheckAmbientGift()
        end)

        if not _waitingForResponse and FileExists(RESPONSE_PATH) then
            -- Leftover from a request that already timed out; discard it
            -- silently so a late reply never gets shown out of context.
            DeleteFile(RESPONSE_PATH)
        end

        if _waitingForResponse and _requestStartedAt and (os.clock() - _requestStartedAt) > RESPONSE_TIMEOUT_SECONDS then
            print(TAG .. " Timed out waiting for a response (" .. RESPONSE_TIMEOUT_SECONDS .. "s), giving up on this one.")
            _waitingForResponse = false
            _requestStartedAt = nil
            _pendingPalName = nil
            DeleteFile(RESPONSE_PATH)  -- in case it shows up late, don't send a stale reply later
        end

        if _waitingForResponse and FileExists(RESPONSE_PATH) then
            local response = ReadEntireFile(RESPONSE_PATH)
            local palName = _pendingPalName or "Pal"
            DeleteFile(RESPONSE_PATH)
            _waitingForResponse = false
            _requestStartedAt = nil
            _pendingPalName = nil

            if response and response ~= "" then
                local displayText = palName .. ": " .. response
                ExecuteInGameThread(function()
                    local sent = SendChat(displayText)
                    if sent then
                        print(TAG .. " Response shown in chat: " .. displayText)
                    else
                        print(TAG .. " Response FAILED to show in chat (see SendChat error above): " .. displayText)
                    end
                end)
            end
        end
    end)
end

RegisterChatHook()
RegisterMainLoop()
print(TAG .. " Loaded. Type '" .. PREFIX .. " something' in the game chat (with a Pal out) to test.")