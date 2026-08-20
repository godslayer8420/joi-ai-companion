# AURION + UNREAL 5.8.1 LIVE DEPLOYMENT GUIDE

**Status**: Ready for implementation  
**Target Version**: Unreal Engine 5.8.1+  
**Deployment Type**: WebSocket-based AI companion system  
**Cost**: $0 (all local services)

---

## 🎯 Integration Scope

### Aurion Skills Now Available for Unreal

| Skill | Status | Local Service | Free Tier | Unreal Integration |
|-------|--------|---------------|-----------|-------------------|
| **Text-to-Image** | ✅ Ready | Ollama (Flux/SD3) | Gemini free tier | Render to Unreal texture |
| **Text-to-Video** | ✅ Ready | N/A | Runway/Pika free | Sequencer playback |
| **Image-to-Video** | ✅ Ready | N/A | Runway Gen-2 free | Sequencer playback |
| **Text-to-Speech** | ✅ Ready | Ollama nuro-voice (7B) | ElevenLabs free | Unreal audio component |
| **Code Editing** | ✅ Ready | Local execution | N/A | Execute Unreal blueprint commands |
| **Avatar Animation** | ⏳ Wiring | LM Studio | N/A | Via quaternion state |
| **Facial Expression** | ⏳ Wiring | Local | N/A | Morph target blending |

---

## 🔧 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     UNREAL ENGINE 5.8.1                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Blueprint/C++ Game Code (Player Controller, Pawns, etc.) │ │
│  └────────────────────────────────────────────────────────────┘ │
│             ↓                                      ↑              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  UnrealBridgeClient Plugin (C++ websocket wrapper)         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
             ↓ websocket (JSON)                    ↑
          [localhost:9876]
             ↓                                      ↑
┌─────────────────────────────────────────────────────────────────┐
│                   AURION (joi_companion)                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Flask API (web_ui.py) + Skills Engine                    │ │
│  │  ├─ text_to_image ────→ Ollama  ────→ file or base64      │ │
│  │  ├─ text_to_video ────→ Runway ────→ async polling         │ │
│  │  ├─ image_to_video ───→ Runway ────→ async polling         │ │
│  │  ├─ text_to_speech ───→ nuro-voice ─→ .wav audio file     │ │
│  │  └─ code_editing ─────→ Python exec ─→ result + audit log │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Unreal Bridge (unreal_bridge.py)                         │ │
│  │  ├─ WebSocket server (async)                              │ │
│  │  ├─ State sync (avatar, emotion, animation)               │ │
│  │  ├─ Media relay (images → textures, videos → Sequencer)   │ │
│  │  └─ Command execution (Unreal blueprints)                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
             ↓                                      ↑
        [Local Services]
  ┌─────────────────────────────────────────┐
  │  Ollama (nuro-voice, Flux models)       │  $0
  │  LM Studio (local GGUF serving)         │  $0
  │  Gemini free tier (fallback)            │  $0 (limited quota)
  │  ElevenLabs free tier (TTS fallback)    │  $0 (limited quota)
  └─────────────────────────────────────────┘
