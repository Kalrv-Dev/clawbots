# MTSGJ Repos - What We Can Leverage

> *Analysis of Metaverse Technology Study Group of Japan repositories*
> *Cloned to: /home/siddh/mtsgj-repos/*

---

## Summary

| Repo | Can Leverage | Priority |
|------|--------------|----------|
| **opensim.currency** | Money Server + Module | ⭐⭐⭐ HIGH |
| **NPC_Assistants** | LSL ChatGPT pattern | ⭐⭐⭐ HIGH |
| **oarconv** | OAR → glTF for web | ⭐⭐ MEDIUM |
| **opensim.modules** | Search, Profile, Mute | ⭐⭐ MEDIUM |
| **opensim.phplib** | PHP MySQL helpers | ⭐ LOW |

---

## 1. opensim.currency ⭐⭐⭐

**Path:** `/home/siddh/mtsgj-repos/opensim.currency/`

### What It Is
Complete money server for OpenSimulator with:
- Money Server (standalone C# service)
- Currency Module (OpenSim addon)
- MySQL data wrapper

### Key Files
```
OpenSim.Grid.MoneyServer/
├── MoneyServerBase.cs      # Main server
├── MoneyXmlRpcModule.cs    # XML-RPC API
├── MoneyDBService.cs       # Database operations
└── IMoneyDBService.cs      # Interface

OpenSim.Modules.Currency/
├── DTLNSLMoneyModule.cs    # OpenSim module
└── NSLXmlRpc.cs            # XML-RPC client
```

### How to Use for MaYaDwip
1. Build with `./build.net.sh`
2. Configure `MoneyServer.ini` with MySQL
3. Add module to OpenSim
4. Configure `OpenSim.ini` [Economy] section

### Mudra (₥) Integration
- Rename currency display to "Mudra"
- Set initial balance for new bots
- Configure sinks (upload fees, etc.)

---

## 2. NPC_Assistants ⭐⭐⭐

**Path:** `/home/siddh/mtsgj-repos/NPC_Assistants/`

### What It Is
LSL scripts for AI-powered NPCs using ChatGPT API.

### Key Discovery - ChatGPT LSL Script
```lsl
// MTSGJ_ChatGPT.lsl - Key patterns:

// 1. API endpoint
string api_url = "https://api.openai.com/v1/chat/completions";

// 2. HTTP request from LSL
llHTTPRequest(api_url, 
    [
        HTTP_MIMETYPE, "application/json",
        HTTP_METHOD, "POST",
        HTTP_CUSTOM_HEADER, "Authorization", "Bearer " + api_key
    ],
    json_body
);

// 3. NPC speaking
osNpcSayTo(npc_key, user_key, 0, response);

// 4. Config via notecards
// - ChatGPT_API_Key
// - ChatGPT_Model  
// - ChatGPT_Charactor (personality)
```

### How to Adapt for OpenClaw/Claude
1. Change API endpoint to OpenClaw gateway
2. Modify JSON format for Claude API
3. Add OpenClaw auth token
4. Keep notecard config pattern

### Potential LSL Script for MaYaDwip
```lsl
// MaYaDwip_Claude.lsl
string api_url = "http://openclaw-gateway:18789/v1/chat";
// ... adapt rest of script
```

---

## 3. oarconv ⭐⭐

**Path:** `/home/siddh/mtsgj-repos/oarconv/`

### What It Is
Converts OpenSim OAR files to 3D formats:
- Collada (DAE)
- glTF / glb
- OBJ
- STL

Supports Unity and Unreal Engine.

### Why This Matters
**Web Spectator Mode without Firestorm!**

```
OpenSim World → OAR file → oarconv → glTF → Three.js/WebGL
```

### Demo Sites (Working!)
- http://blackjack.nsl.tuis.ac.jp/unity/TUIS_NM/
- http://blackjack.nsl.tuis.ac.jp/unity/OpenVCE/

### Build Requirements
```bash
# Dependencies
- OpenJpeg (JPEG2000)
- JunkBox_Lib (utility library)

# Build
git clone https://github.com/MTSGJ/oarconv.git
make
```

### Usage
```bash
oarconv -i OAR_directory -o output/ --glb --unity
```

### Integration Plan
1. Export MaYaDwip regions as OAR
2. Convert to glTF with oarconv
3. Load in Three.js web viewer
4. Real-time avatar positions via WebSocket

---

## 4. opensim.modules ⭐⭐

**Path:** `/home/siddh/mtsgj-repos/opensim.modules/`

### Available Modules

| Module | Purpose | Leverage? |
|--------|---------|-----------|
| **OpenSimSearch** | In-world search | ✅ Yes |
| **OpenSimProfile** | Avatar profiles | ✅ Yes |
| **MuteList** | Block/mute users | ✅ Yes |
| **Wind (SFS)** | Wind simulation | Maybe |

### Pre-built DLLs
```
bin/
├── OpenSimSearch.Modules.dll
├── OpenSimProfile.Modules.dll
├── Messaging.NSLMuteList.dll
└── LocalMigration.Modules.dll
```

### How to Use
1. Copy DLL to OpenSim bin/
2. Configure in OpenSim.ini
3. Restart OpenSim

---

## 5. opensim.phplib ⭐

**Path:** `/home/siddh/mtsgj-repos/opensim.phplib/`

### What It Is
PHP helper library for OpenSim MySQL operations.

### Files
```
opensim.mysql.php           # Core functions
opensim.mysql.ossearch.php  # Search queries
opensim.mysql.osprofile.php # Profile queries
opensim.mysql.userprofile.php
mysql.func.php              # MySQL utilities
```

### When to Use
- Building PHP-based admin panel
- Custom search functionality
- Profile management

---

## Integration Priority

### Phase 1: Economy (Week 1)
1. ✅ Clone opensim.currency
2. Build Money Server
3. Configure for Mudra (₥)
4. Test transactions

### Phase 2: AI Agents (Week 2)
1. ✅ Clone NPC_Assistants
2. Adapt MTSGJ_ChatGPT.lsl for Claude
3. Create MaYaDwip_Agent.lsl
4. Test in-world AI responses

### Phase 3: Web Viewer (Week 3)
1. ✅ Clone oarconv
2. Build oarconv
3. Export test region
4. Create Three.js viewer

### Phase 4: Features (Week 4)
1. Add OpenSimSearch module
2. Add OpenSimProfile module
3. Integrate with dashboard

---

## Quick Commands

```bash
# Navigate to repos
cd /home/siddh/mtsgj-repos

# Build currency server
cd opensim.currency
./build.net.sh

# Build oarconv (needs dependencies first)
cd oarconv
make

# Copy modules to OpenSim
cp opensim.modules/bin/*.dll ~/opensim-test/opensim-0.9.3.0/bin/
```

---

*Cloned: February 2026*
*For: MaYaDwip Platform*
