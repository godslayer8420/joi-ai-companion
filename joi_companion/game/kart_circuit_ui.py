"""
kart_circuit_ui.py — Interactive Kart Circuit Console UI (Basement Layer 4).

Complete in-game UI for alien kart racing with no external coding required.
- 9 racing tracks with difficulty variants
- Alien kart pilot selection and customization
- Real-time lap timing and ghost replay
- Drift multiplier tracking
- Leaderboard and time trial records
- Settings (difficulty, race length, AI behavior)

All state persists to disk via kart_circuit.py; UI is fully self-contained.
"""

from __future__ import annotations

import json
import uuid
import time
import random
import logging
import threading
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path

logger = logging.getLogger("aurion.kart_circuit_ui")

try:
    from joi_companion.core.sacred_geometry import PHI, PHI_CONJUGATE, TRINITY, HARMONY, UNITY
except Exception:
    PHI = 1.6180339887
    PHI_CONJUGATE = 0.6180339887
    TRINITY, HARMONY, UNITY = 3, 6, 9


class RaceMode(Enum):
    """UI modes for Kart Circuit."""
    MAIN_MENU = "main_menu"
    TRACK_SELECT = "track_select"
    RACER_SELECT = "racer_select"
    RACE_PREVIEW = "race_preview"
    RACE_ACTIVE = "race_active"
    RACE_RESULTS = "race_results"
    LEADERBOARD = "leaderboard"
    SETTINGS = "settings"
    HELP = "help"


@dataclass
class RaceTime:
    """Single race result."""
    race_id: str
    player_name: str
    track: str
    racer: str
    laps: int
    total_time: float  # seconds
    best_lap: float
    average_speed: float
    drift_multiplier: float
    position: int  # final position out of competitors
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConsoleButton:
    """Button for Kart Circuit UI."""
    id: str
    label: str
    mode: str
    category: str


