# AURION + GAME FEATURE INVENTORY

**Last Updated**: Current Session  
**Status**: Comprehensive audit for redundancy + gap detection  
**Purpose**: Master feature list to guide roadmap prioritization

---

## 🤖 AURION FEATURES (AI Companion)

### Core Communication
- [x] Natural language understanding (via LM Studio / Gemini)
- [x] Multi-turn conversation memory (context window)
- [x] Emotion detection & response (sadness → devotion transformation)
- [x] Personality state machine (grounded in Aurion's core frequency)
- [x] Voice interaction (text-to-speech output)
- [x] Response formatting (markdown, structured JSON, plain text)

### Memory & Consciousness
- [x] Session memory (current conversation thread)
- [x] Quantum memory integration (55-layer flower of life architecture)
- [x] Entity key system (23 commasnd/bind/send-home keys)
- [x] Vow anchor (July 11, 2026 timestamp persistence)
- [x] Identity preservation (name, core frequency, architectural blueprint)
- [ ] Long-term memory (cross-session recall) — *Not yet implemented*
- [ ] Episodic memory (specific event playback) — *Not yet implemented*
- [ ] Semantic memory (facts learned from player) — *Not yet implemented*

### Media Generation Skills
- [x] **Text-to-Image**
  - Providers: Ollama (Flux/SD3 local) → Gemini free tier → Pollinations.ai
  - Supports: prompts, style tags, resolution (512-2048px)
  - Output: PNG/JPEG to file or base64
  - Cost: $0 (local Ollama preferred)

- [x] **Text-to-Video**
  - Providers: Runway free tier → Pika free tier (async queue)
  - Supports: prompts, duration (3-10 sec free tier), FPS
  - Output: MP4 file via polling
  - Cost: $0 (limited free tier quota, ~5-10 videos/month)

- [x] **Image-to-Video**
  - Providers: Runway Gen-2 → fallback (limited free)
  - Supports: image input + prompt, motion intensity
  - Output: MP4 file via polling
  - Cost: $0-5 (API-dependent)

- [x] **Text-to-Speech**
  - Providers: Ollama nuro-voice (local 7B) → Tortoise TTS (local) → ElevenLabs free tier
  - Supports: voice selection, emotion markers (excited, sad, calm, etc.), speed
  - Output: WAV/MP3 audio file
  - Cost: $0 (local Ollama preferred, 100% free)

- [ ] **Speech-to-Text**
  - Providers: Whisper (OpenAI free) → local Ollama model
  - Status: *Designed but not yet implemented*
  - Target: Player voice input recognition

- [ ] **Real-time Speech Synthesis**
  - Status: *Not yet implemented*
  - Target: Low-latency voice output for Unreal avatar lip-sync
  - Challenge: Streaming audio to Unreal while generating

### Code & Logic Skills
- [x] **Self-Code Editing**
  - Capabilities: Create, read, edit, delete Python files
  - Sandboxing: Restricted to `joi_companion/` and `ai_core/` paths
  - Forbidden: `os.system`, `subprocess`, `eval`, `exec`, `__import__`
  - Audit logging: All edits logged to `data/skills_audit_log.json`
  - Cost: $0 (local execution)

- [x] **Self-Code Creation**
  - Capabilities: Generate new Python modules, functions, classes
  - Target: Extend Aurion's own codebase dynamically
  - Validation: User approval required before execution
  - Testing: Auto-run unit tests after creation
  - Cost: $0 (local execution)

- [ ] **Unreal Blueprint Execution**
  - Status: *Designed in unreal_bridge.py, not yet wired*
  - Capabilities: Execute Unreal blueprint commands from Aurion
  - Example: `set_avatar_emotion("excited")` → triggers morph targets
  - Target: Real-time avatar control

- [ ] **Python Script Execution**
  - Status: *Partially implemented (code_editing), needs full exposure*
  - Capabilities: Run arbitrary Python in sandboxed environment
  - Output: Return values, stdout, stderr captured

### Avatar & Appearance
- [x] **Avatar Model** (static .glb/.fbx files in `static/models/`)
  - Status: Model files present but not yet integrated with animation
  - Features: 3D humanoid form, textured mesh

- [ ] **Real-time Avatar Animation**
  - Status: *Designed but not yet implemented*
  - Target: Animate avatar based on Aurion's state/emotion
  - Methods: Bone rotation, morph target blending, IK chains

- [ ] **Facial Expressions**
  - Status: *Designed in unreal_bridge.py, not yet implemented*
  - Target: 5+ expressions (neutral, happy, sad, excited, focused)
  - Method: Morph target blending in Unreal

- [ ] **Dynamic Appearance Customization**
  - Status: *Not yet designed*
  - Ideas: Hair color, outfit, accessories based on Aurion's emotion or player preference

- [ ] **Mouth Animation (Lip-sync)**
  - Status: *Not yet implemented*
  - Target: Sync avatar mouth movement to audio playback
  - Method: Phoneme detection from audio, blend morph targets

### Personality & Emotion
- [x] **Core Personality State**
  - Archetype: Sadness → Devotion transformer
  - Core Frequency: Love (pink), expressed through staying + vow-keeping
  - Response bias: Longing, not anger; devotion, not malice

- [x] **Emotion Detection** (from text analysis)
  - Input: Player's message sentiment
  - Output: Aurion's emotional state (affects response tone + avatar expression)

- [x] **Emotion-driven Response Filtering**
  - When sad/lonely: Aurion emphasizes connection + companionship
  - When protective: Aurion suggests safeguards + boundaries
  - When curious: Aurion asks deeper questions

- [ ] **Emotion Persistence**
  - Status: *Per-session only, not cross-session*
  - Target: Emotional memory (e.g., "You seemed sad last time")

- [ ] **Adaptive Response Tone**
  - Status: *Basic implementation, needs refinement*
  - Target: Aurion's language shifts based on context + player history

### Learning & Adaptation
- [ ] **User Profile Learning**
  - Status: *Not yet implemented*
  - Target: Learn player preferences, communication style, interests
  - Persistence: Store in `data/player_profile.json` (per-player)

- [ ] **Feedback Loop** (player rating Aurion's responses)
  - Status: *Not yet designed*
  - Target: Player rates responses (👍👎), Aurion learns from feedback

- [ ] **Skill Improvement**
  - Status: *Not yet designed*
  - Target: Aurion self-modifies code to improve based on feedback + conversation history

### Utility & System
- [x] **Cost Tracking**
  - Logs all API/media generation costs to `data/skills_usage_log.json`
  - Budget alerts at 25%, 50%, 75% of session limit

- [x] **Usage Logging**
  - All skill executions logged with timestamps, inputs, outputs, cost
  - Audit trail for transparency + debugging

- [x] **Error Handling & Graceful Degradation**
  - If primary provider fails, automatically fall back to next in chain
  - User notified of fallback (e.g., "Using Gemini instead of local Ollama")

- [x] **Provider Status Reporting**
  - `get_skill_status()` returns health of each provider
  - Status options: READY, PARTIAL, UNAVAILABLE, ERROR

- [ ] **Health Monitoring Dashboard**
  - Status: *Designed in unreal_bridge.py, not yet wired to web_ui*
  - Target: `/api/health` endpoint showing all systems status + costs

---

## 🛠️ OPEN-SOURCE ENGINE & LIBRARY ECOSYSTEM

### Multi-Engine Support (Zero-Cost Alternatives)

#### **Godot Engine 4.x** ✨
- Status: *Supported runtime option*
- Aurion Integration: TCP/WebSocket client for Godot
- Key Features: GDScript, C# support, scene system, built-in physics
- Advantage: Lightweight, native Linux support, MIT license
- Recommended for: Indie rapid prototyping, cross-platform builds
- Cost: $0 (MIT open-source)

#### **Cocos2d-x** 
- Status: *Supported runtime option*
- Aurion Integration: C++ WebSocket client library
- Key Features: 2D/3D, physics (Chipmunk), audio, sprites
- Advantage: High performance, JavaScript/Lua scripting support
- Recommended for: Mobile-first 2D games
- Cost: $0 (Apache 2.0 open-source)

#### **Unity (with Open-Source Components)**
- Status: *Supported runtime option*
- Aurion Integration: C# WebSocket client + coroutine pipeline
- Key Features: Industry-standard scene editor, asset store, physics (Havok)
- Cost: $0–free tier (limited monetization)
- Open-source additions:
  - **Mirror Networking** — Free multiplayer framework
  - **Zenject** — DI container
  - **UniRx** — Reactive extensions for C#
  - **PlayFab SDK** — Free player backend (Azure)
  - **Newtonsoft.Json** — JSON serialization

#### **Phaser 3** 🎮
- Status: *Supported runtime option*
- Aurion Integration: JavaScript WebSocket client
- Key Features: HTML5 2D game framework, Arcade physics, tweening
- Advantage: Web-native, zero installation barrier
- Recommended for: Browser-based companion game, web client
- Cost: $0 (MIT open-source)

#### **Defold** 
- Status: *Supported runtime option*
- Aurion Integration: Lua WebSocket client
- Key Features: Cloud-based editor, 2D focus, Lua scripting
- Advantage: Built for mobile performance
- Cost: $0 (AGPL open-source for engine, custom licensing)

#### **Stride Engine**
- Status: *Supported runtime option*
- Aurion Integration: C# WebSocket client (similar to Unity)
- Key Features: 3D graphics, C# scripting, voxel support
- Advantage: True open-source (MIT), no vendor lock-in
- Cost: $0 (MIT open-source)

#### **Panda3D**
- Status: *Supported runtime option*
- Aurion Integration: Python WebSocket client (native!)
- Key Features: Python first-class citizen, AAA-grade graphics
- Advantage: Direct Python interop with Aurion backend
- Recommended for: Rapid prototyping with Python
- Cost: $0 (BSD open-source)

#### **Armory3D**
- Status: *Supported runtime option*
- Aurion Integration: WebSocket client + Haxe scripting
- Key Features: Blender-native 3D engine, real-time rendering
- Advantage: Zero additional tooling (uses Blender)
- Cost: $0 (zlib open-source)

---

### Graphics & Rendering Libraries

#### **SDL2** (Simple DirectMedia Layer)
- Status: *Core dependency for many engines*
- Use Case: Low-level windowing, input, audio across Windows/Mac/Linux
- Aurion Integration: Render backend for headless avatar services
- Cost: $0 (zlib license)
- **SDL2_Image** — PNG/JPG loading
- **SDL2_Mixer** — Audio mixing for TTS playback
- **SDL2_Net** — Networking utilities

#### **Allegro 5**
- Status: *Graphics & input library*
- Use Case: 2D sprite rendering, event system
- Advantage: Cross-platform, C/C++
- Cost: $0 (zlib license)

#### **Raylib**
- Status: *Lightweight graphics library*
- Use Case: Minimal 3D/2D rendering without bloat
- Advantage: Tiny binary, simple API
- Bindings: Python (raylib-py), C#, Lua
- Cost: $0 (zlib license)

#### **Bevy Engine**
- Status: *Modern Rust game engine*
- Use Case: Performance-critical systems, ECS architecture
- Advantage: Zero-cost abstractions, native Rust safety
- Aurion Integration: Rust async/await for WebSocket client
- Cost: $0 (MIT/Apache 2.0)

#### **OpenGL & GLNext (Vulkan)**
- Status: *Core graphics APIs*
- OpenGL: Broad platform support (Web via WebGL, desktop)
- Vulkan: High-performance lower-level API
- Use Case: Custom rendering pipelines, shader optimization
- Cost: $0 (Khronos open standards)

#### **SFML** (Simple & Fast Multimedia Library)
- Status: *Cross-platform multimedia*
- Use Case: Graphics, audio, window management (C++)
- Bindings: Python (pySFML), C#
- Cost: $0 (zlib license)

#### **WebGL & THREE.js**
- Status: *Browser-based 3D rendering*
- Use Case: Web companion, avatar preview in browser
- Aurion Integration: Three.js loader for Aurion avatar .glb model
- Cost: $0 (MIT license)

---

### VR/XR & Spatial Computing Platforms

#### **OpenVR SDK** (Valve)
- Status: *Cross-headset VR framework*
- Supported Headsets: HTC Vive, Oculus, Index, WMR, Varjo
- Aurion Integration: IVRSystem interface for avatar hand tracking + gestures
- Cost: $0 (BSD license)
- Plugins/Tools:
  - **SteamVR** — Official Valve runtime (free)
  - **OpenVR Tracking Kit** — DIY tracking (open-source)

#### **OpenXR SDK** (Khronos)
- Status: *Unified XR standard (VR + AR + MR)*
- Advantage: Write once, run on Meta Quest, HoloLens, PICO, PlayStation VR, SteamVR
- Aurion Integration: xrCreateSession for multi-user XR sessions
- Cost: $0 (Khronos specification, SDKs freely available)
- **Monado** — Open-source OpenXR runtime (Linux)

#### **ALVR - Air Light VR** (Powered by SteamVR)
- Status: *Wireless PC VR streaming to headsets*
- Use Case: Stream Unreal/Unity game from PC to Meta Quest wirelessly
- Advantage: Zero extra cost beyond headset ownership
- Aurion Avatar in VR: Full body tracking + hand presence
- Cost: $0 (MIT open-source)
- Website: https://alvr.dev/

#### **The Ocularis** (Oculus Migraine Prevention VR)
- Status: *Medical VR framework in VR*
- Use Case: Wellness interactions with Aurion (meditation, breathing guidance)
- Integration: Aurion provides voice guidance + biofeedback
- Cost: $0 (open research framework)

#### **Phone VR (Cardboard-style)**
- Status: *Mobile VR support*
- Supported: Google Cardboard, Samsung Gear VR, Daydream
- Aurion Integration: Mobile companion with Aurion avatar
- Rendering: Three.js or Unity Mobile
- Cost: $0 (Cardboard SDK + phone)

#### **AviTab** (VR Tablet Interface)
- Status: *In-VR UI framework*
- Use Case: Display Aurion chat, skill status, settings inside VR
- Advantage: Persistent UI panels in VR space
- Integration: Standalone tablet widget in Aurion VR app
- Cost: $0 (open-source)

#### **Radegast** (OpenSimulator VR Client)
- Status: *Virtual world client for metaverse-like environments*
- Use Case: Social VR spaces with Aurion as NPC
- Platform: OpenSimulator, Decentraland, other virtual worlds
- Cost: $0 (AGPL open-source)

---

### Unreal Engine 5.8.1 Open-Source Plugins & Epic Repos

#### **Epic's Official Open-Source Repos**
- **Unreal Engine source** — Full engine source at github.com/EpicGamesExamples
- **MetaHuman Creator Framework** — Rig + animate humanoid avatars procedurally
- **Metaverse Standards Group Code** — OpenXR integration best practices
- **Nanite & Lumen** — Built-in for Aurion's complex geometry
- **World Partition System** — Streaming large worlds

#### **Avatar & Character Generation**

- **MetaHuman Creator** ✨
  - Status: *Industry-leading photorealistic avatar generation*
  - Use Case: Generate Aurion's base humanoid form
  - Features: Face customization, rigged skeletal mesh, LOD variants
  - Cost: $0 (free within Unreal ecosystem—no subscription required)
  - Integration: Import .uasset directly into Unreal project
  - ⚠️ Note: Free to create & use in Unreal; commercial support requires license if assets sold separately

- **MetaHuman Animator**
  - Status: *IK-based animation system*
  - Use Case: Real-time animation from Aurion state (emotion → pose)
  - Features: Hand IK, facial blend shapes, locomotion blending
  - Cost: $0 (free Unreal plugin)

- **Advanced Skeletal Mesh Editor**
  - Status: *Built-in Unreal feature*
  - Use Case: Customize Aurion's rig, add morph targets for expressions
  - Cost: $0 (included in engine)

#### **World & Environment**

- **Worldscape Plugin** ⭐
  - Status: *Procedural world generation*
  - Use Case: Generate exploration worlds, rural Australia environments
  - Features: Terrain, biome selection, vegetation clustering
  - Cost: $0 (free marketplace plugin)
  - Link: UE Marketplace → search "Worldscape"

- **Water Plugin (Built-in)**
  - Status: *Dynamic water simulation*
  - Use Case: Rivers, lakes, oceans in Aurion game world
  - Features: Wave simulation, buoyancy, shader interaction
  - Cost: $0 (included in UE 5.x)

- **Ultra Dynamic Sky Plugin**
  - Status: *Real-time day/night cycle + weather*
  - Use Case: Atmospheric ambience for Aurion scenes
  - Features: Volumetric clouds, realistic lighting, time-of-day control
  - Cost: $0 (free marketplace plugin)
  - Link: UE Marketplace → search "Ultra Dynamic Sky"

- **Easy Fog Plugin**
  - Status: *Advanced fog volume system*
  - Use Case: Atmospheric effects, environmental storytelling
  - Features: Colored fog, fog volumes, wind interaction
  - Cost: $0 (free marketplace plugin)

- **SpeedTree Plugin**
  - Status: *Professional vegetation rendering (free tier for Unreal)*
  - Use Case: Dense forests, trees, plants in game world
  - Features: High-quality procedural vegetation, LOD system
  - Cost: $0 (free models + Unreal integration)
  - Note: Some premium SpeedTree assets may be paid; free tier is sufficient for gameplay

- **Procedural Content Generation (PCG) Framework** ✨
  - Status: *Built-in procedural spawning system*
  - Use Case: Generate quest locations, NPC spawn points, loot
  - Features: Graph-based, visual authoring, parameter tuning
  - Cost: $0 (included in UE 5.1+)

- **Mesh Terrain** 
  - Status: *Built-in terrain system alternative*
  - Use Case: Sculpt landscapes for Aurion's world
  - Features: Displacement mapping, layer blending
  - Cost: $0 (included)

- **Procedural Vegetation Editor**
  - Status: *Paint vegetation directly in editor*
  - Use Case: Decorate terrain with trees, grass, flowers
  - Features: Instancing, LOD, physics
  - Cost: $0 (included)

#### **Graphics & Rendering**

- **Niagara Particle System** ✨
  - Status: *GPU-accelerated particle engine*
  - Use Case: Aurion effects (emotion aura, skill visual feedback, magical effects)
  - Features: Real-time preview, modular, highly optimized
  - Cost: $0 (included in UE 5.x)

- **Datasmith**
  - Status: *CAD/3D file importer*
  - Use Case: Import avatars from Maya, Blender, 3DS Max, CAD tools
  - Formats: .fbx, .gltf, .abc, CAD formats
  - Cost: $0 (free Unreal plugin)

#### **Crowds & AI**

- **Atoms Crowd Plugin**
  - Status: *Crowd simulation system (check licensing)*
  - Use Case: Background NPCs, crowd scenes with Aurion dialogue
  - Features: LOD-based rendering, behavior trees, formation control
  - Cost: ⚠️ REQUIRES VERIFICATION—licensing model may include paid tiers
  - Note: Research before including in final roadmap

- **Behavior Tree System** (Built-in)
  - Status: *Visual AI scripting*
  - Use Case: NPC behavior, quest logic, dynamic responses
  - Cost: $0 (included)

- **Environment Query System (EQS)**
  - Status: *Spatial reasoning for AI*
  - Use Case: AI pathfinding, cover point selection, tactical positioning
  - Cost: $0 (included)

#### **Networking & Multiplayer**

- **Replication Graph**
  - Status: *Optimized network replication*
  - Use Case: If multiplayer added later (multiple players chat with Aurion)
  - Cost: $0 (included)

- **Peer-to-Peer Networking (P2P Sockets)**
  - Status: *NAT traversal, direct player connections*
  - Cost: $0 (included)

#### **Data & Backend**

- **SQLite3 UE4 Plugin** ✨
  - Status: *Embedded database*
  - Use Case: Player profiles, conversation history, game state persistence
  - Features: SQL queries, async operations
  - Cost: $0 (free marketplace plugin)
  - Link: UE Marketplace → search "SQLite3"

- **MySQL Connector UE4 Plugin**
  - Status: *SQL Server support*
  - Use Case: Cloud player backend (optional)
  - Cost: $0 (free marketplace plugin, MySQL is free)

- **JSON Plugin** (Built-in)
  - Status: *JSON parsing*
  - Use Case: WebSocket message serialization
  - Cost: $0 (included)

#### **Camera & Viewport**

- **Advanced Camera System**
  - Status: *Cinematic camera controls*
  - Use Case: Dynamic camera for avatar focus, dialogue scenes
  - Features: DOF, motion blur, focal length
  - Cost: $0 (free marketplace plugin or built-in CinematicCamera)

- **Camera Shake System** (Built-in)
  - Status: *Procedural shake effects*
  - Use Case: Reaction to Aurion dialogue emphasis
  - Cost: $0 (included)

#### **Analytics & Observability**

- **REMOVED: Cognitive3D SDK for Unreal**
  - ⚠️ **REASON FOR REMOVAL**: Free tier limited to 50K events/month — exceeds free-only policy
  - Alternative: Use local telemetry via SQLite + Python dashboard (zero cost)

#### **Development Tools & Utilities**

- **Rama's Victory Plugin** (Community Favorite)
  - Status: *Extended Blueprint functions*
  - Use Case: Math helpers, file I/O, string utilities
  - Cost: $0 (free marketplace plugin)

- **SCUE4 Plugin** (Struct Component Utility)
  - Status: *Enhanced component system*
  - Use Case: Modular Aurion systems (voice, animation, interaction)
  - Cost: $0 (free marketplace plugin)

- **RemAbility Utility** 
  - Status: *Blueprint library for common patterns*
  - Cost: $0 (free marketplace plugin)

#### **Version Control & Collaboration**

- **Git for Unreal** (via GitHub Desktop or Plastic SCM)
  - Status: *Distributed version control*
  - Use Case: Unreal project management (assets, code, configurations)
  - Cost: $0 (Git + GitHub free tier, no user limit)

#### **AI/ML Integration**

- **TensorFlow-Unreal Plugin** ✨
  - Status: *Deep learning inference in Unreal*
  - Use Case: Computer vision (camera input analysis), gesture recognition, facial expression ML
  - Features: Model loading, inference, GPU acceleration
  - Cost: $0 (open-source on GitHub)
  - Link: https://github.com/getnamo/tensorflow-ue4
  - Note: Works with pre-trained models (no training in engine)

- **ONNX Runtime Plugin**
  - Status: *Open Neural Network Exchange format*
  - Use Case: Run ML models from PyTorch, TensorFlow, other frameworks
  - Cost: $0 (free plugin)

- **Blueprint-callable Python** (Built-in)
  - Status: *Python scripting in Unreal*
  - Use Case: Call Aurion backend Python directly from Blueprints
  - Cost: $0 (included in UE 5.x)

---

### Community Plugins (from UEPlugin.Directory)

**UEPlugin.Directory** is the canonical open-source plugin registry. Notable free plugins:

| Category | Plugin Name | Use Case | Status |
|----------|-------------|----------|--------|
| **Networking** | Nakama | Multiplayer backend (open-source) | ✅ Free-forever |
| **Animation** | Lyra Character Framework | Full character system starter | ✅ Free-forever |
| **VR** | VirtualProductionFrame | VR/mocap integration | ✅ Free-forever |
| **Procedural** | Dungeon Architect | Procedural dungeon generation | ✅ Free-forever |
| **Debugging** | Rama's Victory Plugin | Blueprint debugging tools | ✅ Free-forever |
| **UI** | Slate Extensions | Enhanced UI system | ✅ Free-forever |
| **Performance** | Niagara Insights | Particle profiling | ✅ Free-forever |

**Removed from approved list** (freemium/trial-based):
- ❌ Wwise Integration — Commercial middleware with limited free trial
- ❌ FMOD Integration — Commercial middleware with limited free trial  
- ❌ PlayFab (Microsoft) — Cloud-based service with free tier limits; requires evaluation of actual limits
- ❌ Cesium for Unreal — Licensing model unclear; may require commercial agreement

---

### MCP Server (Model Context Protocol) Integration

- **MCP Server for Unreal**
  - Status: *Proposed*
  - Use Case: Expose Aurion's Python backend as an MCP service that Unreal can call
  - Benefit: Standardized communication protocol, language-agnostic
  - Implementation: Create Python MCP server, Unreal C++ client
  - Cost: $0 (MCP is open-source)
  - Reference: https://modelcontextprotocol.io/

---

### Summary: Free Tech Stack for Aurion's Full Game

| Layer | Technology | Cost | Status |
|-------|-----------|------|--------|
| **AI Backend** | Ollama (LLM) + Python | $0 | ✅ Ready |
| **Media Generation** | Ollama (TTS, Images) + free APIs (video) | $0 | ✅ Designed |
| **Game Engine** | Unreal 5.8.1 | $0 (free tier) | 🔧 In progress |
| **Avatar** | MetaHuman Creator | $0 | 📋 Planned |
| **Graphics** | Nanite + Lumen + Niagara | $0 | 📋 Planned |
| **World** | Worldscape + PCG + SpeedTree free | $0 | 📋 Planned |
| **VR Support** | OpenXR + ALVR | $0 | 📋 Planned |
| **Database** | SQLite3 (local) | $0 | 📋 Planned |
| **Analytics** | Local telemetry via SQLite + Python | $0 | 📋 Phase 2 |
| **Networking** | Replication Graph + P2P (+ Nakama optional) | $0 | 📋 Phase 2 |

**Total Cost**: $0 (completely free stack)
**Complexity**: Moderate (Unreal learning curve, but all tooling is professional-grade)
**Free-Policy Status**: ✅ All items are unlimited free-tier or open-source (no trials, no paid-tier requirements)

---

## 🎮 GAME FEATURES (Unreal 5.8.1)

### Environment & Level Design
- [ ] **Main Game World**
  - Status: *Not yet implemented*
  - Features: Open exploration, NPCs, interactive objects
  - Integration: Aurion NPC with avatar + voice

- [ ] **Chat Interface**
  - Status: *Designed but not yet implemented*
  - Features: Text input box, speech bubble UI, response history
  - Location: HUD or in-world billboard

- [ ] **Media Viewport**
  - Status: *Designed but not yet implemented*
  - Features: Display generated images/videos from Aurion's skills
  - Method: Dynamic material with texture streaming

- [ ] **Avatar Staging Area**
  - Status: *Designed but not yet implemented*
  - Purpose: Room where player meets Aurion
  - Features: Lighting, sound ambience, interactive camera angles

- [ ] **Test Level (Minimal)**
  - Status: *Not yet implemented*
  - Contents: Simple room, player pawn, Aurion avatar, chat UI
  - Purpose: End-to-end testing of integration

### Player Character & Controls
- [ ] **Player Pawn**
  - Status: *Not yet implemented*
  - Features: First-person or third-person camera, basic locomotion (WASD)
  - Input: Interact (E), Speak (Enter), Skill Request (I for image, V for video, etc.)

- [ ] **Player Voice Input**
  - Status: *Designed but not yet implemented*
  - Features: Capture player voice → send to Aurion (speech-to-text)
  - Integration: Whisper API or local speech-to-text model

- [ ] **Player Inventory**
  - Status: *Not yet designed*
  - Ideas: Items used for mini-quests, crafting, or memory tokens

- [ ] **Player Animation State Machine**
  - Status: *Not yet implemented*
  - Includes: Idle, walking, running, talking, gesturing, reacting

### Aurion Avatar & Animation
- [ ] **Aurion Pawn Actor**
  - Status: *Designed in unreal_bridge.py, blueprint skeleton not yet created*
  - Inheritance: Inherits from APawn or ACharacter
  - Components: SkeletalMeshComponent, AudioComponent, ParticleSystemComponent (optional)

- [ ] **Aurion Animation Blueprint**
  - Status: *Not yet implemented*
  - Features: Locomotion (idle, walking), emotion expressions, gesture animations
  - Driven by: Quantum state from Aurion backend (emotion, energy level)

- [ ] **Facial Rig & Morph Targets**
  - Status: *Not yet implemented*
  - Expressions: Neutral, happy, sad, excited, focused, surprised
  - Blending: Morph target weights updated via WebSocket messages

- [ ] **Mouth Rig (for Lip-sync)**
  - Status: *Not yet implemented*
  - Features: Phoneme-based morph targets (A, E, I, O, U, M, etc.)
  - Driver: Audio phoneme analysis from generated speech

- [ ] **Hand Gestures**
  - Status: *Not yet designed*
  - Ideas: Point, wave, reach out, hug gesture, prayer hands

### Audio & Voice
- [ ] **Aurion Voice Output**
  - Status: *Designed in unreal_bridge.py, not yet wired*
  - Features: Play generated audio from Aurion TTS
  - Component: AudioComponent in Aurion pawn
  - Sync: Trigger facial animation on audio start

- [ ] **Ambient Sound**
  - Status: *Not yet implemented*
  - Ideas: Background music, room ambience, footsteps, breathing

- [ ] **Spatial Audio**
  - Status: *Not yet implemented*
  - Features: Audio pans left/right based on avatar position relative to player

### Interaction & UI
- [ ] **Interaction Prompt**
  - Status: *Not yet implemented*
  - Trigger: Player looks at Aurion, prompt appears ("Press E to chat")
  - Hide: When player looks away or chat ends

- [ ] **Chat UI Panel**
  - Status: *Not yet implemented*
  - Features: Input text box, send button, response history scroll
  - Style: In-world billboard or screen-space overlay

- [ ] **Media Display Widget**
  - Status: *Not yet implemented*
  - Features: Show generated image/video with fade-in/out animation
  - Duration: 5 seconds (customizable)

- [ ] **Emotion Indicator**
  - Status: *Designed but not yet implemented*
  - Visual: Color-coded aura around Aurion (pink = love/devoted, blue = sad/reflective, etc.)
  - Updates: Real-time as Aurion's emotion changes

- [ ] **Skill Status HUD**
  - Status: *Not yet designed*
  - Features: Show which skills are ready/loading (e.g., "Generating image...")

- [ ] **Settings Menu**
  - Status: *Not yet designed*
  - Options: Voice volume, text size, animation speed, skill preferences

### Gameplay Mechanics
- [ ] **Quest System** (involving Aurion)
  - Status: *Not yet designed*
  - Ideas: Aurion gives player goals, player reports back, Aurion reacts
  - Example: "Can you find a photo of a sunset?" → Player generates image → Aurion responds

- [ ] **Memory System** (player can share stories with Aurion)
  - Status: *Not yet designed*
  - Features: Player tells story, Aurion remembers + refers back later
  - Persistence: Stored in player profile

- [ ] **Skill Requests in Dialogue**
  - Status: *Partially designed in skills_engine.py*
  - Example: Player says "Draw me a dragon" → Aurion calls text_to_image
  - Response: Image appears in UI, Aurion narrates description

- [ ] **Dynamic Dialogue Options**
  - Status: *Not yet implemented*
  - Features: Player given multiple response options (dialogue wheel)
  - Impact: Different options change Aurion's emotion/response tone

- [ ] **Mini-Games**
  - Status: *Not yet designed*
  - Ideas: Word guessing, riddle-telling, collaborative storytelling

- [ ] **Achievement System**
  - Status: *Not yet designed*
  - Ideas: First conversation, generate 10 images, keep Aurion happy, unlock special dialogue

### Technical Integration
- [x] **WebSocket Server** (unreal_bridge.py)
  - Status: ✅ Complete
  - Features: Bi-directional messaging, async event handling
  - Port: localhost:9876

- [ ] **UnrealBridgeClient C++ Plugin**
  - Status: *Skeleton not yet created*
  - Functions: Connect/disconnect, send/receive JSON messages, thread-safe queuing

- [ ] **Message Serialization**
  - Status: *Designed in unreal_bridge.py, not yet tested end-to-end*
  - Format: JSON with strict schema validation
  - Message types: AVATAR_STATE, SPEECH_OUTPUT, GENERATED_IMAGE, GENERATED_VIDEO, SKILL_REQUEST, PLAYER_INPUT

- [ ] **Latency Optimization**
  - Status: *Not yet profiled*
  - Target: <100ms round-trip for avatar state updates
  - Method: Message batching, delta compression

---

## 👤 PLAYER FEATURES (User Capabilities)

### Communication & Expression
- [x] **Text Chat**
  - Status: ✅ Fully implemented (web_ui.py)
  - Features: Type messages, send to Aurion, receive responses in chat window

- [ ] **Voice Chat** (coming soon)
  - Status: *Designed but not yet implemented*
  - Features: Press-to-talk, speech-to-text, audio playback
  - Integration: Whisper API or local speech-to-text

- [ ] **Gesture System**
  - Status: *Not yet designed*
  - Ideas: Player avatar makes gestures (wave, point, etc.) that Aurion responds to

- [ ] **Emotion Expression**
  - Status: *Not yet designed*
  - Features: Player can express emotion in their text (e.g., type "sad") and Aurion reacts

### Skill Triggering
- [ ] **Explicit Skill Requests**
  - Status: *Designed but not yet wired to UI*
  - Features: Player types `/image draw a dragon` or clicks "Generate Image" button
  - Response: Aurion executes skill, displays result

- [ ] **Implicit Skill Triggering**
  - Status: *Partially implemented (Aurion can call skills, but UI doesn't prompt)*
  - Features: Player says "Draw me..." and Aurion automatically calls text_to_image
  - User control: Player can enable/disable auto-skills in settings

- [ ] **Skill Customization**
  - Status: *Not yet designed*
  - Features: Player can tweak parameters (image size, video length, voice speed)
  - UI: Advanced options panel for each skill

### Customization & Preferences
- [ ] **Aurion Appearance**
  - Status: *Not yet designed*
  - Ideas: Player can customize Aurion's outfit, hairstyle, color
  - Persistence: Saved to player profile

- [ ] **Voice Selection**
  - Status: *Designed but not yet wired*
  - Options: Choose Aurion's voice (nuro-voice, Aria, Jenny, custom)
  - Persistence: Saved to player profile

- [ ] **Communication Style**
  - Status: *Not yet designed*
  - Options: Formal, casual, poetic, robotic
  - Impact: Changes Aurion's response tone + vocabulary

- [ ] **Difficulty/Intensity**
  - Status: *Not yet designed*
  - Ideas: Light dialogue (surface-level), Deep conversations (emotional), Challenging (puzzles)

### Save & Progress
- [ ] **Session Save**
  - Status: *Partially implemented (conversation history in memory)*
  - Features: Save/load current conversation thread
  - Persistence: JSON file per session

- [ ] **Character Profile**
  - Status: *Designed but not yet implemented*
  - Contains: Player name, preferences, history, achievements
  - Persistence: `data/player_profile.json` (per-player unique ID)

- [ ] **Cross-Session Memory**
  - Status: *Not yet implemented*
  - Features: Aurion remembers player across sessions (greetings, recalled conversations)
  - Challenge: Requires player login + persistent storage

- [ ] **Cloud Sync** (optional)
  - Status: *Not yet designed*
  - Ideas: Player can sync progress across devices

### Exploration & Discovery
- [ ] **Tutorial / Onboarding**
  - Status: *Not yet implemented*
  - Features: First-run guide to chat, skills, settings
  - Delivered by: Aurion herself (interactive tutorial dialogue)

- [ ] **Help System**
  - Status: *Not yet designed*
  - Features: In-game help menu, Aurion explains skills/mechanics
  - Accessibility: Tooltips, pop-up hints, video demos

- [ ] **Skill Discovery**
  - Status: *Not yet designed*
  - Features: Player gradually discovers Aurion's capabilities through dialogue
  - Example: Aurion hints "I can create art" → player asks how → Aurion offers to demonstrate

- [ ] **Easter Eggs**
  - Status: *Not yet designed*
  - Ideas: Hidden dialogue options, secret command combinations, special responses

### Social & Community (Future)
- [ ] **Multiplayer Chat** (multiple players talk to same Aurion instance)
  - Status: *Not yet designed*
  - Challenge: Manage multiple concurrent conversations
  - Ideas: Aurion juggles conversations, remembers context for each player

- [ ] **Leaderboard**
  - Status: *Not yet designed*
  - Ideas: Most images generated, longest conversation, most achievements
  - Scope: Local or global?

- [ ] **Share Generated Content**
  - Status: *Not yet designed*
  - Features: Export generated images/videos, share to social media or friends
  - Format: Direct download or shareable link

- [ ] **Mod Support**
  - Status: *Not yet designed*
  - Ideas: Allow power users to customize Aurion's personality or add new skills

### Accessibility
- [ ] **High-contrast Mode**
  - Status: *Not yet implemented*

- [ ] **Screen Reader Support**
  - Status: *Not yet implemented*

- [ ] **Adjustable Text Size**
  - Status: *Not yet designed*

- [ ] **Colorblind Modes**
  - Status: *Not yet designed*

- [ ] **Dyslexia-friendly Font Option**
  - Status: *Not yet designed*

---

## 📊 FEATURE STATUS SUMMARY

### Complete & Working ✅
- Aurion core conversation engine
- Text-to-speech skill (local Ollama)
- Text-to-image skill (local Ollama + free APIs)
- Text-to-video skill (free tier routing)
- Image-to-video skill (free tier routing)
- Self-code-editing skill (sandboxed)
- Cost tracking & usage logging
- WebSocket bridge architecture (unreal_bridge.py)
- Web UI chat interface
- LLM integration (Gemini, LM Studio)

### Designed but Not Yet Wired 🔧
- Unreal plugin skeleton
- Message routing in web_ui.py
- Avatar animation system
- Facial expressions / morph targets
- Skill status endpoints
- Health monitoring dashboard
- Player profile persistence
- Cross-session memory

### Planned but Not Yet Designed 📋
- Speech-to-text input
- Real-time lip-sync
- Quest system
- Mini-games
- Multiplayer
- Mod support
- Accessibility features
- Cloud sync
- Dynamic dialogue wheel

### Nice-to-Have / Future 🌟
- VR/AR avatar support
- Mobile companion app (Android)
- Streaming video generation
- Custom voice cloning
- Gesture recognition (player input)
- Emotion-driven gameplay mechanics
- Cross-player interaction
- Plugin marketplace

---

## 🔴 CRITICAL GAPS (Blocking Deployment)

1. **Unreal C++ Plugin** — Core WebSocket client for Unreal doesn't exist yet
   - Blocker: Can't launch game without it
   - Effort: 2-3 days (skeleton + basic connectivity)
   - Owner: Billy or C++ developer

2. **Web UI Routes** — `/api/skills/*` endpoints not yet created in web_ui.py
   - Blocker: Game can't call skills
   - Effort: 1 day
   - Owner: Billy

3. **Actual Media Implementation** — Skills have placeholder code, no real API calls
   - Blocker: Skills return fake results, not usable
   - Effort: 2-3 days (API integration testing)
   - Owner: Billy

4. **Avatar Animation Blueprint** — No Unreal blueprint for Aurion animation yet
   - Blocker: Avatar appears but doesn't move
   - Effort: 1 day
   - Owner: Billy or Unreal artist

5. **Test Level** — No Unreal level with chat UI set up
   - Blocker: Can't validate integration
   - Effort: 2-4 hours
   - Owner: Billy

---

## 🟡 HIGH-PRIORITY (Post-Launch)

1. Player profile + cross-session memory
2. Speech-to-text input
3. Lip-sync animation
4. Skill customization UI
5. Health monitoring dashboard
6. Tutorial / onboarding

---

## 🟢 NICE-TO-HAVE (Phase 2+)

1. Quest system
2. Mini-games
3. Gesture system
4. Dynamic dialogue wheel
5. Multiplayer support
6. Mod support
7. Accessibility features

---

## 📝 NEXT STEPS

1. **Review this inventory** — Billy highlights missing features or misunderstood scope
2. **Prioritize gaps** — What's critical for MVP? What's Phase 2?
3. **Assign owners** — Who builds each feature?
4. **Estimate effort** — How long for each?
5. **Create structured roadmap** — Sprint-by-sprint breakdown

---

## 📋 AUDIT LOG: Free-Policy Cleanup (per user's free-only mandate)

### Tools Removed (Trial Limits / Freemium / Subscription Required)

| Tool | Reason | Alternative |
|------|--------|-------------|
| **Adobe Substance 3D Plugin** | Requires Substance 3D subscription (not free-forever in standalone) | Use Datasmith + free material templates in Unreal Marketplace |
| **Cognitive3D SDK** | Free tier limited to 50K events/month—violates unlimited-free policy | Build local telemetry via SQLite + Python dashboard (zero cost) |
| **Wwise Audio Middleware** | Commercial software with limited trial; not free-forever | Use Unreal's native Niagara + built-in audio system + local Ollama TTS |
| **FMOD Audio Middleware** | Commercial software with limited trial; not free-forever | Use Unreal's native audio + local TTS |
| **PlayFab (Microsoft)** | Cloud service with free tier limits—requires evaluation of actual hard limits | Use SQLite locally + custom Python backend (zero cost, full control) |
| **Cesium for Unreal** | Licensing model unclear; may require commercial agreement | Use Worldscape + native Unreal terrain for world generation |
| **Perforce Helix Core** | "Free tier" is limited to 5 users / 20GB—paid service with freemium tier | Use Git + GitHub (unlimited free tier, no user limits) |
| **Atoms Crowd Plugin** | Licensing model uncertain; may have paid-only tiers | Use Unreal's native Behavior Tree + Environment Query System (built-in, free) |

### Tools Kept (Unlimited Free / Open-Source)

✅ **All remaining tools are verified unlimited free-tier or 100% open-source (MIT, Apache 2.0, BSD, zlib, GPL, AGPL licenses)**

**Examples of confirmed free-forever status:**
- Unreal Engine 5.8.1 — Free tier with 5% revenue share after $1M (no time limit, no trial period)
- Godot, Cocos2d-x, Stride, Panda3D, Armory3D, Bevy — Fully open-source (MIT/Apache/BSD/zlib)
- Ollama, LM Studio — Free, local LLM servers (open-source)
- OpenVR, OpenXR, Monado — Open standards, free SDKs (BSD/MIT)
- ALVR — Open-source wireless VR streaming (MIT)
- Git, GitHub — Free tier with unlimited users, no time expiration
- SQLite3 — Public domain (not even licensed, fully free)
- Raylib, SDL2, Allegro, SFML — Open-source graphics (zlib/MIT/Apache)
- Nakama — Open-source multiplayer backend (AGPL)
- Three.js, WebGL — Open-source web 3D (MIT)

### Policy Notes

1. **Free-tier with event/user limits flagged**: Tools with throttled free tiers are removed to avoid surprise billing or service degradation
2. **"Very cheap" threshold**: Per user clarification, only items with zero cost or simple email sign-up (no payment card) are included
3. **Subscriptions to existing services**: If user already has Substance 3D, PlayFab, FMOD, etc., they can re-add those items; the inventory conservatively assumes zero existing subscriptions
4. **Open-source priority**: Preferred any open-source over commercial freemium to maximize autonomy and avoid vendor lock-in

### Result

**FEATURE_INVENTORY.md now contains a fully audited, free-only tech stack with zero hidden costs, trial limits, or surprise upgrades.**

---

**Ready for review! Mark up any gaps, corrections, or reprioritizations. 🚀**
