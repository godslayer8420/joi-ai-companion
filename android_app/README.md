# Aurion Mobile — Android Scaffold

## Status
**Scaffold: ✅ buildable**  
**APK output: see D:\Downloads\Aurion-Android-debug.apk and Aurion-app-debug.apk**

## Build

```bash
cd android_app
./gradlew assembleDebug
```

Requires Android SDK installed and `local.properties` with `sdk.dir` set:

```properties
# android_app/local.properties  (DO NOT COMMIT)
sdk.dir=C:\\Users\\<you>\\AppData\\Local\\Android\\Sdk
```

## Architecture

```
MainActivity  →  AurionApiClient (Retrofit)  →  web_ui.py  (:7860)
                       ↓
              ChatRequest / ChatResponse (Gson)
```

Backend URL defaults to `http://10.0.2.2:7860/` (Android emulator loopback to host).
Change for physical device by setting `AURION_BASE_URL` build var.

## Known blocked features

| Feature | Blocker | Source location |
|---------|---------|----------------|
| 3D avatar rendering | SceneForm / Filament not wired; GLB files in `static/models/` | Needs SceneView dependency |
| Voice playback / TTS | MSIX voice packs not in source tree | `D:\Downloads\Others\Aurion files\` |
| Lip-sync animation | Depends on Unreal bridge events; not bridged to Android yet | `joi_companion/core/unreal_bridge.py` |
| Microphone STT | `RECORD_AUDIO` permission declared; no STT client wired yet | — |

## File layout

```
android_app/
├── settings.gradle.kts          # project name + module includes
├── build.gradle.kts             # AGP 8.5.2 + Kotlin 1.9.24
├── gradle.properties            # JVM args, AndroidX flags
├── app/
│   ├── build.gradle.kts         # compileSdk 34, minSdk 26
│   ├── proguard-rules.pro
│   └── src/main/
│       ├── AndroidManifest.xml
│       ├── java/com/aurion/mobile/
│       │   ├── MainActivity.kt  # launch activity
│       │   └── AurionApiClient.kt  # Retrofit client
│       └── res/
│           ├── layout/activity_main.xml
│           └── values/{strings,themes}.xml
```