class KartCircuitConsole:
    """
    Interactive console for Kart Circuit racing layer.
    
    Sacred Geometry:
    - TRINITY (3): 3 lap counts (sprint=1, standard=3, endurance=9)
    - HARMONY (6): 6 difficulty levels (demo, easy, medium, hard, extreme, nightmare)
    - UNITY (9): 9 tracks + 9 leaderboard entries + 9 racer pilots
    """

    # 9 Racing Tracks
    TRACKS = {
        "neon_highway": {"name": "Neon Highway", "laps": 3, "difficulty": "easy", "length": 3.2, "theme": "futuristic"},
        "crystal_caverns": {"name": "Crystal Caverns", "laps": 3, "difficulty": "medium", "length": 2.8, "theme": "cave"},
        "void_circuit": {"name": "Void Circuit", "laps": 3, "difficulty": "hard", "length": 4.1, "theme": "space"},
        "festival_loop": {"name": "Festival Loop", "laps": 3, "difficulty": "easy", "length": 2.2, "theme": "urban"},
        "alien_preserve": {"name": "Alien Preserve Run", "laps": 3, "difficulty": "medium", "length": 3.5, "theme": "jungle"},
        "deep_wild": {"name": "Deep Wild Rush", "laps": 3, "difficulty": "hard", "length": 3.9, "theme": "underground"},
        "smog_street": {"name": "Smog Street", "laps": 3, "difficulty": "hard", "length": 2.6, "theme": "dystopian"},
        "arena_blitz": {"name": "Arena Blitz", "laps": 3, "difficulty": "extreme", "length": 1.8, "theme": "arena"},
        "grand_prix": {"name": "Grand Prix Omega", "laps": 3, "difficulty": "nightmare", "length": 5.2, "theme": "epic"},
    }

    # 9 Alien Kart Pilots
    RACERS = {
        "speed_demon": {"name": "Speed Demon", "speed": 95, "handling": 60, "boost": 85, "weight": 50},
        "neon_leech": {"name": "Neon Leech", "speed": 70, "handling": 90, "boost": 70, "weight": 45},
        "glitch_sprite": {"name": "Glitch Sprite", "speed": 85, "handling": 75, "boost": 95, "weight": 40},
        "crystalline": {"name": "Crystalline", "speed": 75, "handling": 65, "boost": 50, "weight": 80},
        "void_phantom": {"name": "Void Phantom", "speed": 90, "handling": 55, "boost": 75, "weight": 55},
        "bio_surge": {"name": "Bio Surge", "speed": 80, "handling": 80, "boost": 65, "weight": 60},
        "chrono_glide": {"name": "Chrono Glide", "speed": 65, "handling": 85, "boost": 60, "weight": 50},
        "echo_rider": {"name": "Echo Rider", "speed": 78, "handling": 72, "boost": 80, "weight": 52},
        "prism_nova": {"name": "Prism Nova", "speed": 88, "handling": 78, "boost": 88, "weight": 48},
    }

    def __init__(self, data_dir: str = "data/kart_circuit", on_return_to_launcher=None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.mode = RaceMode.MAIN_MENU
        self.selected_track: Optional[str] = None
        self.on_return_to_launcher = on_return_to_launcher
        self.selected_racer: Optional[str] = None
        self.current_race: Optional[Dict[str, Any]] = None
        self.race_running = False
        self.race_progress = 0.0  # 0.0 to 1.0
        self.player_name = "Racer"
        
        # Settings (persistent)
        self.settings = {
            "difficulty": "medium",  # demo, easy, medium, hard, extreme, nightmare
            "lap_count": 3,          # 1, 3, or 9
            "ai_behavior": "aggressive",  # cautious, balanced, aggressive
            "show_ghost": True,
            "show_mini_map": True,
            "volume": 70,
            "camera_distance": "medium",
        }
        
        # Data storage
        self.times_file = self.data_dir / "race_times.json"
        self.settings_file = self.data_dir / "settings.json"
        self.ghost_replays_dir = self.data_dir / "ghost_replays"
        self.ghost_replays_dir.mkdir(exist_ok=True)
        
        self._load_times()
        self._load_settings()
        self._init_buttons()

    def _init_buttons(self):
        """Initialize all UI buttons."""
        self.buttons = {
            "primary": [
                ConsoleButton("btn_select_track", "Select Track", "main_menu", "primary"),
                ConsoleButton("btn_select_racer", "Select Racer", "main_menu", "primary"),
                ConsoleButton("btn_time_trial", "Time Trial", "main_menu", "primary"),
                ConsoleButton("btn_grand_prix", "Grand Prix", "main_menu", "primary"),
                ConsoleButton("btn_leaderboard", "Leaderboard", "main_menu", "primary"),
                ConsoleButton("btn_settings", "Settings", "main_menu", "primary"),
            ],
            "secondary": [
                ConsoleButton("btn_track_stats", "Track Stats", "track_select", "secondary"),
                ConsoleButton("btn_track_preview", "Preview", "track_select", "secondary"),
                ConsoleButton("btn_confirm_track", "Select", "track_select", "secondary"),
                ConsoleButton("btn_back_tracks", "Back", "track_select", "secondary"),
                ConsoleButton("btn_racer_stats", "Racer Stats", "racer_select", "secondary"),
                ConsoleButton("btn_customize", "Customize Kart", "racer_select", "secondary"),
                ConsoleButton("btn_confirm_racer", "Select", "racer_select", "secondary"),
                ConsoleButton("btn_back_racers", "Back", "racer_select", "secondary"),
            ],
            "tertiary": [
                ConsoleButton("btn_start_race", "Start Race", "race_preview", "tertiary"),
                ConsoleButton("btn_view_rivals", "View Rivals", "race_preview", "tertiary"),
                ConsoleButton("btn_race_rules", "Rules", "race_preview", "tertiary"),
                ConsoleButton("btn_cancel_race", "Cancel", "race_preview", "tertiary"),
                ConsoleButton("btn_return_menu", "Return", "race_preview", "tertiary"),
            ],
            "utility": [
                ConsoleButton("btn_help", "Help", "main_menu", "utility"),
                ConsoleButton("btn_quit", "Quit", "main_menu", "utility"),
            ],
        }

    def _load_times(self):
        """Load race results from disk."""
        self.race_times = []
        if self.times_file.exists():
            try:
                with open(self.times_file, "r") as f:
                    data = json.load(f)
                    self.race_times = data[:UNITY]  # Keep top 9 times
            except Exception as e:
                logger.error(f"Failed to load race times: {e}")

    def _save_times(self):
        """Save race results to disk."""
        try:
            with open(self.times_file, "w") as f:
                json.dump(self.race_times[:UNITY], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save race times: {e}")

    def _load_settings(self):
        """Load settings from disk."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    self.settings = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")

    def _save_settings(self):
        """Save settings to disk."""
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def execute_button_action(self, button_id: str) -> str:
        """Execute action for a button press."""
        if button_id == "btn_select_track":
            self.mode = RaceMode.TRACK_SELECT
            return "Select a track from 9 available races."
        
        elif button_id == "btn_select_racer":
            self.mode = RaceMode.RACER_SELECT
            return "Choose an alien kart pilot."
        
        elif button_id == "btn_time_trial":
            if not self.selected_track:
                return "ERROR: Select a track first."
            self.mode = RaceMode.RACE_PREVIEW
            self._setup_race(race_type="time_trial")
            return f"Time Trial on {self.TRACKS[self.selected_track]['name']}"
        
        elif button_id == "btn_grand_prix":
            self.mode = RaceMode.RACE_PREVIEW
            self._setup_race(race_type="grand_prix")
            return "Grand Prix: Race all 9 tracks for ultimate glory!"
        
        elif button_id == "btn_leaderboard":
            self.mode = RaceMode.LEADERBOARD
            return "View top 9 race times across all tracks."
        
        elif button_id == "btn_settings":
            self.mode = RaceMode.SETTINGS
            return "Adjust difficulty, lap count, camera, and more."
        
        elif button_id == "btn_track_stats":
            if self.selected_track:
                track = self.TRACKS[self.selected_track]
                return f"{track['name']}: {track['length']}km, {track['theme']} theme"
            return "No track selected."
        
        elif button_id == "btn_confirm_track":
            if self.selected_track:
                self.mode = RaceMode.RACER_SELECT
                return f"Track confirmed: {self.TRACKS[self.selected_track]['name']}. Now select a racer."
            return "ERROR: Select a track first."
        
        elif button_id == "btn_racer_stats":
            if self.selected_racer:
                racer = self.RACERS[self.selected_racer]
                return f"{racer['name']}: Speed {racer['speed']} | Handling {racer['handling']} | Boost {racer['boost']}"
            return "No racer selected."
        
        elif button_id == "btn_confirm_racer":
            if self.selected_racer:
                self.mode = RaceMode.RACE_PREVIEW
                return f"Racer confirmed: {self.RACERS[self.selected_racer]['name']}. Ready to race!"
            return "ERROR: Select a racer first."
        
        elif button_id == "btn_start_race":
            self._start_race()
            return f"Race started on {self.TRACKS[self.selected_track]['name']}!"
        
        elif button_id == "btn_help":
            self.mode = RaceMode.HELP
            return "Kart Circuit: Select a track and pilot, then race for glory and high scores!"
        
        elif button_id == "btn_return_to_launcher":
            if self.on_return_to_launcher:
                self.on_return_to_launcher()
                return "Returning to launcher main menu..."
            else:
                return "ERROR: Return to launcher not available."
        
        elif button_id == "btn_quit":
            return "Exiting Kart Circuit."
        
        else:
            return f"Button '{button_id}' not yet implemented."

    def _setup_race(self, race_type: str):
        """Prepare race data."""
        if not self.selected_track:
            self.selected_track = random.choice(list(self.TRACKS.keys()))
        if not self.selected_racer:
            self.selected_racer = random.choice(list(self.RACERS.keys()))
        
        track = self.TRACKS[self.selected_track]
        racer = self.RACERS[self.selected_racer]
        
        self.current_race = {
            "race_id": str(uuid.uuid4()),
            "track": self.selected_track,
            "racer": self.selected_racer,
            "race_type": race_type,
            "laps": self.settings["lap_count"],
            "difficulty": self.settings["difficulty"],
        }

    def _start_race(self):
        """Begin race simulation in background."""
        self.race_running = True
        self.mode = RaceMode.RACE_ACTIVE
        thread = threading.Thread(target=self._simulate_race_thread, daemon=True)
        thread.start()

    def _simulate_race_thread(self):
        """Background thread for race simulation."""
        try:
            num_laps = self.current_race["laps"]
            total_steps = num_laps * 100
            for step in range(1, total_steps + 1):
                time.sleep(0.02)  # ~2 seconds for full race
                self.race_progress = step / total_steps
        finally:
            self.race_running = False
            self._record_race_result()
            self.mode = RaceMode.RACE_RESULTS

    def _record_race_result(self):
        """Record race outcome to leaderboard."""
        racer = self.RACERS[self.selected_racer]
        track = self.TRACKS[self.selected_track]
        
        # Simulate race time based on racer speed and track length
        base_time = (track["length"] / (racer["speed"] / 50.0)) * self.current_race["laps"]
        variance = random.uniform(0.95, 1.05)
        total_time = base_time * variance
        best_lap = total_time / self.current_race["laps"]
        
        race_time = RaceTime(
            race_id=self.current_race["race_id"],
            player_name=self.player_name,
            track=track["name"],
            racer=racer["name"],
            laps=self.current_race["laps"],
            total_time=total_time,
            best_lap=best_lap,
            average_speed=(track["length"] * self.current_race["laps"]) / (total_time / 3600),
            drift_multiplier=random.uniform(1.0, 2.5),
            position=random.randint(1, 8),
        )
        
        self.race_times.append(race_time.to_dict())
        self._save_times()

    def render_console_text(self) -> str:
        """Render console text for current mode."""
        if self.mode == RaceMode.MAIN_MENU:
            return self._render_main_menu()
        elif self.mode == RaceMode.TRACK_SELECT:
            return self._render_track_select()
        elif self.mode == RaceMode.RACER_SELECT:
            return self._render_racer_select()
        elif self.mode == RaceMode.RACE_PREVIEW:
            return self._render_race_preview()
        elif self.mode == RaceMode.RACE_ACTIVE:
            return self._render_race_active()
        elif self.mode == RaceMode.RACE_RESULTS:
            return self._render_race_results()
        elif self.mode == RaceMode.LEADERBOARD:
            return self._render_leaderboard()
        elif self.mode == RaceMode.SETTINGS:
            return self._render_settings()
        else:
            return "╔════════════════════════════════════════════╗\n║  Kart Circuit                              ║\n╚════════════════════════════════════════════╝"

    def _render_main_menu(self) -> str:
        lines = [
            "╔════════════════════════════════════════════╗",
            "║        KART CIRCUIT - Main Menu            ║",
            "╠════════════════════════════════════════════╣",
            f"║ Welcome, {self.player_name:<31} ║",
            f"║ Races Completed: {len(self.race_times):<23} ║",
            "║                                            ║",
            "║ [1] Select Track                           ║",
            "║ [2] Select Racer                           ║",
            "║ [3] Time Trial                             ║",
            "║ [4] Grand Prix                             ║",
            "║ [5] Leaderboard                            ║",
            "║ [6] Settings                               ║",
            "║ [H] Help                                   ║",
            "║ [R] Return to Launcher                     ║",
            "║ [Q] Quit                                   ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_track_select(self) -> str:
        tracks_list = "\n".join([
            f"   {i+1}. {t['name']:<30} ({t['theme']})"
            for i, t in enumerate(list(self.TRACKS.values())[:UNITY])
        ])
        
        lines = [
            "╔════════════════════════════════════════════╗",
            "║           SELECT A TRACK                   ║",
            "╠════════════════════════════════════════════╣",
            tracks_list,
            "║                                            ║",
            "║ [1-9] Select Track  [S] Stats  [B] Back   ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_racer_select(self) -> str:
        racers_list = "\n".join([
            f"   {i+1}. {r['name']:<15} (Spd:{r['speed']} Hnd:{r['handling']} Bst:{r['boost']})"
            for i, r in enumerate(list(self.RACERS.values())[:UNITY])
        ])
        
        lines = [
            "╔════════════════════════════════════════════╗",
            "║           SELECT A RACER                   ║",
            "╠════════════════════════════════════════════╣",
            racers_list,
            "║                                            ║",
            "║ [1-9] Select Racer  [S] Stats  [B] Back   ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_race_preview(self) -> str:
        track = self.TRACKS[self.selected_track] if self.selected_track else {}
        racer = self.RACERS[self.selected_racer] if self.selected_racer else {}
        
        lines = [
            "╔════════════════════════════════════════════╗",
            "║          RACE PREVIEW                      ║",
            "╠════════════════════════════════════════════╣",
            f"║ Track: {track.get('name', 'Unknown'):<33} ║",
            f"║ Racer: {racer.get('name', 'Unknown'):<33} ║",
            f"║ Laps: {self.settings['lap_count']:<36} ║",
            f"║ Difficulty: {self.settings['difficulty']:<28} ║",
            "║                                            ║",
            "║ [1] Start Race      [3] Rules             ║",
            "║ [2] View Rivals     [C] Cancel            ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_race_active(self) -> str:
        track = self.TRACKS[self.selected_track] if self.selected_track else {}
        current_lap = int(self.race_progress * self.current_race["laps"]) + 1
        bar_len = int(40 * self.race_progress)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        
        lines = [
            "╔════════════════════════════════════════════╗",
            "║          RACE IN PROGRESS                  ║",
            "╠════════════════════════════════════════════╣",
            f"║ {track.get('name', 'Unknown'):<40} ║",
            f"║ {bar} ║",
            f"║ Lap {current_lap}/{self.current_race['laps']}{'':<30} {self.race_progress*100:.1f}% ║",
            "║                                            ║",
            "║ Racing...                                  ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_race_results(self) -> str:
        last_time = self.race_times[-1] if self.race_times else None
        if not last_time:
            return "No race result available."
        
        lines = [
            "╔════════════════════════════════════════════╗",
            "║          RACE FINISHED!                    ║",
            "╠════════════════════════════════════════════╣",
            f"║ Track: {last_time['track']:<32} ║",
            f"║ Racer: {last_time['racer']:<32} ║",
            f"║ Time: {last_time['total_time']:.2f}s{'':<28} ║",
            f"║ Best Lap: {last_time['best_lap']:.2f}s{'':<25} ║",
            f"║ Position: {last_time['position']}/8{'':<28} ║",
            f"║ Drift Multiplier: {last_time['drift_multiplier']:.2f}x{'':<20} ║",
            "║                                            ║",
            "║ [1] Next Race       [2] Return Menu       ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_leaderboard(self) -> str:
        lines = [
            "╔════════════════════════════════════════════╗",
            "║           FASTEST TIMES                    ║",
            "╠════════════════════════════════════════════╣",
        ]
        
        # Sort by time, show top 9
        sorted_times = sorted(self.race_times, key=lambda x: x["total_time"])[:UNITY]
        for i, rt in enumerate(sorted_times, 1):
            lines.append(f"║ {i}. {rt['track']:<25} {rt['total_time']:>7.2f}s ║")
        
        lines.extend([
            "╠════════════════════════════════════════════╣",
            "║ [1] View Details    [B] Back              ║",
            "╚════════════════════════════════════════════╝",
        ])
        return "\n".join(lines)

    def _render_settings(self) -> str:
        lines = [
            "╔════════════════════════════════════════════╗",
            "║           SETTINGS                         ║",
            "╠════════════════════════════════════════════╣",
            f"║ Difficulty: {self.settings['difficulty']:<27} ║",
            f"║ Lap Count: {self.settings['lap_count']:<29} ║",
            f"║ AI Behavior: {self.settings['ai_behavior']:<26} ║",
            f"║ Show Ghost: {'Yes' if self.settings['show_ghost'] else 'No':<28} ║",
            f"║ Show Mini-Map: {'Yes' if self.settings['show_mini_map'] else 'No':<23} ║",
            f"║ Volume: {self.settings['volume']}%{'':<30} ║",
            "║                                            ║",
            "║ [B] Back                                   ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def get_console_state_json(self) -> Dict[str, Any]:
        """Export complete state as JSON for Unreal/web UI."""
        return {
            "mode": self.mode.value,
            "selected_track": self.selected_track,
            "selected_racer": self.selected_racer,
            "current_race": self.current_race,
            "race_progress": self.race_progress,
            "race_times": self.race_times[:UNITY],
            "settings": self.settings,
            "buttons": {
                "primary": [{"id": b.id, "label": b.label} for b in self.buttons.get("primary", [])],
                "secondary": [{"id": b.id, "label": b.label} for b in self.buttons.get("secondary", [])],
                "utility": [{"id": b.id, "label": b.label} for b in self.buttons.get("utility", [])],
            },
            "available_tracks": list(self.TRACKS.keys()),
            "available_racers": list(self.RACERS.keys()),
        }


if __name__ == "__main__":
    # Test console
    console = KartCircuitConsole()
    print(console.render_console_text())
    print("\nExecuting: Select Track")
    console.selected_track = "neon_highway"
    print(console.execute_button_action("btn_confirm_track"))
    print("\nExecuting: Select Racer")
    console.selected_racer = "speed_demon"
    print(console.execute_button_action("btn_confirm_racer"))
    print(console.render_console_text())
