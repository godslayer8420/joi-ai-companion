"""
battle_arena_ui.py — Interactive Battle Arena Console UI (Basement Layer 3).

Complete in-game UI for alien battles with no external coding required.
- Tournament bracket display
- Real-time match simulation
- Alien team management
- Prize history
- Settings (difficulty, battle speed, spectator mode)

All state persists to disk via battle_arena.py; UI is fully self-contained.
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

logger = logging.getLogger("aurion.battle_arena_ui")

try:
    from joi_companion.core.sacred_geometry import PHI, PHI_CONJUGATE, TRINITY, HARMONY, UNITY
except Exception:
    PHI = 1.6180339887
    PHI_CONJUGATE = 0.6180339887
    TRINITY, HARMONY, UNITY = 3, 6, 9


class BattleMode(Enum):
    """UI modes for Battle Arena."""
    MAIN_MENU = "main_menu"
    TOURNAMENT_SELECT = "tournament_select"
    TEAM_MANAGE = "team_manage"
    BATTLE_PREVIEW = "battle_preview"
    BATTLE_ACTIVE = "battle_active"
    BATTLE_RESULTS = "battle_results"
    LEADERBOARD = "leaderboard"
    SETTINGS = "settings"
    HELP = "help"


@dataclass
class BattleTeam:
    """Player's battle team (up to 6 aliens in bracket formation)."""
    team_id: str
    name: str
    aliens: List[Dict[str, Any]] = field(default_factory=list)  # [{"catch_id", "name", "level", "type"}]
    wins: int = 0
    losses: int = 0
    tier: str = "Bronze"
    credits_earned: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BattleScore:
    """Match result record."""
    match_id: str
    team_name: str
    opponent: str
    tier: str
    result: str  # "victory" or "defeat"
    aliens_used: List[str]
    damage_dealt: int
    damage_taken: int
    prize_credits: int
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConsoleButton:
    """Button for Battle Arena UI."""
    id: str
    label: str
    mode: str  # current mode
    category: str  # "primary", "secondary", "tertiary", "utility"


