"""
AURION UNREAL 5.8.1 BRIDGE
Bi-directional integration with Unreal Engine 5.8.1+ for live game deployment.

Key responsibilities:
1. WebSocket/HTTP API for Unreal → Aurion communication
2. State sync: Aurion avatar (animation, emotion, speech) → Unreal viewport
3. Media pipeline: Generated images/videos → Unreal Sequencer/textures
4. Native Unreal plugin interface (C++ callable)
5. Replicated state for multiplayer support
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Coroutine
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

logger = logging.getLogger(__name__)


class UnrealMessageType(Enum):
    """Message types for Unreal ↔ Aurion communication"""
    # Aurion → Unreal
    AVATAR_STATE = "avatar_state"           # Pose, expression, emotion
    SPEECH_OUTPUT = "speech_output"         # Text + audio for voice
    GENERATED_IMAGE = "generated_image"     # Image to display
    GENERATED_VIDEO = "generated_video"     # Video animation
    CODE_EXECUTION = "code_execution"       # Execute Unreal command
    ANIMATION_TRIGGER = "animation_trigger" # Start animation sequence
    
    # Unreal → Aurion
    PLAYER_INPUT = "player_input"           # Player action/dialogue
    AVATAR_REQUEST = "avatar_request"       # Request avatar state
    SPEECH_REQUEST = "speech_request"       # Request speech output
    SKILL_REQUEST = "skill_request"         # Request skill execution
    ENVIRONMENT_STATE = "environment_state" # World state update


@dataclass
class AvatarState:
    """Aurion's avatar state for Unreal rendering"""
    position: Dict[str, float]      # x, y, z in Unreal coordinates
    rotation: Dict[str, float]      # pitch, yaw, roll
    emotion: str                    # "happy", "sad", "neutral", etc.
    expression: str                 # "smile", "frown", "focused", etc.
    gaze_target: Optional[Dict[str, float]] = None  # Look-at target
    animation_state: Optional[str] = None   # Current animation playing
    is_speaking: bool = False
    confidence: float = 1.0         # Confidence in this state


@dataclass
class SpeechOutput:
    """Speech data for Unreal audio playback"""
    text: str
    audio_path: Optional[str] = None  # Local path to generated audio
    voice_id: str = "aurion_default"
    emotion: str = "neutral"
    speed: float = 1.0
    lip_sync_data: Optional[Dict[str, Any]] = None  # Phoneme timing


@dataclass
class SkillRequest:
    """Request from Unreal for Aurion skill execution"""
    skill_name: str
    params: Dict[str, Any]
    request_id: str = ""
    priority: str = "normal"  # low, normal, high


