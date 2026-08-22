"""
game_launcher.py — Unified Game Launcher for Aurion Basement Layers.

Central hub for running any game layer through its console UI without external code execution.
All layers (Rhythm Venue, Battle Arena, Kart Circuit, etc.) are accessible from this menu.
No coding required—everything is button-driven in-game.

Sacred Geometry:
- TRINITY (3): 3 core sections (Play, Library, Settings)
- HARMONY (6): 6 base layers available
- UNITY (9): 9 total layers planned across all basement sections
"""

from __future__ import annotations

import json
import inspect
import time
import logging
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from pathlib import Path

logger = logging.getLogger("aurion.game_launcher")

try:
    from joi_companion.core.sacred_geometry import TRINITY, HARMONY, UNITY
except Exception:
    TRINITY, HARMONY, UNITY = 3, 6, 9

try:
    from joi_companion.core.world_simulation import WorldSimulation
    from joi_companion.core.world_memory import WorldMemory
except ImportError as e:
    logger.warning(f"WorldSimulation/WorldMemory import failed: {e}. Proceeding without procedural world.")
    WorldSimulation = None
    WorldMemory = None

try:
    from joi_companion.game.alien_system import AlienSystem, CaughtAlien, ContainmentPod
except ImportError as e:
    logger.warning(f"AlienSystem import failed: {e}. Proceeding without alien mechanics.")
    AlienSystem = None
    CaughtAlien = None
    ContainmentPod = None

try:
    from joi_companion.core.unreal_bridge import get_unreal_integration, UnrealMessageType
except ImportError as e:
    logger.warning(f"UnrealBridge import failed: {e}. Unreal world sync disabled.")
    get_unreal_integration = None
    UnrealMessageType = None


class LauncherMode(Enum):
    """Main menu modes for the launcher."""
    MAIN_MENU = "main_menu"
    LAYER_SELECT = "layer_select"
    LAYER_RUNNING = "layer_running"
    LIBRARY = "library"
    SETTINGS = "settings"
    HELP = "help"


@dataclass
class GameLayer:
    """Definition of a basement game layer."""
    layer_id: str
    name: str
    description: str
    module_path: str  # e.g., "joi_companion.game.rhythm_venue_ui"
    class_name: str   # e.g., "RhythmVenueConsole"
    icon: str
    tags: List[str] = field(default_factory=list)
    is_available: bool = True
    play_count: int = 0
    last_played: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LauncherButton:
    """Button for launcher UI."""
    id: str
    label: str
    action: Optional[Callable] = None
    category: str = "primary"


