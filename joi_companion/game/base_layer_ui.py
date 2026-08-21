"""
base_layer_ui.py — Unified Game Layer UI Framework.

Every game layer (Rhythm Venue, Battle Arena, Kart Circuit, etc.) inherits from
BaseLayerUI to provide consistent in-game console experience with no external
code execution required.

Sacred geometry:
  - TRINITY (3): core gameplay loops per layer
  - HARMONY (6): menu sections per layer
  - UNITY (9): leaderboard/history entries displayed
"""

from __future__ import annotations

import json
import threading
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
from enum import Enum

logger = logging.getLogger("aurion.game.ui")

try:
    from joi_companion.core.sacred_geometry import PHI, TRINITY, HARMONY, UNITY
except Exception:
    PHI = 1.6180339887
    TRINITY, HARMONY, UNITY = 3, 6, 9


class UIMode(Enum):
    """Global UI state modes."""
    MAIN_MENU = "main_menu"
    SETTINGS = "settings"
    LOADING = "loading"
    GAMEPLAY = "gameplay"
    PAUSE = "pause"
    RESULTS = "results"
    LEADERBOARD = "leaderboard"
    HELP = "help"


@dataclass
class UIButton:
    """Interactive button definition."""
    id: str
    label: str
    category: str  # "action", "navigation", "utility"
    action: Callable
    enabled: bool = True
    help_text: str = ""
    icon: str = ""
    hotkey: Optional[str] = None  # Single key binding


@dataclass
class GameScore:
    """Score/result record."""
    player_id: str
    score: int
    level: int
    difficulty: str
    timestamp: float
    session_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UIState:
    """Current console state."""
    mode: UIMode = UIMode.MAIN_MENU
    error_message: Optional[str] = None
    status_message: str = ""
    progress_pct: int = 0
    selected_item_id: Optional[str] = None
    scroll_offset: int = 0
    paused: bool = False