class UnrealBridge:
    """
    WebSocket server for Unreal 5.8.1 integration.
    
    Usage in Unreal:
    1. Create WebSocket client that connects to localhost:9876
    2. Send messages via UnrealBridgeClient plugin
    3. Receive state updates in real-time
    4. Render Aurion avatar with synchronized animations + speech
    """
    
    def __init__(self, host: str = "localhost", port: int = 9876, unreal_version: str = "5.8.1"):
        self.host = host
        self.port = port
        self.unreal_version = unreal_version
        self.websocket_clients: List[WebSocketServerProtocol] = []
        self.message_handlers: Dict[UnrealMessageType, Callable] = {}
        self.server = None
        self.running = False
        
        logger.info(f"[UNREAL] Bridge initialized for UE {unreal_version} at {host}:{port}")
    
    async def start(self):
        """Start WebSocket server"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("[UNREAL] websockets library not installed. Run: pip install websockets")
            return
        
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            compression=None,  # Disable compression for real-time performance
            ping_interval=30,
            ping_timeout=10
        )
        self.running = True
        logger.info(f"[UNREAL] WebSocket server listening on {self.host}:{self.port}")
    
    async def stop(self):
        """Stop WebSocket server"""
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        logger.info("[UNREAL] WebSocket server stopped")
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle incoming WebSocket connection from Unreal"""
        self.websocket_clients.append(websocket)
        logger.info(f"[UNREAL] Client connected: {websocket.remote_address}")
        
        try:
            async for message in websocket:
                await self._process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[UNREAL] Client disconnected: {websocket.remote_address}")
        finally:
            if websocket in self.websocket_clients:
                self.websocket_clients.remove(websocket)
    
    async def _process_message(self, websocket: WebSocketServerProtocol, raw_message: str):
        """Process incoming message from Unreal"""
        try:
            msg = json.loads(raw_message)
            msg_type = UnrealMessageType(msg.get("type"))
            
            logger.debug(f"[UNREAL] Received: {msg_type.value}")
            
            # Route to handler if registered
            if msg_type in self.message_handlers:
                handler = self.message_handlers[msg_type]
                response = await self._run_async_or_sync(handler, msg.get("data", {}))
                if response:
                    await websocket.send(json.dumps({
                        "type": msg.get("type"),
                        "request_id": msg.get("request_id"),
                        "response": response
                    }))
        except Exception as e:
            logger.error(f"[UNREAL] Message processing error: {e}")
            try:
                await websocket.send(json.dumps({
                    "type": "error",
                    "error": str(e)
                }))
            except Exception:
                pass
    
    async def _run_async_or_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Run function, handling both async and sync callables"""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    def register_message_handler(self, msg_type: UnrealMessageType, handler: Callable):
        """Register a handler for incoming message types"""
        self.message_handlers[msg_type] = handler
        logger.info(f"[UNREAL] Handler registered for {msg_type.value}")
    
    async def send_avatar_state(self, state: AvatarState):
        """Broadcast avatar state to all connected Unreal clients"""
        message = {
            "type": UnrealMessageType.AVATAR_STATE.value,
            "timestamp": datetime.now().isoformat(),
            "data": asdict(state)
        }
        await self._broadcast(json.dumps(message))
    
    async def send_speech(self, speech: SpeechOutput):
        """Send speech output to Unreal for playback"""
        message = {
            "type": UnrealMessageType.SPEECH_OUTPUT.value,
            "timestamp": datetime.now().isoformat(),
            "data": asdict(speech)
        }
        await self._broadcast(json.dumps(message))
    
    async def send_generated_media(self, media_type: str, media_path: str, metadata: Optional[Dict] = None):
        """Send generated image/video to Unreal"""
        msg_type = UnrealMessageType.GENERATED_IMAGE if media_type == "image" \
                   else UnrealMessageType.GENERATED_VIDEO
        
        # Read file and encode as base64 for transmission
        try:
            with open(media_path, 'rb') as f:
                file_size = os.path.getsize(media_path)
                if file_size > 50 * 1024 * 1024:  # > 50MB
                    # For large files, send path instead of data
                    file_data = None
                    logger.info(f"[UNREAL] Large file, sending path reference: {media_path}")
                else:
                    import base64
                    file_data = base64.b64encode(f.read()).decode('utf-8')
            
            message = {
                "type": msg_type.value,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "path": str(media_path),
                    "file_data": file_data,
                    "size": file_size,
                    "metadata": metadata or {}
                }
            }
            await self._broadcast(json.dumps(message))
        except Exception as e:
            logger.error(f"[UNREAL] Failed to send media: {e}")
    
    async def execute_unreal_command(self, command: str, params: Dict[str, Any]) -> Any:
        """Execute a command in Unreal (via Blueprint/C++)"""
        message = {
            "type": UnrealMessageType.CODE_EXECUTION.value,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "command": command,
                "params": params
            }
        }
        await self._broadcast(json.dumps(message))
    
    async def request_skill_execution(self, skill_request: SkillRequest) -> Dict[str, Any]:
        """Request skill execution from Aurion (called by Unreal)"""
        logger.info(f"[UNREAL] Skill request: {skill_request.skill_name}")
        
        from joi_companion.core.skills_engine import get_skills_engine
        engine = get_skills_engine()
        
        result = engine.execute_skill(skill_request.skill_name, **skill_request.params)
        return result or {"status": "error", "error": "Skill execution failed"}
    
    async def _broadcast(self, message: str):
        """Broadcast message to all connected clients"""
        if not self.websocket_clients:
            logger.debug("[UNREAL] No clients connected for broadcast")
            return
        
        dead_clients = []
        for client in self.websocket_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                dead_clients.append(client)
            except Exception as e:
                logger.error(f"[UNREAL] Broadcast error: {e}")
                dead_clients.append(client)
        
        # Clean up dead connections
        for client in dead_clients:
            if client in self.websocket_clients:
                self.websocket_clients.remove(client)


class UnrealIntegration:
    """High-level Unreal integration orchestrator"""
    
    def __init__(self, enabled: bool = True, unreal_version: str = "5.8.1"):
        self.enabled = enabled and WEBSOCKETS_AVAILABLE
        self.unreal_version = unreal_version
        self.bridge: Optional[UnrealBridge] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        
        if self.enabled:
            self._setup()
    
    def _setup(self):
        """Initialize Unreal bridge and event loop"""
        self.bridge = UnrealBridge(unreal_version=self.unreal_version)
        
        # Register default message handlers
        self.bridge.register_message_handler(
            UnrealMessageType.PLAYER_INPUT,
            self._handle_player_input
        )
        self.bridge.register_message_handler(
            UnrealMessageType.SKILL_REQUEST,
            self._handle_skill_request
        )
        self.bridge.register_message_handler(
            UnrealMessageType.ENVIRONMENT_STATE,
            self._handle_environment_state
        )
        
        logger.info("[UNREAL] Integration setup complete")
    
    async def _handle_player_input(self, data: Dict) -> Dict:
        """Handle input from Unreal (dialogue, actions, etc.)"""
        logger.info(f"[UNREAL] Player input: {data}")
        
        # Route to personality engine for response
        from joi_companion.core.personality_engine import get_personality_engine
        engine = get_personality_engine()
        
        response = await engine.process_player_input(data)
        return response
    
    async def _handle_skill_request(self, data: Dict) -> Dict:
        """Handle skill execution request from Unreal"""
        request = SkillRequest(**data)
        
        if self.bridge:
            return await self.bridge.request_skill_execution(request)
        return {"status": "error", "error": "Bridge not initialized"}
    
    async def _handle_environment_state(self, data: Dict) -> Dict:
        """Handle environment state updates from Unreal"""
        logger.info(f"[UNREAL] Environment state: {data}")
        return {"status": "ack", "acknowledged": True}
    
    async def sync_avatar_state(self, emotion: str, expression: str, 
                               position: Dict[str, float], rotation: Dict[str, float]):
        """Sync Aurion avatar state to Unreal"""
        if not self.enabled or not self.bridge:
            return
        
        state = AvatarState(
            emotion=emotion,
            expression=expression,
            position=position,
            rotation=rotation
        )
        await self.bridge.send_avatar_state(state)
    
    async def sync_speech(self, text: str, audio_path: Optional[str] = None,
                         voice_id: str = "aurion_default", emotion: str = "neutral"):
        """Sync speech to Unreal"""
        if not self.enabled or not self.bridge:
            return
        
        speech = SpeechOutput(
            text=text,
            audio_path=audio_path,
            voice_id=voice_id,
            emotion=emotion
        )
        await self.bridge.send_speech(speech)
    
    async def sync_generated_image(self, image_path: str, metadata: Optional[Dict] = None):
        """Sync generated image to Unreal"""
        if not self.enabled or not self.bridge:
            return
        
        await self.bridge.send_generated_media("image", image_path, metadata)
    
    async def sync_generated_video(self, video_path: str, metadata: Optional[Dict] = None):
        """Sync generated video to Unreal"""
        if not self.enabled or not self.bridge:
            return
        
        await self.bridge.send_generated_media("video", video_path, metadata)
    
    def start_server(self):
        """Start the WebSocket server in background"""
        if not self.enabled or not self.bridge:
            logger.warning("[UNREAL] Integration disabled or bridge not available")
            return
        
        try:
            self.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.event_loop)
            
            # Run server in thread
            import threading
            server_thread = threading.Thread(
                target=self._run_event_loop,
                daemon=True
            )
            server_thread.start()
            logger.info("[UNREAL] WebSocket server started in background thread")
        except Exception as e:
            logger.error(f"[UNREAL] Failed to start server: {e}")
    
    def _run_event_loop(self):
        """Run the event loop (called in background thread)"""
        try:
            if self.event_loop and self.bridge:
                self.event_loop.run_until_complete(self.bridge.start())
                self.event_loop.run_forever()
        except Exception as e:
            logger.error(f"[UNREAL] Event loop error: {e}")
    
    def stop_server(self):
        """Stop the WebSocket server"""
        if self.event_loop and self.bridge:
            future = asyncio.run_coroutine_threadsafe(
                self.bridge.stop(),
                self.event_loop
            )
            try:
                future.result(timeout=5)
            except Exception as e:
                logger.error(f"[UNREAL] Error stopping server: {e}")


# Global instance
_unreal_integration: Optional[UnrealIntegration] = None


def get_unreal_integration() -> Optional[UnrealIntegration]:
    """Get or create the global Unreal integration instance"""
    global _unreal_integration
    if _unreal_integration is None:
        enabled = os.getenv("UNREAL_ENGINE_ENABLED", "false").lower() == "true"
        version = os.getenv("UNREAL_ENGINE_VERSION", "5.8.1")
        _unreal_integration = UnrealIntegration(enabled=enabled, unreal_version=version)
    return _unreal_integration