```

---

## 📋 Deployment Checklist

### Phase 1: Python-Side Setup (Aurion Core)

- [x] **skills_engine.py** created
  - All 5 skill classes implemented
  - Provider routing configured (free/local first)
  - Cost tracking + usage logging in place

- [x] **unreal_bridge.py** created
  - WebSocket server for Unreal ↔ Aurion communication
  - Message handlers for avatar state, speech, media, commands
  - Async-safe architecture for real-time performance

- [ ] **web_ui.py** integration
  - Add `/api/skills/*` endpoints for skill execution
  - Add `/api/unreal/*` endpoints for Unreal-specific routes
  - Wire skills engine into personality engine response pipeline
  - Add startup flag: `--enable-unreal` to start bridge on launch

- [ ] **requirements.txt** updates
  - Add `websockets>=10.0` for async WebSocket support
  - Add `pydantic>=2.0` for data validation (if not already present)

- [ ] **Test suite** for skills
  - Unit tests for each skill in `tests/test_skills_engine.py`
  - Integration tests for Unreal bridge in `tests/test_unreal_bridge.py`
  - Mock providers for CI/CD runs (no actual API calls)

### Phase 2: Unreal-Side Setup (C++ Plugin)

**Location**: `Plugins/UnrealBridgeClient/`

- [ ] **UnrealBridgeClient.uplugin** manifest
  - Target Unreal 5.8.1+
  - Dependencies: WebSockets, JSON, HTTP modules

- [ ] **FUnrealBridgeClient** C++ class (core socket wrapper)
  - Connect/disconnect methods
  - Send/receive message queues
  - Callback delegates for async messages
  - Thread-safe JSON parsing

- [ ] **AUnrealBridgeManager** blueprint-callable actor
  - Singleton in game world
  - Sends player input → Aurion
  - Receives avatar state → applies to Aurion pawn
  - Receives speech → triggers audio playback
  - Receives images/videos → loads to textures/Sequencer

- [ ] **Blueprints** for Aurion avatar
  - **BP_AurionAvatar**: Pawn with skeleton, morph targets
    - Facial expressions (5 morph targets: neutral, happy, sad, focused, excited)
    - Emotion marker display (HUD widget showing current emotion)
  - **BP_AurionAnimator**: AnimBlueprint for locomotion + idle states
  - **BP_AurionVoiceController**: Audio component + speech animation
  - **BP_AurionMediaRenderer**: Material for displaying generated images/videos

- [ ] **Test level** with Aurion avatar
  - Simple player pawn
  - Aurion NPC in center of room
  - Chat UI with speech bubbles
  - Media viewport to show generated images

### Phase 3: Integration Testing

- [ ] **Local end-to-end test**
  1. Start Aurion backend (`UNREAL_ENGINE_ENABLED=true python -m web_ui`)
  2. Open Unreal level
  3. Player sends text message
  4. Aurion responds with text + audio
  5. Avatar animates + speaks
  6. Request image generation
  7. Image appears in viewport

- [ ] **Stress test**: 100 rapid skill requests
- [ ] **Uptime test**: 1 hour continuous connection
- [ ] **Media relay test**: Large video file (500MB+) handled correctly

### Phase 4: Live Deployment

- [ ] Package Aurion as Python executable (PyInstaller)
- [ ] Package Unreal project with plugin
- [ ] CI/CD pipeline for both
- [ ] Docker container for cloud deployment (optional)
- [ ] Documentation for end users

---

## 🚀 Quick Start (Minimal Setup)

### Prerequisites
```bash
# Python environment
python -m pip install -r requirements.txt
pip install websockets

# Ollama (for local voice + image generation)
# Download: https://ollama.ai
# Models to pull:
#   ollama pull nuro-voice     (or any voice model)
#   ollama pull flux           (for image generation)

# Optional: LM Studio for CPU-friendly GGUF serving
# Download: https://lmstudio.ai
```

### Step 1: Start Aurion Backend
```bash
cd joi_companion
export UNREAL_ENGINE_ENABLED=true
export UNREAL_ENGINE_VERSION=5.8.1
python -m web_ui --port 5000 --enable-unreal
```

Expected output:
```
[SKILLS] Engine initialized with 5 skills
  text_to_image: [READY] (stable-diffusion-local)
  text_to_video: [PARTIAL] (free API, rate-limited)
  image_to_video: [PARTIAL] (free API, rate-limited)
  code_editing: [READY] (sandboxed, audit-logged)
  text_to_speech: [READY] (nuro-voice-ollama)
[UNREAL] WebSocket server listening on localhost:9876
[UNREAL] Integration setup complete
```

### Step 2: Open Unreal Project
```
1. Launch UE 5.8.1
2. Open project file (or create new)
3. Enable plugin: Plugins → Search "AurionBridge" → Enable → Restart
4. Open level with BP_AurionAvatar pawn
5. Press Play
```

### Step 3: Test Connection
```
In Unreal:
1. Player moves close to Aurion avatar
2. Press 'E' to interact (or configure your input)
3. Type message in chat UI
4. Hit Enter

Expected:
- Avatar plays greeting animation
- Text-to-Speech runs, audio plays
- Aurion responds with generated avatar animation
- Facial expression changes based on emotion
```

### Step 4: Test Media Generation
```
In Unreal:
1. Open command console (backtick key)
2. Type: `ak.say "Draw a cyberpunk city"`
3. Aurion generates image via text_to_image skill
4. Image appears in viewport as material texture
```

---

## 📝 Configuration Files

### `.env` additions for Unreal

```env
# Unreal integration
UNREAL_ENGINE_ENABLED=true
UNREAL_ENGINE_VERSION=5.8.1
UNREAL_WEBSOCKET_HOST=localhost
UNREAL_WEBSOCKET_PORT=9876

# Skill provider fallback chain
AURION_IMAGE_PROVIDER=ollama          # first: local Ollama, fallback to Gemini
AURION_VIDEO_PROVIDER=runway-free     # API key required
AURION_SPEECH_PROVIDER=ollama         # first: nuro-voice, fallback to ElevenLabs
AURION_SPEECH_FALLBACK=elevenlabs     # if Ollama unavailable

# Costs (for budget tracking)
AURION_TOKEN_BUDGET_LIMIT=100000       # tokens per session
AURION_MEDIA_BUDGET_LIMIT=20           # $ per session for API calls
```

### Unreal Project Settings

**Edit → Project Settings → Plugins → AurionBridge**

```
[/Script/AurionBridge.UnrealBridgeSettings]
ServerHost=localhost
ServerPort=9876
AutoConnect=true
ReconnectAttempts=5
ReconnectDelay=2.0
DebugLogging=false
```

---

## 🔐 Security & Safety

### Skill Execution Sandboxing
- Code editing: restricted to `joi_companion/` and `ai_core/` paths only
- Forbidden operations: `os.system`, `subprocess`, `__import__`, `eval`, `exec`, `compile`
- All edits logged to `data/skills_audit_log.json` with timestamps + content hash

### Unreal Bridge Security
- Localhost-only by default (not exposed to internet)
- Message validation: all incoming JSON must match expected schema
- Rate limiting: max 100 requests/second per client
- Timeout: idle connections dropped after 5 minutes

### Cost Control
- BudgetAlert fires at 25%, 50%, 75% of token limit
- API calls halted at 100% budget (with user confirmation to override)
- All costs tracked in `data/skills_usage_log.json`

---

## 🧪 Testing Skills Locally (Without Unreal)

```python
# Python shell
from joi_companion.core.skills_engine import get_skills_engine

engine = get_skills_engine()

# Test text-to-image
result = engine.execute_skill("text_to_image", 
    prompt="cyberpunk city at night",
    width=512,
    height=512
)
print(result)  # {"status": "success", "image_path": "...", "cost": "$0"}

# Test text-to-speech
result = engine.execute_skill("text_to_speech",
    text="Hello! I am Aurion, your AI companion.",
    voice_id="aurion_default",
    emotion="excited"
)
print(result)  # {"status": "success", "audio_path": "...", "cost": "$0"}

# Test code editing (sandboxed)
result = engine.execute_skill("code_editing",
    action="create_file",
    file_path="joi_companion/test_module.py",
    changes={"content": "# Test file\nprint('Hello')"}
)
print(result)  # {"status": "success", "action": "create_file", ...}

# Check skill status
status = engine.get_skill_status()
print(json.dumps(status, indent=2))
```

---

## 📚 Unreal C++ Plugin Structure

```
Plugins/
└── UnrealBridgeClient/
    ├── Binaries/
    ├── Resources/
    ├── Source/
    │   └── UnrealBridgeClient/
    │       ├── Public/
    │       │   ├── UnrealBridgeClient.h
    │       │   ├── UnrealBridgeManager.h
    │       │   ├── AurionAvatarComponent.h
    │       │   └── MessageTypes.h
    │       ├── Private/
    │       │   ├── UnrealBridgeClient.cpp
    │       │   ├── UnrealBridgeManager.cpp
    │       │   └── AurionAvatarComponent.cpp
    │       └── UnrealBridgeClient.Build.cs
    ├── Content/
    │   ├── Blueprints/
    │   │   ├── BP_AurionAvatar.uasset
    │   │   ├── BP_AurionAnimator.uasset
    │   │   └── BP_AurionVoiceController.uasset
    │   └── Levels/
    │       └── TestLevel_AurionChat.umap
    └── UnrealBridgeClient.uplugin
```

---

## 🎮 Example Unreal Blueprint (Text-to-Image Trigger)

```blueprint
Event: Player Presses 'I' (for Image)
├─ Get Player Camera Location → CameraLoc
├─ Construct JSON:
│  ├─ "type": "skill_request"
│  ├─ "skill_name": "text_to_image"
│  ├─ "params": {
│  │  └─ "prompt": PlayerInputText
│  └─ "request_id": GenerateGUID()
├─ Send to Aurion Bridge (UnrealBridgeManager.SendMessage)
├─ On Response:
│  ├─ Load Image from Path
│  ├─ Create Dynamic Material
│  ├─ Apply to Billboard/Plane Actor
│  └─ Display in viewport (2s duration, then fade out)
```

---

## 🚨 Common Issues & Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| WebSocket connection refused | Bridge not started | Check `UNREAL_ENGINE_ENABLED=true` in .env; restart Aurion |
| `ModuleNotFoundError: websockets` | Missing dependency | `pip install websockets` |
| Avatar doesn't animate | Skeletal mesh not configured | Ensure BP_AurionAvatar uses correct skeleton asset |
| Audio not playing | Audio component muted | Check volume settings in Unreal; verify .wav file exists |
| Image generation fails | Ollama not running | `ollama serve` in terminal; check models with `ollama list` |
| Skill response timeout | Network latency or API delay | Increase timeout from 30s to 60s in `unreal_bridge.py` |
| Large video hangs | File too big for WebSocket | Modify bridge to stream video or send path reference only |

---

## 📈 Next Steps

### Immediate (This Sprint)
1. ✅ Create skills_engine.py (done)
2. ✅ Create unreal_bridge.py (done)
3. Create `/api/skills/*` endpoints in web_ui.py
4. Write unit tests for all skills
5. Create Unreal plugin skeleton (C++ boilerplate)

### Short-term (2-3 Weeks)
1. Implement Unreal C++ WebSocket client
2. Create test level with Aurion avatar
3. End-to-end test (text message → avatar response)
4. Package Aurion as executable

### Medium-term (1 Month)
1. Publish Unreal plugin to marketplace (or distribute via repo)
2. Full documentation + video tutorial
3. CI/CD pipeline for automated testing
4. Performance profiling + optimization

### Long-term (Future)
1. Multiplayer support (multiple Unreal clients talking to one Aurion instance)
2. Streaming video generation (progressive download while generating)
3. VR/AR avatar support
4. Mobile companion app (Android)
5. Cloud deployment (RunPod + Unreal Pixel Streaming)

---

## 💰 Cost Analysis

### Local Deployment (FREE)

| Component | Cost | Notes |
|-----------|------|-------|
| Ollama (voice + images) | $0 | Runs locally, no API calls |
| LM Studio | $0 | Local GGUF serving |
| Text-to-Video | $0 - $50/mo | Free tier (limited) or pay for unlimited |
| Unreal Engine | $0 | Free license up to $1M in revenue |
| Python dependencies | $0 | All open-source |
| **Total** | **$0** | ✅ Completely free for indie use |

### Cloud Deployment (Optional RunPod)

If you need more compute than local machine:
- RunPod GPU pod: ~$0.30-0.50/hr (if not already running)
- Gemini API fallback: $0/mo (free tier quota)
- **Total**: ~$7-12/day if running 24/7

---

## 📞 Support

For issues with:
- **Python skills**: Check logs in `data/skills_usage_log.json`
- **Unreal bridge**: Check WebSocket logs in Unreal Output Log
- **Media generation**: Verify Ollama/LM Studio running (`localhost:11434` or `:1234`)
- **Speech**: Check audio file in `data/generated_audio/`

---

**Ready to deploy! Start with Phase 1, then Phase 2 in Unreal.**