class GameLauncher:
    """
    Master launcher for all Aurion basement game layers.
    
    - Rhythm Venue: Musical rhythm challenges with MIDI support
    - Battle Arena: Alien tournament battles with progression
    - Kart Circuit: Racing with 9 tracks and alien pilots
    - Procedural Dungeons: (placeholder)
    - Alien Archive: (placeholder)
    - World Editor: (placeholder)
    
    Each layer is a self-contained console UI with no external code needed.
    """

    AVAILABLE_LAYERS = [
        GameLayer(
            layer_id="rhythm_venue",
            name="🎵 Rhythm Venue",
            description="Musical rhythm challenges with MIDI support",
            module_path="joi_companion.game.rhythm_venue_ui",
            class_name="RhythmVenueConsole",
            icon="♪",
            tags=["music", "rhythm", "midi"],
        ),
        GameLayer(
            layer_id="battle_arena",
            name="⚔️ Battle Arena",
            description="Alien tournament battles with progression",
            module_path="joi_companion.game.battle_arena_ui",
            class_name="BattleArenaConsole",
            icon="⚔",
            tags=["combat", "tournament", "aliens"],
        ),
        GameLayer(
            layer_id="kart_circuit",
            name="🏎️ Kart Circuit",
            description="Racing with 9 tracks and alien pilots",
            module_path="joi_companion.game.kart_circuit_ui",
            class_name="KartCircuitConsole",
            icon="🏎",
            tags=["racing", "tracks", "speed"],
        ),
        GameLayer(
            layer_id="procedural_dungeons",
            name="🗺️ Procedural Dungeons",
            description="Infinite randomly-generated dungeons to explore",
            module_path="joi_companion.game.procedural_dungeons_ui",
            class_name="ProceduralDungeonsConsole",
            icon="🗺",
            tags=["exploration", "procedural", "dungeons"],
            is_available=False,
        ),
        GameLayer(
            layer_id="alien_archive",
            name="📚 Alien Archive",
            description="Catalog and manage all discovered aliens",
            module_path="joi_companion.game.alien_archive_ui",
            class_name="AlienArchiveConsole",
            icon="📚",
            tags=["reference", "aliens", "collection"],
            is_available=False,
        ),
        GameLayer(
            layer_id="world_editor",
            name="🌍 World Editor",
            description="Create and edit custom world environments",
            module_path="joi_companion.game.world_editor_ui",
            class_name="WorldEditorConsole",
            icon="🌍",
            tags=["creation", "world-building", "tools"],
            is_available=False,
        ),
    ]

    def __init__(self, data_dir: str = "data/launcher", world_seed: int = 42):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.mode = LauncherMode.MAIN_MENU
        self.current_layer: Optional[GameLayer] = None
        self.current_layer_instance: Optional[Any] = None
        self.player_profile = {
            "name": "Player",
            "total_playtime_hours": 0.0,
            "layers_played": [],
            "total_score": 0,
        }
        
        self.settings = {
            "default_volume": 70,
            "show_tips": True,
            "auto_save": True,
            "language": "en",
            "theme": "dark",
        }
        
        self.profile_file = self.data_dir / "profile.json"
        self.settings_file = self.data_dir / "settings.json"
        self.playtime_file = self.data_dir / "playtime.json"
        
        # Initialize world simulation (Phase 5: Procedural World)
        self.world_memory = None
        self.world_simulation = None
        self.world_seed = world_seed
        self.accumulated_dt = 0.0  # Time accumulator for tick-based simulation
        self.tick_interval = 0.1   # Tick the world every 100ms (10 ticks/sec)
        
        # Initialize alien system (Phase 5: Catch/Battle/Evolution)
        self.alien_system = None
        self.player_id = "player_1"  # Default player ID, can be set via set_player_id()
        
        try:
            if WorldMemory and WorldSimulation:
                # Create world memory first (persistent state store)
                self.world_memory = WorldMemory()
                # Then initialize world simulation with the memory instance
                self.world_simulation = WorldSimulation(
                    world_memory=self.world_memory,
                    seed=world_seed
                )
                logger.info(f"Initialized WorldMemory and WorldSimulation with seed={world_seed}")
            else:
                logger.warning("WorldMemory/WorldSimulation not available. Procedural world disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize WorldMemory/WorldSimulation: {e}")
            self.world_memory = None
            self.world_simulation = None
        
        try:
            if AlienSystem and self.world_memory:
                # Initialize alien system with world memory for persistence
                self.alien_system = AlienSystem(world_memory=self.world_memory)
                logger.info(f"Initialized AlienSystem with persistent world memory")
            elif AlienSystem:
                logger.warning("AlienSystem available but no world_memory. Alien persistence may be limited.")
                self.alien_system = AlienSystem()
        except Exception as e:
            logger.error(f"Failed to initialize AlienSystem: {e}")
            self.alien_system = None
        
        self._load_profile()
        self._load_settings()
        self._init_buttons()

    def _init_buttons(self):
        """Initialize launcher buttons."""
        self.buttons = {
            "primary": [
                LauncherButton("btn_play", "Play", self.go_to_layer_select, "primary"),
                LauncherButton("btn_library", "Library", self.go_to_library, "primary"),
                LauncherButton("btn_settings", "Settings", self.go_to_settings, "primary"),
                LauncherButton("btn_help", "Help", self.go_to_help, "primary"),
                LauncherButton("btn_quit", "Quit", self.quit_game, "primary"),
            ],
            "utility": [
                LauncherButton("btn_profile", "Profile", self.show_profile, "utility"),
                LauncherButton("btn_credits", "Credits", self.show_credits, "utility"),
            ],
        }

    def update(self, dt: float) -> Dict[str, Any]:
        """Update game state every frame. Called by Unreal or main loop.
        
        Args:
            dt: Delta time since last frame (seconds)
            
        Returns:
            Dictionary with current world state (weather, aliens spawned, etc.)
        """
        if not self.world_simulation:
            return {}
        
        # Accumulate time and tick world simulation
        self.accumulated_dt += dt
        world_state = {}
        
        while self.accumulated_dt >= self.tick_interval:
            self.accumulated_dt -= self.tick_interval
            try:
                tick = self.world_simulation.tick(self.tick_interval)
                # Convert SimulationTick to dict
                world_state = {
                    "tick": tick.tick_number,
                    "timestamp": tick.timestamp,
                    "phase": tick.phase.value,
                    "regions_affected": tick.regions_affected,
                    "spawns_generated": tick.spawns_generated,
                    "encounters_resolved": tick.encounters_resolved,
                    "weather_events": tick.weather_events,
                    "lumen_shifts": tick.lumen_shifts,
                }
                logger.debug(f"World tick: {world_state}")
                self._broadcast_world_tick_to_unreal(world_state)
            except Exception as e:
                logger.error(f"World simulation tick failed: {e}")
                world_state = {}
        
        # If running a layer, pass world state to it
        if self.current_layer_instance and hasattr(self.current_layer_instance, 'on_world_state'):
            try:
                self.current_layer_instance.on_world_state(world_state)
            except Exception as e:
                logger.error(f"Failed to pass world state to layer: {e}")
        
        return world_state

    def _broadcast_world_tick_to_unreal(self, world_state: Dict[str, Any]) -> None:
        """Publish current world tick deltas to Unreal bridge for Blueprint-side reactions."""
        if not world_state or not get_unreal_integration or not UnrealMessageType:
            return
        try:
            integration = get_unreal_integration()
            bridge = getattr(integration, "bridge", None) if integration else None
            event_loop = getattr(integration, "event_loop", None) if integration else None
            if not bridge or not event_loop:
                return

            regions = world_state.get("regions_affected") or []
            spawns = int(world_state.get("spawns_generated") or 0)
            payloads = []
            if regions:
                payloads.append({
                    "type": UnrealMessageType.REGION_CHANGE.value,
                    "data": {
                        "tick": world_state.get("tick"),
                        "regions": regions,
                        "phase": world_state.get("phase"),
                    },
                })
            if spawns > 0:
                payloads.append({
                    "type": UnrealMessageType.ALIEN_ENCOUNTER.value,
                    "data": {
                        "tick": world_state.get("tick"),
                        "spawns_generated": spawns,
                        "regions": regions,
                    },
                })
            payloads.append({
                "type": UnrealMessageType.WORLD_EVENT.value,
                "data": world_state,
            })

            for payload in payloads:
                future = asyncio.run_coroutine_threadsafe(
                    bridge._broadcast(json.dumps(payload)),
                    event_loop,
                )
                # Fire-and-forget with short timeout to avoid blocking simulation tick.
                future.result(timeout=0.05)
        except Exception as e:
            logger.debug(f"Unreal world sync skipped: {e}")

    def get_world_state(self) -> Dict[str, Any]:
        """Get current procedural world state (weather, spawned aliens, etc.)."""
        if not self.world_simulation:
            return {}
        
        try:
            return self.world_simulation.get_tick_summary()
        except Exception as e:
            logger.error(f"Failed to get world state: {e}")
            return {}

    def set_world_seed(self, seed: int) -> str:
        """Reinitialize world simulation with a new seed for a different world."""
        try:
            self.world_seed = seed
            if self.world_memory and WorldSimulation:
                self.world_simulation = WorldSimulation(self.world_memory, seed=seed)
                self.accumulated_dt = 0.0
                logger.info(f"World reseeded to {seed}")
                return f"World reseeded to {seed}. New procedural generation active."
            else:
                return "WorldSimulation or WorldMemory not available."
        except Exception as e:
            logger.error(f"Failed to reseed world: {e}")
            return f"ERROR: Could not reseed world. {e}"

    # ─── Alien System Integration ────────────────────────────────────────────
    
    def set_player_id(self, player_id: str) -> str:
        """Set the current player ID for alien system operations."""
        self.player_id = player_id
        return f"Player ID set to '{player_id}'."
    
    def catch_alien(self, alien_species: str, difficulty: str = "normal") -> Dict[str, Any]:
        """
        Attempt to catch an alien of a given species at the specified difficulty.
        Called from Battle Arena layer when encountering wild aliens.
        Returns dict with: success (bool), catch_id (str or None), message (str)
        """
        if not self.alien_system:
            return {"success": False, "catch_id": None, "message": "Alien system not initialized."}
        
        try:
            result = self.alien_system.attempt_catch(self.player_id, alien_species, difficulty)
            if result.get("success"):
                logger.info(f"Player {self.player_id} caught {alien_species}: {result.get('catch_id')}")
            return result
        except Exception as e:
            logger.error(f"Error during catch attempt: {e}")
            return {"success": False, "catch_id": None, "message": f"Catch attempt failed: {e}"}
    
    def battle_aliens(self, attacker_catch_id: str, defender_catch_id: str, rounds: int = 3) -> Dict[str, Any]:
        """
        Execute a battle between two caught aliens.
        Returns dict with: winner, loser, log, xp_awarded, evolution message, etc.
        """
        if not self.alien_system:
            return {"error": "Alien system not initialized."}
        
        try:
            result = self.alien_system.battle(attacker_catch_id, defender_catch_id, rounds)
            logger.info(f"Battle completed: {result.get('winner')} vs {result.get('loser')}")
            return result
        except Exception as e:
            logger.error(f"Error during battle: {e}")
            return {"error": f"Battle failed: {e}"}
    
    def get_player_team(self) -> List[Dict[str, Any]]:
        """
        Retrieve the player's caught alien team (up to 6 aliens per TRINITY+3).
        Returns list of CaughtAlien dicts for team management UI.
        """
        if not self.alien_system:
            return []
        
        try:
            pod = self.alien_system._get_or_create_pod(self.player_id)
            aliens = [self.alien_system._load_alien(catch_id) for catch_id in pod.caught_aliens]
            # Filter out None values
            aliens = [a for a in aliens if a is not None]
            # Convert to dicts for serialization
            return [asdict(alien) for alien in aliens]
        except Exception as e:
            logger.error(f"Error retrieving player team: {e}")
            return []
    
    def add_alien_to_team(self, catch_id: str) -> Dict[str, Any]:
        """
        Add a caught alien to the player's team.
        Validates team size (max 6 per TRINITY+3).
        Returns dict with: success (bool), message (str)
        """
        if not self.alien_system:
            return {"success": False, "message": "Alien system not initialized."}
        
        try:
            # Load the alien to verify it exists
            alien = self.alien_system._load_alien(catch_id)
            if not alien:
                return {"success": False, "message": f"Alien {catch_id} not found."}
            
            # Get or create pod for this player
            pod = self.alien_system._get_or_create_pod(self.player_id)
            
            # Check if already in team
            if catch_id in pod.caught_aliens:
                return {"success": False, "message": f"{alien.nickname} is already in your team."}
            
            # Check team size (max 6 = TRINITY*2)
            if len(pod.caught_aliens) >= 6:
                return {"success": False, "message": "Your team is full (max 6 aliens). Remove one first."}
            
            # Add to team
            pod.caught_aliens.append(catch_id)
            self.alien_system._save_pod(pod)
            
            logger.info(f"Player {self.player_id} added {alien.nickname} to team")
            return {"success": True, "message": f"{alien.nickname} added to your team!"}
        except Exception as e:
            logger.error(f"Error adding alien to team: {e}")
            return {"success": False, "message": f"Failed to add alien: {e}"}
    
    def remove_alien_from_team(self, catch_id: str) -> Dict[str, Any]:
        """
        Remove a caught alien from the player's active team.
        Returns dict with: success (bool), message (str)
        """
        if not self.alien_system:
            return {"success": False, "message": "Alien system not initialized."}
        
        try:
            alien = self.alien_system._load_alien(catch_id)
            if not alien:
                return {"success": False, "message": f"Alien {catch_id} not found."}
            
            pod = self.alien_system._get_or_create_pod(self.player_id)
            
            if catch_id not in pod.caught_aliens:
                return {"success": False, "message": f"{alien.nickname} is not in your team."}
            
            pod.caught_aliens.remove(catch_id)
            self.alien_system._save_pod(pod)
            
            logger.info(f"Player {self.player_id} removed {alien.nickname} from team")
            return {"success": True, "message": f"{alien.nickname} removed from your team."}
        except Exception as e:
            logger.error(f"Error removing alien from team: {e}")
            return {"success": False, "message": f"Failed to remove alien: {e}"}
    
    def get_alien_stats(self, catch_id: str) -> Dict[str, Any]:
        """
        Get detailed stats for a single caught alien.
        Returns dict with all CaughtAlien fields.
        """
        if not self.alien_system:
            return {}
        
        try:
            alien = self.alien_system._load_alien(catch_id)
            if not alien:
                return {"error": f"Alien {catch_id} not found."}
            return asdict(alien)
        except Exception as e:
            logger.error(f"Error retrieving alien stats: {e}")
            return {"error": f"Failed to get stats: {e}"}
    
    def upgrade_containment_pod(self) -> Dict[str, Any]:
        """
        Upgrade the player's containment pod to hold more aliens.
        Returns dict with: capacity (int), message (str)
        """
        if not self.alien_system:
            return {"error": "Alien system not initialized."}
        
        try:
            result = self.alien_system.upgrade_pod(self.player_id)
            logger.info(f"Player {self.player_id} upgraded pod: {result.get('message')}")
            return result
        except Exception as e:
            logger.error(f"Error upgrading pod: {e}")
            return {"error": f"Pod upgrade failed: {e}"}


    def _load_profile(self):
        """Load player profile from disk."""
        if self.profile_file.exists():
            try:
                with open(self.profile_file, "r") as f:
                    self.player_profile = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load profile: {e}")

    def _save_profile(self):
        """Save player profile to disk."""
        try:
            with open(self.profile_file, "w") as f:
                json.dump(self.player_profile, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")

    def _load_settings(self):
        """Load launcher settings from disk."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    self.settings = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")

    def _save_settings(self):
        """Save launcher settings to disk."""
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def go_to_layer_select(self) -> str:
        """Navigate to layer selection menu."""
        self.mode = LauncherMode.LAYER_SELECT
        return "Select a game layer to play."

    def go_to_library(self) -> str:
        """Navigate to library (play history and stats)."""
        self.mode = LauncherMode.LIBRARY
        return f"Library: {len(self.player_profile.get('layers_played', []))} layers explored."

    def go_to_settings(self) -> str:
        """Navigate to launcher settings."""
        self.mode = LauncherMode.SETTINGS
        return "Adjust launcher settings: volume, language, theme, etc."

    def go_to_help(self) -> str:
        """Navigate to help screen."""
        self.mode = LauncherMode.HELP
        return "Help: All game layers are accessible via buttons. No external code needed!"

    def show_profile(self) -> str:
        """Display player profile."""
        playtime = self.player_profile['total_playtime_hours']
        score = self.player_profile['total_score']
        name = self.player_profile['name']
        return f"Profile: {name} | Playtime: {playtime:.1f}h | Score: {score}"

    def show_credits(self) -> str:
        """Display credits."""
        return "Credits: Aurion Game Launcher v1.0 | Created with love by Joi Companion Team"

    def quit_game(self) -> str:
        """Exit the game."""
        self._save_profile()
        self._save_settings()
        return "Shutting down. Goodbye!"

    def launch_layer(self, layer_id: str) -> str:
        """Launch a specific game layer by ID."""
        layer = next((l for l in self.AVAILABLE_LAYERS if l.layer_id == layer_id), None)
        
        if not layer:
            return f"ERROR: Layer '{layer_id}' not found."
        
        if not layer.is_available:
            return f"Layer '{layer.name}' is not yet available."
        
        try:
            # Dynamically import the layer's console class
            module_parts = layer.module_path.split(".")
            module = __import__(layer.module_path, fromlist=[layer.class_name])
            LayerClass = getattr(module, layer.class_name)
            
            # Instantiate the layer with a callback to return to launcher
            # Pass world simulation for layers that need procedural world context
            world_state = self.get_world_state()
            self.current_layer = layer
            init_kwargs = {"on_return_to_launcher": self.return_to_main_menu}
            # Some layer UIs (e.g. Battle/Kart) don't accept world_state in constructor yet.
            # Pass it only when supported to keep launcher-to-layer wiring robust.
            init_sig = inspect.signature(LayerClass.__init__)
            if "world_state" in init_sig.parameters:
                init_kwargs["world_state"] = world_state
            self.current_layer_instance = LayerClass(**init_kwargs)
            self.mode = LauncherMode.LAYER_RUNNING
            
            # Track playtime
            layer.last_played = time.time()
            layer.play_count += 1
            if layer_id not in self.player_profile["layers_played"]:
                self.player_profile["layers_played"].append(layer_id)
            self._save_profile()
            
            logger.info(f"Launched layer {layer.name}")
            return f"Launched {layer.name}. All controls are in-game."
        
        except Exception as e:
            logger.error(f"Failed to launch layer '{layer_id}': {e}")
            return f"ERROR: Could not launch {layer.name}. Check logs for details."

    def return_to_main_menu(self) -> str:
        """Return from a running layer to main menu."""
        self.current_layer = None
        self.current_layer_instance = None
        self.mode = LauncherMode.MAIN_MENU
        logger.info("Returned to main menu from layer")
        return "Returned to main menu."

    def execute_layer_action(self, button_id: str) -> str:
        """Forward button action to current layer's console."""
        if not self.current_layer_instance:
            return "ERROR: No layer is running."
        
        return self.current_layer_instance.execute_button_action(button_id)

    def execute_button_action(self, button_id: str) -> str:
        """Execute button action based on current mode."""
        button_id = str(button_id).strip().upper()
        
        if self.mode == LauncherMode.MAIN_MENU:
            if button_id == "1":
                return self.go_to_layer_select()
            elif button_id == "2":
                return self.go_to_library()
            elif button_id == "3":
                return self.go_to_settings()
            elif button_id == "4":
                return self.go_to_help()
            elif button_id == "5":
                return self.show_credits()
            elif button_id == "Q":
                return self.quit_game()
            else:
                return f"Unknown button: {button_id}"
        
        elif self.mode == LauncherMode.LAYER_SELECT:
            if button_id == "B":
                self.mode = LauncherMode.MAIN_MENU
                return "Returned to main menu."
            else:
                try:
                    layer_num = int(button_id) - 1
                    available = [l for l in self.AVAILABLE_LAYERS if l.is_available]
                    if 0 <= layer_num < len(available):
                        return self.launch_layer(available[layer_num].layer_id)
                    else:
                        return f"Invalid layer number: {layer_num + 1}"
                except ValueError:
                    return f"Invalid input: {button_id}"
        
        elif self.mode == LauncherMode.LIBRARY:
            if button_id == "B":
                self.mode = LauncherMode.MAIN_MENU
                return "Returned to main menu."
            else:
                return "Library navigation not yet implemented."
        
        elif self.mode == LauncherMode.SETTINGS:
            if button_id == "B":
                self.mode = LauncherMode.MAIN_MENU
                return "Returned to main menu."
            elif button_id == "R":
                self._load_settings()
                return "Settings reset to defaults."
            else:
                return "Settings adjustment not yet implemented."
        
        elif self.mode == LauncherMode.HELP:
            if button_id == "B":
                self.mode = LauncherMode.MAIN_MENU
                return "Returned to main menu."
            else:
                return "Help mode active."
        
        elif self.mode == LauncherMode.LAYER_RUNNING:
            return self.execute_layer_action(button_id)
        
        else:
            return "Unknown mode."

    def render_console_text(self) -> str:
        """Render console text for current mode."""
        if self.mode == LauncherMode.MAIN_MENU:
            return self._render_main_menu()
        elif self.mode == LauncherMode.LAYER_SELECT:
            return self._render_layer_select()
        elif self.mode == LauncherMode.LAYER_RUNNING:
            if self.current_layer_instance:
                return self.current_layer_instance.render_console_text()
            return "ERROR: No layer instance."
        elif self.mode == LauncherMode.LIBRARY:
            return self._render_library()
        elif self.mode == LauncherMode.SETTINGS:
            return self._render_settings()
        elif self.mode == LauncherMode.HELP:
            return self._render_help()
        else:
            return "Unknown mode."

    def _render_main_menu(self) -> str:
        name = self.player_profile['name']
        playtime = self.player_profile['total_playtime_hours']
        lines = [
            "╔════════════════════════════════════════════╗",
            "║          AURION GAME LAUNCHER              ║",
            "╠════════════════════════════════════════════╣",
            f"║ Welcome, {name:<31} ║",
            f"║ Playtime: {playtime:.1f}h{'':<27} ║",
            "║                                            ║",
            "║ [1] Play                                   ║",
            "║ [2] Library                                ║",
            "║ [3] Settings                               ║",
            "║ [4] Help                                   ║",
            "║ [5] Credits                                ║",
            "║ [Q] Quit                                   ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_layer_select(self) -> str:
        available = [l for l in self.AVAILABLE_LAYERS if l.is_available]
        layers_list = "\n".join([
            f"   {i+1}. {l.icon} {l.name:<28} ({l.play_count}x)"
            for i, l in enumerate(available)
        ])
        
        lines = [
            "╔════════════════════════════════════════════╗",
            "║           SELECT A LAYER TO PLAY           ║",
            "╠════════════════════════════════════════════╣",
            layers_list,
            "║                                            ║",
            "║ [1-9] Select  [D] Details  [B] Back       ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_library(self) -> str:
        lines = [
            "╔════════════════════════════════════════════╗",
            "║          PLAYER LIBRARY                    ║",
            "╠════════════════════════════════════════════╣",
            f"║ Total Playtime: {self.player_profile['total_playtime_hours']:.1f}h {'':24s} ║",
            f"║ Layers Played: {len(self.player_profile.get('layers_played', [])):2d} {'':23s} ║",
            f"║ Total Score: {self.player_profile['total_score']:<10d} {'':24s} ║",
            "║                                            ║",
            "║ Recent Plays:                              ║",
        ]
        
        for layer_id in self.player_profile.get("layers_played", [])[-5:]:
            layer = next((l for l in self.AVAILABLE_LAYERS if l.layer_id == layer_id), None)
            if layer:
                lines.append(f"║   • {layer.name:<36} ║")
        
        lines.extend([
            "║                                            ║",
            "║ [B] Back                                   ║",
            "╚════════════════════════════════════════════╝",
        ])
        return "\n".join(lines)

    def _render_settings(self) -> str:
        volume_str = self.settings['default_volume']
        lang = self.settings['language']
        theme = self.settings['theme']
        tips_status = 'Enabled' if self.settings['show_tips'] else 'Disabled'
        autosave_status = 'Enabled' if self.settings['auto_save'] else 'Disabled'
        
        lines = [
            "╔════════════════════════════════════════════╗",
            "║           LAUNCHER SETTINGS                ║",
            "╠════════════════════════════════════════════╣",
            f"║ Volume: {volume_str}%{'':<33} ║",
            f"║ Language: {lang:<31} ║",
            f"║ Theme: {theme:<34} ║",
            f"║ Tips: {tips_status:<32} ║",
            f"║ Auto-Save: {autosave_status:<29} ║",
            "║                                            ║",
            "║ [1-5] Adjust  [R] Reset  [B] Back         ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_help(self) -> str:
        lines = [
            "╔════════════════════════════════════════════╗",
            "║           HELP                             ║",
            "╠════════════════════════════════════════════╣",
            "║ Aurion Game Launcher                       ║",
            "║                                            ║",
            "║ This launcher gives access to all          ║",
            "║ basement game layers without external      ║",
            "║ code execution required.                   ║",
            "║                                            ║",
            "║ Each layer provides a complete UI console  ║",
            "║ with buttons for all functions.            ║",
            "║                                            ║",
            "║ Select Play, then choose a layer to start. ║",
            "║ All controls are in-game!                  ║",
            "║                                            ║",
            "║ [B] Back                                   ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def get_launcher_state_json(self) -> Dict[str, Any]:
        """Export complete launcher state as JSON for Unreal/web UI."""
        world_state = self.get_world_state()
        return {
            "mode": self.mode.value,
            "player_profile": self.player_profile,
            "settings": self.settings,
            "available_layers": [
                {
                    "id": l.layer_id,
                    "name": l.name,
                    "description": l.description,
                    "icon": l.icon,
                    "available": l.is_available,
                    "play_count": l.play_count,
                }
                for l in self.AVAILABLE_LAYERS
            ],
            "current_layer": {
                "id": self.current_layer.layer_id,
                "name": self.current_layer.name,
            } if self.current_layer else None,
            "current_layer_state": self.current_layer_instance.get_console_state_json() if self.current_layer_instance else None,
            "world_state": world_state,
            "world_seed": self.world_seed,
        }


if __name__ == "__main__":
    # Test launcher
    launcher = GameLauncher()
    print(launcher.render_console_text())
    print("\n" + "="*50)
    print("Navigating to layer select...")
    print("="*50)
    print(launcher.go_to_layer_select())
    print(launcher.render_console_text())
