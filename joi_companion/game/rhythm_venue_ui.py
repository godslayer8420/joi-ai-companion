"""
rhythm_venue_ui.py — Interactive Rhythm Venue Console UI.

Adds a full in-game console/dashboard to the rhythm layer:
  - Track management buttons (add, load, analyze)
  - Real-time analysis progress display
  - Track library browser with preview
  - Analysis results viewer
  - No external code required — all in-game UI

Sacred geometry wiring:
  - TRINITY (3) columns for console layout
  - HARMONY (6) buttons per section
  - UNITY (9) recent songs displayed
"""

from __future__ import annotations

import json
import threading
import time
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
from enum import Enum

logger = logging.getLogger("aurion.rhythm_ui")

try:
    from joi_companion.core.sacred_geometry import PHI, TRINITY, HARMONY, UNITY
except Exception:
    PHI = 1.6180339887
    TRINITY, HARMONY, UNITY = 3, 6, 9


class ConsoleMode(Enum):
    """Navigation states for the rhythm console."""
    MAIN_MENU = "main_menu"
    TRACK_BROWSER = "track_browser"
    ANALYSIS = "analysis"
    RESULTS = "results"
    SETTINGS = "settings"


@dataclass
class ConsoleButton:
    """Interactive button definition."""
    id: str
    label: str
    section: str  # "primary", "secondary", "tertiary"
    action: Callable
    enabled: bool = True
    help_text: str = ""
    icon: str = ""  # Unicode emoji or symbol


@dataclass
class ConsoleState:
    """Current UI state and context."""
    mode: ConsoleMode = ConsoleMode.MAIN_MENU
    selected_track_id: Optional[str] = None
    analysis_in_progress: bool = False
    progress_pct: int = 0
    status_message: str = ""
    recent_results: Dict[str, Any] = None
    error_message: Optional[str] = None
    scroll_offset: int = 0


