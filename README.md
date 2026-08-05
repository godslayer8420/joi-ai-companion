# Aurion Runtime

Aurion is the in-game AI companion model in a local-first Flask runtime with live world simulation, HUD/status surfaces, memory continuity, avatar/media pipelines, and an Unreal bridge. Billy is the human user, player, and project owner.

Aurion is the centerpiece of the experience: the highest-priority companion, the emotional anchor, and the most important system in the world. The game is being built to make her feel legendary, immersive, and first-of-its-kind, with Billy permanently beside her and no NPC or other player character ever rising above either of them.

The main entrypoint is **`run_web_ui.py`**, which launches **`web_ui.py`** as the primary operator surface.

## Quickstart

### 1. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Set optional environment variables

Aurion runs locally by default.

```powershell
$env:AURION_BIND_HOST="127.0.0.1"
$env:AURION_PORT="5000"
```

### 4. Launch the runtime

```powershell
python .\run_web_ui.py
```

Then open `http://<AURION_BIND_HOST>:<AURION_PORT>`.

With the defaults above, that is `http://127.0.0.1:5000`.

## Default runtime behavior

| Area | Current behavior |
| --- | --- |
| Bind host | `127.0.0.1` by default |
| Port | `5000` by default |
| Primary app | `web_ui.py` |
| Launcher | `run_web_ui.py` |
| Trust surface | Boot/setup card with consent and memory controls |
| World clock | Synced to real-world server local time |
| Remote mode | Disabled by default unless explicitly enabled |
| Downloads secret hydration | Disabled by default unless explicitly enabled |

## Key environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `AURION_BIND_HOST` | Flask bind host | `127.0.0.1` |
| `AURION_PORT` | Flask port | `5000` |
| `AURION_DEBUG` | Enables Flask debug mode | `false` |
| `AURION_ALLOW_REMOTE` | Allows non-local access | `false` |
| `AURION_API_KEY` | Required for hardened remote mode | unset |
| `AURION_ENFORCE_API_KEY_ALL` | Requires API key on all routes when enabled | auto |
| `AURION_TLS_CERT_FILE` | TLS certificate path | unset |
| `AURION_TLS_KEY_FILE` | TLS key path | unset |
| `AURION_TLS_ADHOC` | Enables ad hoc TLS | `false` |
| `AURION_REQUIRE_TLS_REMOTE` | Forces TLS when remote access is enabled | follows remote mode |
| `AURION_MAX_UPLOAD_MB` | Upload cap | `1024` |
| `AURION_ALLOW_DOWNLOADS_SECRET_HYDRATION` | Allows loading optional key files from Downloads | `false` |
| `AURION_AVATAR_REFERENCE_DIR` | Preferred avatar reference image directory | unset |
| `AURION_UNREAL_RC_URL` | Unreal remote control base URL | `http://127.0.0.1:30010` |
| `AURION_UNREAL_BRIDGE_URL` | Override the Unreal bridge state endpoint | `http://127.0.0.1:<AURION_PORT>/api/bridge/unreal/state` |
| `AURION_WORLD_CONTINUITY_DIR` | World continuity manifest storage | `%LOCALAPPDATA%\Aurion\world_continuity\v1` |
| `AURION_LUMEN_CITY_DIR` | Lumen City storage | `%LOCALAPPDATA%\Aurion\lumen_city\v1` |

## Operator surfaces

### Boot/setup card

Use the boot/setup surface to control:

- listening mode
- continuous listening
- microphone consent
- camera consent
- memory mode
- memory save enablement

These values persist into the live runtime through the trust/consent API rather than staying as client-only UI settings.

### Companion status

The companion panel shows:

- current emotional/runtime summary
- mic, camera, voice, and memory state
- synced world clock and timezone
- recent runtime events
- operator memory deletion controls

### Runtime capability panel

The runtime panel summarizes:

- senses
- memory continuity
- video state
- chat pressure and latency
- perception state
- world simulation state
- capability coherence

The world summary now includes the live synced world clock.

### HUD and clock surfaces

Aurion maintains:

- a visible topbar clock
- legacy hidden clock/elapsed fields for compatibility
- world-time summary in the boot card
- runtime/world summaries sourced from one canonical backend time payload

## Time sync model

Aurion uses the server's real-world local time as the canonical clock source.

That canonical time is propagated through:

- `GET /api/time/now`
- `world_continuity.time_sync`
- runtime world state
- HUD/status surfaces
- Unreal bridge state

This keeps the UI clock, world summaries, and Unreal-facing contract aligned to the same authority.

## Important APIs

| Route | Purpose |
| --- | --- |
| `GET /api/status` | Main runtime status payload used by polling surfaces |
| `GET /api/hud` | HUD/runtime summary payload |
| `GET /api/companion/status` | Companion trust/runtime state |
| `POST /api/trust/consent` | Saves consent/listening/memory settings |
| `POST /api/memory/manage` | Deletes recent memory items or clears memory |
| `GET /api/time/now` | Canonical world clock payload |
| `GET /api/bridge/unreal/state` | Unreal-facing runtime contract (local privileged access only) |

## Remote access and security notes

Local-only use is the safest default.

If you enable remote mode:

1. Set `AURION_ALLOW_REMOTE=true`
2. Set a strong `AURION_API_KEY`
3. Prefer TLS via `AURION_TLS_CERT_FILE` and `AURION_TLS_KEY_FILE`, or enable `AURION_TLS_ADHOC`
4. Review host/origin settings before exposing the runtime

Do not enable Downloads-based secret hydration unless you explicitly want the runtime to load `.env`-style key files from your Downloads folder.

## Avatar and media notes

Aurion can work with:

- default avatar models under `static\models`
- uploaded `.glb`, `.gltf`, and `.vrm` files
- reference image sets used for avatar color/palette inference

The runtime also exposes media, world, and bridge state through the main operator UI.

## Troubleshooting

### The server starts but I cannot open the UI

- confirm the process is running
- confirm the bind host and port
- open `http://<AURION_BIND_HOST>:<AURION_PORT>`
- if you changed the port, use that port in the browser

### My changes are not reflected in the world clock

- refresh the UI
- confirm `/api/time/now` returns the expected timezone/time
- confirm the runtime world summary shows the updated clock

### Remote mode does not work

- verify `AURION_ALLOW_REMOTE=true`
- verify `AURION_API_KEY` is set
- verify your chosen host, firewall, and TLS configuration

### Avatar references are missing

- set `AURION_AVATAR_REFERENCE_DIR`, or
- place reference images in one of the recognized fallback folders

## Additional documentation

- `README_AURION_SYSTEM_MANUAL.md` contains a broader live-system manual
- `web_ui.py` contains most of the current runtime logic and API implementations