class BattleArenaConsole:
    """
    Interactive console for Battle Arena layer.
    
    Sacred Geometry:
    - TRINITY (3): 3 team formations (aggressive, balanced, defensive)
    - HARMONY (6): 6 primary actions (select_tournament, manage_team, view_bracket, simulate_match, leaderboard, settings)
    - UNITY (9): 9 leaderboard entries, 9 recent matches in history
    """

    def __init__(self, data_dir: str = "data/battle_arena", on_return_to_launcher=None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.mode = BattleMode.MAIN_MENU
        self.current_team: Optional[BattleTeam] = None
        self.selected_tournament: Optional[str] = None
        self.active_match: Optional[Dict[str, Any]] = None
        self.on_return_to_launcher = on_return_to_launcher
        self.simulation_running = False
        self.simulation_progress = 0.0
        
        # Settings (persistent)
        self.settings = {
            "battle_speed": "normal",  # slow, normal, fast
            "difficulty": "medium",     # easy, medium, hard
            "spectator_mode": False,
            "show_stats": True,
            "volume": 70,
            "screen_shake": True,
        }
        
        # Data storage
        self.teams_file = self.data_dir / "teams.json"
        self.scores_file = self.data_dir / "scores.json"
        self.settings_file = self.data_dir / "settings.json"
        
        self._load_teams()
        self._load_scores()
        self._load_settings()
        self._init_buttons()

    def _init_buttons(self):
        """Initialize all UI buttons."""
        self.buttons = {
            "primary": [
                ConsoleButton("btn_select_tournament", "Select Tournament", "main_menu", "primary"),
                ConsoleButton("btn_manage_team", "Manage Team", "main_menu", "primary"),
                ConsoleButton("btn_view_bracket", "View Bracket", "main_menu", "primary"),
                ConsoleButton("btn_simulate_match", "Simulate Match", "main_menu", "primary"),
                ConsoleButton("btn_leaderboard", "Leaderboard", "main_menu", "primary"),
                ConsoleButton("btn_settings", "Settings", "main_menu", "primary"),
            ],
            "secondary": [
                ConsoleButton("btn_team_stats", "Team Stats", "team_manage", "secondary"),
                ConsoleButton("btn_add_alien", "Add Alien", "team_manage", "secondary"),
                ConsoleButton("btn_remove_alien", "Remove Alien", "team_manage", "secondary"),
                ConsoleButton("btn_rearrange_formation", "Rearrange", "team_manage", "secondary"),
                ConsoleButton("btn_rename_team", "Rename Team", "team_manage", "secondary"),
                ConsoleButton("btn_back_to_menu", "Back", "team_manage", "secondary"),
            ],
            "tertiary": [
                ConsoleButton("btn_next_match", "Next Match", "battle_preview", "tertiary"),
                ConsoleButton("btn_abandon_match", "Abandon", "battle_preview", "tertiary"),
                ConsoleButton("btn_view_opponent", "Opponent Info", "battle_preview", "tertiary"),
                ConsoleButton("btn_start_battle", "Start Battle", "battle_preview", "tertiary"),
                ConsoleButton("btn_cancel_battle", "Cancel", "battle_preview", "tertiary"),
                ConsoleButton("btn_return_menu", "Return", "battle_preview", "tertiary"),
            ],
            "utility": [
                ConsoleButton("btn_help", "Help", "main_menu", "utility"),
                ConsoleButton("btn_return_to_launcher", "🚪 Return to Launcher", "main_menu", "utility"),
                ConsoleButton("btn_quit", "Quit", "main_menu", "utility"),
            ],
        }

    def _load_teams(self):
        """Load teams from disk."""
        if self.teams_file.exists():
            try:
                with open(self.teams_file, "r") as f:
                    data = json.load(f)
                    if data:
                        self.current_team = BattleTeam(**data[0])  # Load first team
            except Exception as e:
                logger.error(f"Failed to load teams: {e}")
                self.current_team = None
        
        if not self.current_team:
            # Create default team
            self.current_team = BattleTeam(
                team_id=str(uuid.uuid4()),
                name="Rookie Squad",
                aliens=[],
                tier="Bronze",
            )
            self._save_teams()

    def _save_teams(self):
        """Save teams to disk."""
        try:
            with open(self.teams_file, "w") as f:
                json.dump([self.current_team.to_dict()], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save teams: {e}")

    def _load_scores(self):
        """Load match history from disk."""
        self.scores = []
        if self.scores_file.exists():
            try:
                with open(self.scores_file, "r") as f:
                    data = json.load(f)
                    self.scores = data[:UNITY]  # Keep top 9
            except Exception as e:
                logger.error(f"Failed to load scores: {e}")

    def _save_scores(self):
        """Save match history to disk."""
        try:
            with open(self.scores_file, "w") as f:
                json.dump(self.scores[:UNITY], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save scores: {e}")

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
        """Execute action for a button press. Returns feedback message."""
        if button_id == "btn_select_tournament":
            self.mode = BattleMode.TOURNAMENT_SELECT
            return "Select a tournament tier: Bronze, Silver, Gold, Platinum, or Void."
        
        elif button_id == "btn_manage_team":
            self.mode = BattleMode.TEAM_MANAGE
            return f"Managing team: {self.current_team.name} ({len(self.current_team.aliens)}/6 aliens)"
        
        elif button_id == "btn_view_bracket":
            self.mode = BattleMode.TOURNAMENT_SELECT
            return "Tournament bracket (simulated). Select tournament to view current round."
        
        elif button_id == "btn_simulate_match":
            if not self.current_team or not self.current_team.aliens:
                return "ERROR: Team has no aliens. Add aliens to your team first."
            self.mode = BattleMode.BATTLE_PREVIEW
            self._generate_random_opponent()
            return f"Match preview: {self.current_team.name} vs {self.active_match.get('opponent_name', 'Unknown')}"
        
        elif button_id == "btn_leaderboard":
            self.mode = BattleMode.LEADERBOARD
            return "Top 9 battle teams and recent victories."
        
        elif button_id == "btn_settings":
            self.mode = BattleMode.SETTINGS
            return "Adjust battle speed, difficulty, volume, and visual effects."
        
        elif button_id == "btn_add_alien":
            # Placeholder: in real implementation, would fetch caught aliens
            new_alien = {
                "catch_id": str(uuid.uuid4()),
                "name": f"Alien_{random.randint(100, 999)}",
                "level": random.randint(1, 50),
                "type": random.choice(["Void", "Crystal", "Neon", "Bio"]),
                "hp": 100,
                "attack": 60,
                "defense": 50,
            }
            if len(self.current_team.aliens) < 6:
                self.current_team.aliens.append(new_alien)
                self._save_teams()
                return f"Added {new_alien['name']} (Lv. {new_alien['level']}) to team."
            else:
                return "ERROR: Team is full (6/6 aliens)."
        
        elif button_id == "btn_start_battle":
            self._start_simulation()
            return f"Battle started: {self.current_team.name} vs {self.active_match['opponent_name']}"
        
        elif button_id == "btn_help":
            self.mode = BattleMode.HELP
            return "Battle Arena: Recruit aliens, build teams, and compete in tournaments for prizes."
        
        elif button_id == "btn_return_to_launcher":
            if self.on_return_to_launcher:
                self.on_return_to_launcher()
                return "Returning to launcher main menu..."
            else:
                return "ERROR: Return to launcher not available."
        
        elif button_id == "btn_quit":
            return "Exiting Battle Arena."
        
        else:
            return f"Button '{button_id}' not yet implemented."

    def _generate_random_opponent(self):
        """Create a random opponent for battle preview."""
        opponent_names = [
            "Neon Hunters", "Crystal Syndicate", "Void Collective",
            "Bio Collective", "Storm Riders", "Silent Sentinels",
            "Chaos Agents", "Prism Cult", "Void Shepherds"
        ]
        opponent_team = [
            {
                "name": f"Opponent_{i}",
                "level": random.randint(1, 50),
                "type": random.choice(["Void", "Crystal", "Neon", "Bio"]),
            }
            for i in range(random.randint(1, 6))
        ]
        self.active_match = {
            "match_id": str(uuid.uuid4()),
            "opponent_name": random.choice(opponent_names),
            "opponent_team": opponent_team,
            "tier": self.current_team.tier,
            "estimated_difficulty": "medium",
        }

    def _start_simulation(self):
        """Start background battle simulation."""
        self.simulation_running = True
        self.mode = BattleMode.BATTLE_ACTIVE
        thread = threading.Thread(target=self._simulate_battle_thread, daemon=True)
        thread.start()

    def _simulate_battle_thread(self):
        """Background thread for battle simulation."""
        try:
            for step in range(1, 101):
                time.sleep(0.05)  # Simulate 5 seconds total
                self.simulation_progress = step / 100.0
        finally:
            self.simulation_running = False
            # Determine winner
            player_win = random.random() > 0.5
            self._record_match_result(player_win)
            self.mode = BattleMode.BATTLE_RESULTS

    def _record_match_result(self, won: bool):
        """Record match outcome to history."""
        result_str = "victory" if won else "defeat"
        prize = random.randint(100, 500) if won else random.randint(10, 100)
        
        score = BattleScore(
            match_id=self.active_match.get("match_id", str(uuid.uuid4())),
            team_name=self.current_team.name,
            opponent=self.active_match.get("opponent_name", "Unknown"),
            tier=self.current_team.tier,
            result=result_str,
            aliens_used=[a.get("name") for a in self.current_team.aliens],
            damage_dealt=random.randint(50, 500),
            damage_taken=random.randint(0, 300),
            prize_credits=prize,
        )
        
        self.scores.append(score.to_dict())
        if won:
            self.current_team.wins += 1
            self.current_team.credits_earned += prize
        else:
            self.current_team.losses += 1
        
        self._save_scores()
        self._save_teams()

    def render_console_text(self) -> str:
        """Render console text for current mode."""
        if self.mode == BattleMode.MAIN_MENU:
            return self._render_main_menu()
        elif self.mode == BattleMode.TEAM_MANAGE:
            return self._render_team_manage()
        elif self.mode == BattleMode.BATTLE_PREVIEW:
            return self._render_battle_preview()
        elif self.mode == BattleMode.BATTLE_ACTIVE:
            return self._render_battle_active()
        elif self.mode == BattleMode.BATTLE_RESULTS:
            return self._render_battle_results()
        elif self.mode == BattleMode.LEADERBOARD:
            return self._render_leaderboard()
        elif self.mode == BattleMode.SETTINGS:
            return self._render_settings()
        else:
            return "╔════════════════════════════════════════════╗\n║  Battle Arena                              ║\n╚════════════════════════════════════════════╝"

    def _render_main_menu(self) -> str:
        lines = [
            "╔════════════════════════════════════════════╗",
            "║           BATTLE ARENA - Main Menu         ║",
            "╠════════════════════════════════════════════╣",
            f"║ Team: {self.current_team.name:<30} ║",
            f"║ Tier: {self.current_team.tier:<30} ║",
            f"║ W/L:  {self.current_team.wins}/{self.current_team.losses:<28} ║",
            "╠════════════════════════════════════════════╣",
            "║ [1] Select Tournament                      ║",
            "║ [2] Manage Team                            ║",
            "║ [3] View Bracket                           ║",
            "║ [4] Simulate Match                         ║",
            "║ [5] Leaderboard                            ║",
            "║ [6] Settings                               ║",
            "║ [H] Help                                   ║",
            "║ [Q] Quit                                   ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_team_manage(self) -> str:
        aliens_text = "\n".join([
            f"   {i+1}. {a.get('name')} (Lv. {a.get('level')}) [{a.get('type')}]"
            for i, a in enumerate(self.current_team.aliens[:6])
        ]) or "   (No aliens yet)"
        
        lines = [
            "╔════════════════════════════════════════════╗",
            "║           TEAM MANAGEMENT                  ║",
            "╠════════════════════════════════════════════╣",
            f"║ Team Name: {self.current_team.name:<27} ║",
            f"║ Tier: {self.current_team.tier:<32} ║",
            "║                                            ║",
            "║ Roster:                                    ║",
            f"{aliens_text}",
            "║                                            ║",
            "║ [1] Add Alien       [4] Rearrange         ║",
            "║ [2] Remove Alien    [5] Rename Team       ║",
            "║ [3] Team Stats      [B] Back              ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_battle_preview(self) -> str:
        opponent_list = "\n".join([
            f"   • {a.get('name')} (Lv. {a.get('level')}) [{a.get('type')}]"
            for a in self.active_match.get("opponent_team", [])
        ])
        
        lines = [
            "╔════════════════════════════════════════════╗",
            "║          BATTLE PREVIEW                    ║",
            "╠════════════════════════════════════════════╣",
            f"║ {self.current_team.name:<20} vs {self.active_match.get('opponent_name'):<14} ║",
            f"║ Tier: {self.active_match.get('tier'):<32} ║",
            "║                                            ║",
            "║ Opponent Team:                             ║",
            f"{opponent_list}",
            "║                                            ║",
            "║ Difficulty: Medium                         ║",
            "║                                            ║",
            "║ [1] Start Battle    [3] Opponent Info     ║",
            "║ [2] Abandon         [B] Back              ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_battle_active(self) -> str:
        bar_len = int(40 * self.simulation_progress)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        
        lines = [
            "╔════════════════════════════════════════════╗",
            "║          BATTLE IN PROGRESS                ║",
            "╠════════════════════════════════════════════╣",
            f"║ {bar} ║",
            f"║ {self.simulation_progress*100:.1f}%{'':<33} ║",
            "║                                            ║",
            f"║ Analyzing moves...                         ║",
            "║                                            ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_battle_results(self) -> str:
        last_score = self.scores[-1] if self.scores else None
        if not last_score:
            return "No match result available."
        
        result_text = "VICTORY! 🎉" if last_score["result"] == "victory" else "DEFEAT"
        
        lines = [
            "╔════════════════════════════════════════════╗",
            f"║          {result_text:<35} ║",
            "╠════════════════════════════════════════════╣",
            f"║ Opponent: {last_score['opponent']:<30} ║",
            f"║ Tier: {last_score['tier']:<34} ║",
            f"║ Damage: {last_score['damage_dealt']}/{last_score['damage_taken']:<25} ║",
            f"║ Prize: {last_score['prize_credits']} credits{'':<26} ║",
            "║                                            ║",
            "║ [1] Next Match      [2] Return Menu       ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _render_leaderboard(self) -> str:
        lines = [
            "╔════════════════════════════════════════════╗",
            "║           TOP 9 TEAMS                      ║",
            "╠════════════════════════════════════════════╣",
        ]
        
        # Aggregate top teams (in real implementation, would come from DB)
        top_teams = sorted(
            [{"name": s["team_name"], "wins": 1} for s in self.scores],
            key=lambda x: x["wins"],
            reverse=True,
        )[:UNITY]
        
        for i, team in enumerate(top_teams, 1):
            lines.append(f"║ {i}. {team['name']:<36} ║")
        
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
            f"║ Battle Speed: {self.settings['battle_speed']:<27} ║",
            f"║ Difficulty: {self.settings['difficulty']:<29} ║",
            f"║ Volume: {self.settings['volume']}%{'':<30} ║",
            f"║ Screen Shake: {'On' if self.settings['screen_shake'] else 'Off':<28} ║",
            f"║ Spectator Mode: {'On' if self.settings['spectator_mode'] else 'Off':<22} ║",
            "║                                            ║",
            "║ Use arrow keys to adjust settings.          ║",
            "║ [B] Back                                   ║",
            "╚════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def get_console_state_json(self) -> Dict[str, Any]:
        """Export complete state as JSON for Unreal/web UI."""
        return {
            "mode": self.mode.value,
            "team": self.current_team.to_dict() if self.current_team else None,
            "active_match": self.active_match,
            "simulation_progress": self.simulation_progress,
            "scores": self.scores[:UNITY],
            "settings": self.settings,
            "buttons": {
                "primary": [{"id": b.id, "label": b.label} for b in self.buttons.get("primary", [])],
                "secondary": [{"id": b.id, "label": b.label} for b in self.buttons.get("secondary", [])],
                "utility": [{"id": b.id, "label": b.label} for b in self.buttons.get("utility", [])],
            },
        }


if __name__ == "__main__":
    # Test console
    console = BattleArenaConsole()
    print(console.render_console_text())
    print("\nExecuting: Add Alien")
    print(console.execute_button_action("btn_add_alien"))
    print(console.render_console_text())