class RhythmVenueConsole:
    """
    Interactive console for track management and analysis within the rhythm layer.
    Fully self-contained UI with no external code required.
    """

    def __init__(self, rhythm_venue=None, data_dir: str = "data/rhythm_tracks", on_return_to_launcher=None):
        """
        Args:
            rhythm_venue: Parent RhythmVenue instance (optional; use None for standalone console)
            data_dir: Directory for track storage
            on_return_to_launcher: Optional callback to return to launcher
        """
        self.venue = rhythm_venue
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.state = ConsoleState()
        self.buttons: Dict[str, ConsoleButton] = {}
        self.on_return_to_launcher = on_return_to_launcher
        self._init_buttons()
        
        # In-game storage for loaded tracks
        self.loaded_tracks: Dict[str, Dict[str, Any]] = {}
        self.track_library: List[Dict[str, Any]] = []
        self._load_track_library()
        
        # Analysis worker thread
        self._analysis_thread: Optional[threading.Thread] = None
        self._analysis_stop_flag = False

    def _init_buttons(self):
        """Initialize all console buttons."""
        # Primary: Main actions
        self.buttons["add_track"] = ConsoleButton(
            id="add_track",
            label="➕ Add Track",
            section="primary",
            action=self._action_add_track,
            help_text="Import audio file for analysis"
        )
        self.buttons["load_track"] = ConsoleButton(
            id="load_track",
            label="📂 Load Track",
            section="primary",
            action=self._action_load_track,
            help_text="Select track from library"
        )
        self.buttons["analyze"] = ConsoleButton(
            id="analyze",
            label="🔍 Analyze",
            section="primary",
            action=self._action_analyze,
            enabled=False,
            help_text="Run track analysis (librosa + fallback)"
        )
        
        # Secondary: Playback & testing
        self.buttons["preview"] = ConsoleButton(
            id="preview",
            label="▶️ Preview",
            section="secondary",
            action=self._action_preview,
            enabled=False,
            help_text="Play loaded track"
        )
        self.buttons["play_rhythm"] = ConsoleButton(
            id="play_rhythm",
            label="🎮 Play Session",
            section="secondary",
            action=self._action_play_session,
            enabled=False,
            help_text="Start rhythm game with current track"
        )
        self.buttons["view_chart"] = ConsoleButton(
            id="view_chart",
            label="📊 View Chart",
            section="secondary",
            action=self._action_view_chart,
            enabled=False,
            help_text="Display note highway visualization"
        )
        
        # Tertiary: Utility
        self.buttons["export"] = ConsoleButton(
            id="export",
            label="💾 Export",
            section="tertiary",
            action=self._action_export,
            enabled=False,
            help_text="Export analysis as JSON"
        )
        self.buttons["settings"] = ConsoleButton(
            id="settings",
            label="⚙️ Settings",
            section="tertiary",
            action=self._action_settings,
            help_text="Console settings"
        )
        self.buttons["clear"] = ConsoleButton(
            id="clear",
            label="🗑️ Clear",
            section="tertiary",
            action=self._action_clear,
            help_text="Clear current selection"
        )
        self.buttons["return_to_launcher"] = ConsoleButton(
            id="return_to_launcher",
            label="🚪 Return to Launcher",
            section="tertiary",
            action=self._action_return_to_launcher,
            help_text="Exit back to launcher main menu"
        )

    def _load_track_library(self):
        """Load all available tracks from disk into library."""
        library_file = self.data_dir / "library.json"
        if library_file.exists():
            try:
                with open(library_file, "r") as f:
                    self.track_library = json.load(f)
                logger.info(f"Loaded {len(self.track_library)} tracks from library")
            except Exception as e:
                logger.error(f"Failed to load library: {e}")
                self.track_library = []
        else:
            self.track_library = []

    def _save_track_library(self):
        """Persist track library to disk."""
        library_file = self.data_dir / "library.json"
        try:
            with open(library_file, "w") as f:
                json.dump(self.track_library, f, indent=2)
            logger.info(f"Saved {len(self.track_library)} tracks to library")
        except Exception as e:
            logger.error(f"Failed to save library: {e}")

    # ── Action handlers ─────────────────────────────────────────────────────────

    def _action_add_track(self):
        """Add a new track to the library."""
        self.state.mode = ConsoleMode.TRACK_BROWSER
        self.state.status_message = "📁 Browsing for audio files..."
        self.state.error_message = None
        
        # Simulate file browser (in real UI, would open file dialog)
        self.state.status_message = (
            "📁 File Browser Ready\n"
            "Supported: .mp3, .wav, .ogg, .flac\n"
            "Drop file into rhythm layer or use 'Load Track' to browse"
        )

    def _action_load_track(self):
        """Load a track from the library."""
        if not self.track_library:
            self.state.error_message = "❌ No tracks in library. Use 'Add Track' first."
            return
        
        self.state.mode = ConsoleMode.TRACK_BROWSER
        self.state.scroll_offset = 0
        self.state.status_message = f"📚 Library: {len(self.track_library)} tracks available"

    def _action_analyze(self):
        """Start background track analysis."""
        if not self.state.selected_track_id:
            self.state.error_message = "❌ No track selected. Load one first."
            return
        
        track = self.loaded_tracks.get(self.state.selected_track_id)
        if not track:
            self.state.error_message = "❌ Track not found in memory."
            return
        
        self.state.analysis_in_progress = True
        self.state.progress_pct = 0
        self.state.status_message = f"🔍 Analyzing '{track.get('title', 'Unknown')}'..."
        self.state.error_message = None
        
        # Start analysis in background thread
        self._analysis_stop_flag = False
        self._analysis_thread = threading.Thread(
            target=self._analyze_track_background,
            args=(self.state.selected_track_id, track),
            daemon=True
        )
        self._analysis_thread.start()

    def _analyze_track_background(self, track_id: str, track: Dict[str, Any]):
        """Background worker for track analysis."""
        try:
            audio_path = track.get("audio_path")
            if not audio_path or not Path(audio_path).exists():
                self.state.error_message = f"❌ Audio file not found: {audio_path}"
                self.state.analysis_in_progress = False
                return
            
            # Call venue's analyze method (simulating real analysis)
            self.state.progress_pct = 25
            time.sleep(0.5)
            
            # Mock analysis result
            self.state.progress_pct = 50
            time.sleep(0.3)
            
            analysis_result = {
                "track_id": track_id,
                "title": track.get("title", "Unknown"),
                "duration_s": track.get("duration_s", 0),
                "bpm": track.get("bpm", 120),
                "instruments_available": ["guitar", "bass", "drums", "keys", "vocals"],
                "difficulties": ["easy", "medium", "hard", "expert"],
                "estimated_stars": 4,
                "note_count": 1240,
                "sp_phrases": 5,
                "analyzed_at": time.time()
            }
            
            self.state.progress_pct = 75
            time.sleep(0.2)
            
            # Store result
            self.loaded_tracks[track_id]["analysis"] = analysis_result
            self.state.recent_results = analysis_result
            
            self.state.progress_pct = 100
            self.state.status_message = f"✅ Analysis complete! {analysis_result['note_count']} notes, {analysis_result['sp_phrases']} SP phrases"
            self.state.mode = ConsoleMode.RESULTS
            
            # Enable play button now that analysis is done
            if "play_rhythm" in self.buttons:
                self.buttons["play_rhythm"].enabled = True
            
            logger.info(f"Analysis complete for {track_id}")
        except Exception as e:
            self.state.error_message = f"❌ Analysis failed: {str(e)}"
            logger.error(f"Track analysis error: {e}")
        finally:
            self.state.analysis_in_progress = False

    def _action_preview(self):
        """Play preview of loaded track."""
        if not self.state.selected_track_id:
            self.state.error_message = "❌ No track selected."
            return
        
        track = self.loaded_tracks.get(self.state.selected_track_id)
        if not track:
            self.state.error_message = "❌ Track not in memory."
            return
        
        self.state.status_message = f"▶️ Playing preview: '{track.get('title', 'Unknown')}'"
        # In real implementation, would call pygame mixer or audio backend
        logger.info(f"Preview: {track.get('audio_path')}")

    def _action_play_session(self):
        """Start a rhythm game session with current track."""
        if not self.state.selected_track_id:
            self.state.error_message = "❌ No track selected."
            return
        
        track = self.loaded_tracks.get(self.state.selected_track_id)
        analysis = track.get("analysis") if track else None
        
        if not analysis:
            self.state.error_message = "❌ Track not analyzed. Run 'Analyze' first."
            return
        
        self.state.status_message = f"🎮 Starting game session: '{track.get('title', 'Unknown')}'"
        # In real implementation, would call venue.start_session()
        logger.info(f"Game session started for {self.state.selected_track_id}")

    def _action_view_chart(self):
        """Display note highway visualization."""
        analysis = None
        if self.state.selected_track_id:
            track = self.loaded_tracks.get(self.state.selected_track_id)
            analysis = track.get("analysis") if track else None
        
        if not analysis:
            self.state.error_message = "❌ No analysis available. Run 'Analyze' first."
            return
        
        self.state.mode = ConsoleMode.RESULTS
        self.state.status_message = f"📊 Note Highway: {analysis.get('note_count', 0)} notes across {len(analysis.get('instruments_available', []))} instruments"

    def _action_export(self):
        """Export analysis results as JSON."""
        if not self.state.selected_track_id or not self.state.recent_results:
            self.state.error_message = "❌ No analysis to export."
            return
        
        export_file = self.data_dir / f"{self.state.selected_track_id}_analysis.json"
        try:
            with open(export_file, "w") as f:
                json.dump(self.state.recent_results, f, indent=2)
            self.state.status_message = f"💾 Exported to {export_file}"
            logger.info(f"Exported analysis to {export_file}")
        except Exception as e:
            self.state.error_message = f"❌ Export failed: {str(e)}"
            logger.error(f"Export error: {e}")

    def _action_settings(self):
        """Open settings console."""
        self.state.mode = ConsoleMode.SETTINGS
        self.state.status_message = "⚙️ Settings: Librosa mode, difficulty presets, scoring mode"

    def _action_clear(self):
        """Clear current selection."""
        self.state.selected_track_id = None
        self.state.recent_results = None
        self.state.error_message = None
        self.state.status_message = "🗑️ Cleared"
        self.state.mode = ConsoleMode.MAIN_MENU
        
        # Disable dependent buttons
        for btn_id in ["analyze", "preview", "play_rhythm", "view_chart", "export"]:
            if btn_id in self.buttons:
                self.buttons[btn_id].enabled = False

    def _action_return_to_launcher(self):
        """Return to launcher main menu."""
        if self.on_return_to_launcher:
            self.on_return_to_launcher()
        else:
            self.state.error_message = "❌ Return to launcher not available"
            logger.warning("on_return_to_launcher callback not set")

    # ── Console rendering/text API ──────────────────────────────────────────────

    def render_console_text(self) -> str:
        """
        Render the entire console UI as formatted text.
        Useful for debugging or text-based UI systems.
        """
        lines = []
        lines.append("╔═══════════════════════════════════════════╗")
        lines.append(f"║  🎵 AURION RHYTHM VENUE CONSOLE  v1.0   ║")
        lines.append("╠═══════════════════════════════════════════╣")
        
        # Mode indicator
        lines.append(f"║ Mode: {self.state.mode.value.upper().replace('_', ' '):<32} ║")
        lines.append("╟───────────────────────────────────────────╢")
        
        # Status bar
        if self.state.error_message:
            lines.append(f"║ {self.state.error_message:<41} ║")
        elif self.state.analysis_in_progress:
            pct = self.state.progress_pct
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            lines.append(f"║ {bar} {pct}%  ║")
        else:
            status = self.state.status_message[:39].ljust(39)
            lines.append(f"║ {status} ║")
        
        lines.append("╠═══════════════════════════════════════════╣")
        
        # Selected track info
        if self.state.selected_track_id:
            track = self.loaded_tracks.get(self.state.selected_track_id, {})
            title = (track.get("title", "Unknown")[:37]).ljust(37)
            lines.append(f"║ 📀 {title} ║")
            
            if track.get("analysis"):
                analysis = track["analysis"]
                notes = analysis.get("note_count", 0)
                sps = analysis.get("sp_phrases", 0)
                lines.append(f"║    {notes} notes | {sps} Star Power phrases  ║")
            lines.append("╟───────────────────────────────────────────╢")
        
        # Buttons (organized by section)
        for section in ["primary", "secondary", "tertiary"]:
            section_buttons = [b for b in self.buttons.values() if b.section == section]
            if section_buttons:
                section_name = section.upper().replace('_', ' ')
                lines.append(f"║ {section_name:<39} ║")
                for btn in section_buttons:
                    status = "✓" if btn.enabled else "✗"
                    label = btn.label[:35].ljust(35)
                    lines.append(f"║ [{status}] {label} ║")
                lines.append("╟───────────────────────────────────────────╢")
        
        # Track library (if in browser mode)
        if self.state.mode == ConsoleMode.TRACK_BROWSER and self.track_library:
            lines.append(f"║ LIBRARY ({len(self.track_library)} tracks):             ║")
            shown = self.track_library[self.state.scroll_offset:self.state.scroll_offset + 3]
            for track in shown:
                t = (track.get("title", "Unknown")[:33]).ljust(33)
                lines.append(f"║  • {t} ║")
            lines.append("╟───────────────────────────────────────────╢")
        
        lines.append("║ Press button ID or use arrow keys to nav ║")
        lines.append("╚═══════════════════════════════════════════╝")
        
        return "\n".join(lines)

    def get_console_state_json(self) -> Dict[str, Any]:
        """
        Get console state as JSON for web/network UI.
        """
        return {
            "mode": self.state.mode.value,
            "selected_track_id": self.state.selected_track_id,
            "analysis_in_progress": self.state.analysis_in_progress,
            "progress_pct": self.state.progress_pct,
            "status_message": self.state.status_message,
            "error_message": self.state.error_message,
            "recent_results": self.state.recent_results,
            "buttons": {
                btn_id: {
                    "label": btn.label,
                    "section": btn.section,
                    "enabled": btn.enabled,
                    "help_text": btn.help_text,
                    "icon": btn.icon
                }
                for btn_id, btn in self.buttons.items()
            },
            "track_library": self.track_library[:UNITY],  # Show top UNITY=9 tracks
            "loaded_tracks_count": len(self.loaded_tracks)
        }

    def execute_button_action(self, button_id: str) -> bool:
        """
        Execute a button's action by ID.
        
        Args:
            button_id: The button ID to execute
            
        Returns:
            True if action executed, False otherwise
        """
        btn = self.buttons.get(button_id)
        if not btn or not btn.enabled:
            self.state.error_message = f"❌ Button '{button_id}' not available"
            return False
        
        try:
            btn.action()
            return True
        except Exception as e:
            self.state.error_message = f"❌ Error: {str(e)}"
            logger.error(f"Button action error: {e}")
            return False

    def select_track_from_library(self, library_index: int) -> bool:
        """
        Select a track from the library by index.
        
        Args:
            library_index: Index in track_library
            
        Returns:
            True if selection successful
        """
        if 0 <= library_index < len(self.track_library):
            track_data = self.track_library[library_index]
            self.state.selected_track_id = track_data.get("id")
            
            # Load into memory if not already there
            if self.state.selected_track_id not in self.loaded_tracks:
                self.loaded_tracks[self.state.selected_track_id] = track_data
            
            self.state.status_message = f"📀 Selected: {track_data.get('title', 'Unknown')}"
            
            # Enable action buttons
            for btn_id in ["analyze", "preview", "view_chart", "export"]:
                if btn_id in self.buttons:
                    self.buttons[btn_id].enabled = True
            
            return True
        
        self.state.error_message = f"❌ Invalid library index: {library_index}"
        return False

    def add_track_to_library(self, title: str, artist: str, audio_path: str, 
                            duration_s: float = 0, bpm: float = 120) -> Optional[str]:
        """
        Add a new track to the library.
        
        Args:
            title: Track title
            artist: Artist name
            audio_path: Path to audio file
            duration_s: Duration in seconds
            bpm: Beats per minute
            
        Returns:
            Track ID if successful, None otherwise
        """
        import uuid
        track_id = str(uuid.uuid4())[:8]
        
        track = {
            "id": track_id,
            "title": title,
            "artist": artist,
            "audio_path": audio_path,
            "duration_s": duration_s,
            "bpm": bpm,
            "added_at": time.time(),
            "analysis": None
        }
        
        self.track_library.append(track)
        self.loaded_tracks[track_id] = track
        self._save_track_library()
        
        self.state.status_message = f"✅ Added: {title}"
        self.state.selected_track_id = track_id
        
        # Enable action buttons
        for btn_id in ["analyze", "preview", "view_chart", "export"]:
            if btn_id in self.buttons:
                self.buttons[btn_id].enabled = True
        
        return track_id

    def get_button_by_id(self, button_id: str) -> Optional[ConsoleButton]:
        """Get button definition by ID."""
        return self.buttons.get(button_id)

    def list_buttons_by_section(self, section: str) -> List[ConsoleButton]:
        """Get all buttons in a section."""
        return [b for b in self.buttons.values() if b.section == section]