class BaseLayerUI(ABC):
    """
    Abstract base class for all game layer UIs.
    Every layer implements this to provide consistent in-game console.
    """

    def __init__(self, layer_name: str, data_dir: str = "data", on_return_to_launcher=None):
        """
        Args:
            layer_name: Readable name (e.g., "Rhythm Venue", "Battle Arena")
            data_dir: Base directory for layer data
            on_return_to_launcher: Optional callback to invoke when user returns to launcher
        """
        self.layer_name = layer_name
        self.data_dir = Path(data_dir) / layer_name.lower().replace(" ", "_")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.state = UIState()
        self.buttons: Dict[str, UIButton] = {}
        self.scores: List[GameScore] = []
        self.settings: Dict[str, Any] = {}
        self.on_return_to_launcher = on_return_to_launcher
        
        self._load_scores()
        self._load_settings()
        self._init_buttons()
        self._init_layer_specific()

    @abstractmethod
    def _init_layer_specific(self):
        """Initialize layer-specific UI elements. Override in subclasses."""
        pass

    @abstractmethod
    def _init_buttons(self):
        """
        Initialize all layer buttons.
        Must populate self.buttons dict.
        Override in subclasses for layer-specific actions.
        """
        # Base buttons that every layer should have
        self.buttons["play"] = UIButton(
            id="play",
            label="▶️ Play",
            category="action",
            action=self._action_play,
            help_text="Start new game session"
        )
        self.buttons["continue"] = UIButton(
            id="continue",
            label="↩️ Continue",
            category="action",
            action=self._action_continue,
            enabled=False,
            help_text="Resume previous game"
        )
        self.buttons["leaderboard"] = UIButton(
            id="leaderboard",
            label="🏆 Leaderboard",
            category="navigation",
            action=self._action_leaderboard,
            help_text="View top scores"
        )
        self.buttons["settings"] = UIButton(
            id="settings",
            label="⚙️ Settings",
            category="navigation",
            action=self._action_settings,
            help_text="Game settings"
        )
        self.buttons["back"] = UIButton(
            id="back",
            label="◀️ Back",
            category="navigation",
            action=self._action_back,
            help_text="Return to previous menu"
        )
        self.buttons["quit"] = UIButton(
            id="quit",
            label="❌ Quit",
            category="utility",
            action=self._action_quit,
            help_text="Exit this layer"
        )

    def _load_scores(self):
        """Load scores from disk."""
        scores_file = self.data_dir / "scores.json"
        if scores_file.exists():
            try:
                with open(scores_file, "r") as f:
                    scores_data = json.load(f)
                    self.scores = [GameScore(**s) for s in scores_data]
                logger.info(f"Loaded {len(self.scores)} scores for {self.layer_name}")
            except Exception as e:
                logger.error(f"Failed to load scores: {e}")

    def _save_scores(self):
        """Persist scores to disk."""
        scores_file = self.data_dir / "scores.json"
        try:
            with open(scores_file, "w") as f:
                json.dump([asdict(s) for s in self.scores], f, indent=2)
            logger.info(f"Saved {len(self.scores)} scores for {self.layer_name}")
        except Exception as e:
            logger.error(f"Failed to save scores: {e}")

    def _load_settings(self):
        """Load layer settings from disk."""
        settings_file = self.data_dir / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, "r") as f:
                    self.settings = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
        else:
            # Default settings every layer should have
            self.settings = {
                "difficulty": "medium",
                "volume": 0.8,
                "music_volume": 0.8,
                "sfx_volume": 0.8,
                "screen_shake": True,
                "fullscreen": False,
                "show_hints": True
            }

    def _save_settings(self):
        """Persist settings to disk."""
        settings_file = self.data_dir / "settings.json"
        try:
            with open(settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
            logger.info(f"Saved settings for {self.layer_name}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    # ─── Default action handlers ───────────────────────────────────────────────

    def _action_play(self):
        """Start new game session."""
        self.state.mode = UIMode.GAMEPLAY
        self.state.status_message = f"🎮 Starting {self.layer_name}..."
        logger.info(f"Play action on {self.layer_name}")

    def _action_continue(self):
        """Resume previous session."""
        self.state.mode = UIMode.GAMEPLAY
        self.state.status_message = f"↩️ Resuming {self.layer_name}..."
        logger.info(f"Continue action on {self.layer_name}")

    def _action_leaderboard(self):
        """Display leaderboard."""
        self.state.mode = UIMode.LEADERBOARD
        self.state.scroll_offset = 0
        self.state.status_message = f"🏆 {self.layer_name} Leaderboard"

    def _action_settings(self):
        """Open settings menu."""
        self.state.mode = UIMode.SETTINGS
        self.state.status_message = "⚙️ Settings"

    def _action_back(self):
        """Return to previous menu."""
        if self.state.mode == UIMode.MAIN_MENU:
            return
        self.state.mode = UIMode.MAIN_MENU
        self.state.selected_item_id = None
        self.state.status_message = f"🎵 {self.layer_name} Menu"

    def _action_quit(self):
        """Exit layer."""
        self.state.mode = UIMode.MAIN_MENU
        self.state.status_message = "Exiting..."
        logger.info(f"Quit {self.layer_name}")

    # ─── Console rendering ────────────────────────────────────────────────────

    def render_console_text(self) -> str:
        """Render console UI as formatted text."""
        lines = []
        lines.append(f"╔═══════════════════════════════════════════╗")
        lines.append(f"║  🎮 {self.layer_name.upper():35}  ║")
        lines.append(f"╠═══════════════════════════════════════════╣")
        
        # Mode & status
        mode_str = self.state.mode.value.upper().replace('_', ' ')
        lines.append(f"║ [{mode_str:<35}] ║")
        
        if self.state.error_message:
            lines.append(f"║ ❌ {self.state.error_message:<36} ║")
        elif self.state.progress_pct > 0 and self.state.progress_pct < 100:
            bar = "█" * (self.state.progress_pct // 5) + "░" * (20 - self.state.progress_pct // 5)
            lines.append(f"║ {bar} {self.state.progress_pct}%  ║")
        else:
            status = self.state.status_message[:39].ljust(39)
            lines.append(f"║ {status} ║")
        
        lines.append("╠═══════════════════════════════════════════╣")
        
        # Mode-specific content
        if self.state.mode == UIMode.MAIN_MENU:
            lines.extend(self._render_main_menu())
        elif self.state.mode == UIMode.LEADERBOARD:
            lines.extend(self._render_leaderboard())
        elif self.state.mode == UIMode.SETTINGS:
            lines.extend(self._render_settings())
        elif self.state.mode == UIMode.GAMEPLAY:
            lines.extend(self._render_gameplay())
        
        lines.append("║                                           ║")
        lines.append("╚═══════════════════════════════════════════╝")
        
        return "\n".join(lines)

    def _render_main_menu(self) -> List[str]:
        """Render main menu buttons."""
        lines = []
        action_buttons = [b for b in self.buttons.values() if b.category == "action"]
        nav_buttons = [b for b in self.buttons.values() if b.category == "navigation"]
        
        lines.append("║ ACTIONS:                                  ║")
        for btn in action_buttons:
            status = "✓" if btn.enabled else "✗"
            label = btn.label[:33].ljust(33)
            lines.append(f"║ [{status}] {label} ║")
        
        if nav_buttons:
            lines.append("╟───────────────────────────────────────────╢")
            lines.append("║ NAVIGATE:                                 ║")
            for btn in nav_buttons:
                label = btn.label[:35].ljust(35)
                lines.append(f"║  • {label} ║")
        
        return lines

    def _render_leaderboard(self) -> List[str]:
        """Render leaderboard display."""
        lines = []
        lines.append(f"║ TOP {min(UNITY, len(self.scores))} SCORES:                       ║")
        
        sorted_scores = sorted(self.scores, key=lambda s: s.score, reverse=True)
        for i, score in enumerate(sorted_scores[:UNITY]):
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
            score_str = f"{score.score:,}".rjust(6)
            player = score.player_id[:15].ljust(15)
            lines.append(f"║ {medal} {score_str} {player[:15]} ║")
        
        return lines

    def _render_settings(self) -> List[str]:
        """Render settings menu."""
        lines = []
        lines.append("║ SETTINGS:                                ║")
        for key, value in list(self.settings.items())[:5]:
            key_str = key.replace('_', ' ').title()
            val_str = str(value)[:25]
            lines.append(f"║  {key_str:<18} {val_str:>18} ║")
        
        return lines

    def _render_gameplay(self) -> List[str]:
        """Render gameplay screen. Override in subclasses."""
        return ["║ (Gameplay - override in subclass)         ║"]

    def get_state_json(self) -> Dict[str, Any]:
        """Get full UI state as JSON."""
        return {
            "layer_name": self.layer_name,
            "mode": self.state.mode.value,
            "status_message": self.state.status_message,
            "error_message": self.state.error_message,
            "progress_pct": self.state.progress_pct,
            "buttons": {
                btn_id: {
                    "label": btn.label,
                    "category": btn.category,
                    "enabled": btn.enabled,
                    "help_text": btn.help_text,
                    "icon": btn.icon,
                    "hotkey": btn.hotkey
                }
                for btn_id, btn in self.buttons.items()
            },
            "top_scores": [
                asdict(s) for s in sorted(
                    self.scores, key=lambda x: x.score, reverse=True
                )[:UNITY]
            ],
            "settings": self.settings
        }

    def execute_button(self, button_id: str) -> bool:
        """Execute button action by ID."""
        btn = self.buttons.get(button_id)
        if not btn or not btn.enabled:
            self.state.error_message = f"❌ Button '{button_id}' unavailable"
            return False
        
        try:
            btn.action()
            return True
        except Exception as e:
            self.state.error_message = f"❌ Error: {str(e)}"
            logger.error(f"Button execution error: {e}")
            return False

    def record_score(self, player_id: str, score: int, level: int, 
                    difficulty: str, metadata: Dict[str, Any] = None) -> GameScore:
        """Record a game score."""
        import uuid
        game_score = GameScore(
            player_id=player_id,
            score=score,
            level=level,
            difficulty=difficulty,
            timestamp=time.time(),
            session_id=str(uuid.uuid4())[:8],
            metadata=metadata or {}
        )
        self.scores.append(game_score)
        self._save_scores()
        
        self.state.status_message = f"✅ Score saved: {score} points!"
        return game_score

    def set_setting(self, key: str, value: Any):
        """Update a setting."""
        self.settings[key] = value
        self._save_settings()
        self.state.status_message = f"✅ {key} = {value}"

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)

    def show_error(self, message: str):
        """Display an error message."""
        self.state.error_message = f"❌ {message}"
        logger.error(message)

    def show_status(self, message: str):
        """Display a status message."""
        self.state.status_message = message
        self.state.error_message = None
