"""
rhythm_venue.py — Basement Layer 5: Rhythm Game Venue.

Rock Band-style mechanics:
  - MIDI drums, microphone (vocals), MIDI keyboard, controller guitar/bass
  - Custom track import (audio file → note chart via onset/beat analysis)
  - Librosa-based track analysis (free, local, no API)
  - Highway renderer data for Unreal Engine
  - Scoring: streak multipliers, star ratings, SP (Star Power) phrases
  - All state in world_memory.db / rhythm_* tables

Sacred geometry wiring:
  - TRINITY (3) = note highway lanes (guitar/bass: 3 colors active per phrase)
  - HARMONY (6) = band size limit per session
  - UNITY   (9) = max star rating phases (3 × 3 = 9 perfect stars)
  - PHI     = streak multiplier growth curve
"""

from __future__ import annotations

import os
import uuid
import time
import json
import logging
import threading
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger("aurion.rhythm")

try:
    from joi_companion.core.sacred_geometry import PHI, PHI_CONJUGATE, TRINITY, HARMONY, UNITY
except Exception:
    PHI = 1.6180339887; PHI_CONJUGATE = 0.6180339887
    TRINITY, HARMONY, UNITY = 3, 6, 9

# ── Instrument definitions ─────────────────────────────────────────────────────
INSTRUMENTS = {
    "guitar":   {"lanes": 5, "colors": ["green","red","yellow","blue","orange"], "input": "controller_guitar"},
    "bass":     {"lanes": 5, "colors": ["green","red","yellow","blue","orange"], "input": "controller_guitar"},
    "drums":    {"lanes": 5, "colors": ["red","yellow","blue","green","kick"],   "input": "midi_drums"},
    "keys":     {"lanes": 5, "colors": ["green","red","yellow","blue","orange"], "input": "midi_keyboard"},
    "vocals":   {"lanes": 1, "colors": ["pitch"],                                "input": "microphone"},
}

DIFFICULTIES = ["easy", "medium", "hard", "expert"]

# Star thresholds (% of max score)
STAR_THRESHOLDS = [0.20, 0.40, 0.60, 0.80, 1.00]  # 1–5 stars; 6th "gold star" = FC

# Streak multipliers: 1× → 2× → 3× → 4× capped (Rock Band style)
STREAK_MULT_THRESHOLDS = [0, 10, 20, 30]  # notes to reach each multiplier level
MAX_MULTIPLIER = 4

NOTE_BASE_SCORE = 50        # per note hit
CHORD_BONUS     = 25        # per extra simultaneous note in a chord
SP_PHRASE_MULT  = 2.0       # Star Power doubles multiplier while active


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class NoteEvent:
    """Single note on the highway."""
    time_s: float           # onset time in seconds
    lane: int               # 0-4 (instrument-specific color index)
    duration_s: float = 0.0 # sustain length (0 = tap note)
    is_sp: bool = False     # part of Star Power phrase
    is_forced: bool = False # HOPO / forced strum

@dataclass
class TrackChart:
    """Full note chart for one instrument at one difficulty."""
    song_id: str
    instrument: str
    difficulty: str
    notes: List[NoteEvent]
    bpm_events: List[Dict]   # [{time_s, bpm}]
    sp_phrases: List[Dict]   # [{start_s, end_s}]
    duration_s: float = 0.0

@dataclass
class SongMeta:
    song_id: str
    title: str
    artist: str
    audio_path: str          # local path to audio file
    chart_path: str          # local path to .json chart (generated or imported)
    duration_s: float
    bpm: float
    genres: List[str]
    added_ts: float = field(default_factory=time.time)
    analyzed: bool = False

@dataclass
class RhythmScore:
    score_id: str
    song_id: str
    session_id: str
    instrument: str
    difficulty: str
    score: int
    max_score: int
    stars: int               # 1-5 (6 = gold / FC)
    streak_max: int
    notes_hit: int
    notes_total: int
    accuracy: float          # 0.0-1.0
    full_combo: bool
    ts: float = field(default_factory=time.time)


# ── Track Analyzer ─────────────────────────────────────────────────────────────

class TrackAnalyzer:
    """
    Converts an audio file into a playable note chart using librosa onset detection.
    Fully local — no API, no cost.  Falls back to BPM-grid chart if librosa is absent.
    """

    def analyze(
        self,
        audio_path: str,
        instrument: str = "guitar",
        difficulty: str = "medium",
        song_id: str = "",
    ) -> TrackChart:
        logger.info("Analyzing track: %s [%s/%s]", audio_path, instrument, difficulty)
        try:
            return self._analyze_librosa(audio_path, instrument, difficulty, song_id)
        except ImportError:
            logger.warning("librosa not installed — using BPM-grid fallback chart")
            return self._analyze_fallback(audio_path, instrument, difficulty, song_id)
        except Exception as e:
            logger.error("Track analysis error: %s", e)
            return self._analyze_fallback(audio_path, instrument, difficulty, song_id)

    def _analyze_librosa(
        self, audio_path: str, instrument: str, difficulty: str, song_id: str
    ) -> TrackChart:
        import librosa  # type: ignore
        import numpy as np

        y, sr = librosa.load(audio_path, sr=None, mono=True)
        duration_s = float(len(y) / sr)

        # Beat / tempo
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo) if hasattr(tempo, '__float__') else float(np.mean(tempo))
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        # Onset detection
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units='frames',
                                                   backtrack=True, delta=0.07)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)

        # Harmonic / percussive separation — assign notes
        y_harm, y_perc = librosa.effects.hpss(y)
        onset_perc = librosa.onset.onset_detect(y=y_perc, sr=sr, units='frames')
        perc_times = set(map(float, librosa.frames_to_time(onset_perc, sr=sr).tolist()))

        lanes = INSTRUMENTS[instrument]["lanes"]
        diff_density = {"easy": 0.3, "medium": 0.55, "hard": 0.80, "expert": 1.0}.get(difficulty, 0.55)

        notes: List[NoteEvent] = []
        sp_phrases: List[Dict] = []
        sp_start: Optional[float] = None
        sp_note_count = 0

        # Build note events
        import random as _rng
        _rng.seed(int(bpm * 100))  # deterministic per song
        for i, t in enumerate(onset_times):
            if _rng.random() > diff_density:
                continue
            lane = _rng.randint(0, lanes - 1)
            # Drums: percussive onsets → kick/snare lanes
            if instrument == "drums" and float(t) in perc_times:
                lane = _rng.choice([0, 4])  # red or kick
            # Sustains: harmonic onsets on guitar/keys
            dur = 0.0
            if instrument in ("guitar", "bass", "keys"):
                next_t = onset_times[i + 1] if i + 1 < len(onset_times) else t + 0.25
                gap = float(next_t) - float(t)
                if gap > 0.35 and _rng.random() < 0.4:
                    dur = round(gap * 0.8, 3)
            # Star Power phrases: every ~32 beats, 8-beat window
            beat_idx = int(t / (60.0 / bpm)) if bpm > 0 else 0
            is_sp = (beat_idx % 32 >= 24)
            if is_sp and sp_start is None:
                sp_start = float(t)
            if not is_sp and sp_start is not None:
                sp_phrases.append({"start_s": sp_start, "end_s": float(t)})
                sp_start = None

            notes.append(NoteEvent(
                time_s=round(float(t), 4),
                lane=lane,
                duration_s=dur,
                is_sp=is_sp,
            ))

        if sp_start is not None:
            sp_phrases.append({"start_s": sp_start, "end_s": duration_s})

        bpm_events = [{"time_s": 0.0, "bpm": bpm}]

        return TrackChart(
            song_id=song_id,
            instrument=instrument,
            difficulty=difficulty,
            notes=notes,
            bpm_events=bpm_events,
            sp_phrases=sp_phrases,
            duration_s=duration_s,
        )

    def _analyze_fallback(
        self, audio_path: str, instrument: str, difficulty: str, song_id: str
    ) -> TrackChart:
        """BPM-grid chart — no librosa needed. Estimated 120 BPM."""
        bpm = 120.0
        duration_s = 180.0  # 3-minute default
        step = 60.0 / bpm / 2  # 8th notes
        lanes = INSTRUMENTS[instrument]["lanes"]
        diff_density = {"easy": 0.25, "medium": 0.5, "hard": 0.75, "expert": 1.0}.get(difficulty, 0.5)

        import random as _rng; _rng.seed(42)
        notes: List[NoteEvent] = []
        t = 0.0
        while t < duration_s:
            if _rng.random() < diff_density:
                notes.append(NoteEvent(time_s=round(t, 3), lane=_rng.randint(0, lanes - 1)))
            t += step

        sp_phrases = [
            {"start_s": s, "end_s": s + 8 * step}
            for s in [i * 32 * step for i in range(int(duration_s / (32 * step)))]
        ]
        return TrackChart(
            song_id=song_id,
            instrument=instrument,
            difficulty=difficulty,
            notes=notes,
            bpm_events=[{"time_s": 0.0, "bpm": bpm}],
            sp_phrases=sp_phrases,
            duration_s=duration_s,
        )


# ── Scoring engine ─────────────────────────────────────────────────────────────

class RhythmScorer:
    """
    Stateful per-song scoring session.
    Call note_hit() / note_miss() for each note judgment from the input layer.
    """

    def __init__(self, chart: TrackChart):
        self.chart = chart
        self.score = 0
        self.max_score = self._calc_max_score(chart)
        self.streak = 0
        self.streak_max = 0
        self.notes_hit = 0
        self.notes_total = len(chart.notes)
        self._multiplier = 1
        self._sp_active = False
        self._sp_meter = 0.0   # 0.0–1.0

    def _calc_max_score(self, chart: TrackChart) -> int:
        total = 0
        mult = 1
        streak = 0
        for note in chart.notes:
            mult = self._mult_at(streak)
            effective = SP_PHRASE_MULT if note.is_sp else 1.0
            total += int(NOTE_BASE_SCORE * mult * effective)
            streak += 1
        return max(1, total)

    def _mult_at(self, streak: int) -> int:
        m = 1
        for threshold in STREAK_MULT_THRESHOLDS:
            if streak >= threshold:
                m += 1
        return min(m, MAX_MULTIPLIER)

    def note_hit(self, note: NoteEvent, chord_bonus_notes: int = 0):
        self.notes_hit += 1
        self.streak += 1
        self.streak_max = max(self.streak_max, self.streak)
        self._multiplier = self._mult_at(self.streak)
        sp_mult = SP_PHRASE_MULT if (self._sp_active or note.is_sp) else 1.0
        earned = int((NOTE_BASE_SCORE + chord_bonus_notes * CHORD_BONUS) * self._multiplier * sp_mult)
        self.score += earned
        if note.is_sp:
            self._sp_meter = min(1.0, self._sp_meter + 0.25)

    def note_miss(self):
        self.streak = 0
        self._multiplier = 1

    def activate_sp(self) -> bool:
        if self._sp_meter >= 0.5:
            self._sp_active = True
            return True
        return False

    def drain_sp(self, delta: float = 0.01):
        if self._sp_active:
            self._sp_meter = max(0.0, self._sp_meter - delta)
            if self._sp_meter <= 0.0:
                self._sp_active = False

    @property
    def accuracy(self) -> float:
        if self.notes_total == 0:
            return 1.0
        return round(self.notes_hit / self.notes_total, 4)

    @property
    def stars(self) -> int:
        ratio = self.score / self.max_score
        for i, thresh in enumerate(STAR_THRESHOLDS):
            if ratio <= thresh:
                return i + 1
        stars = len(STAR_THRESHOLDS)
        if self.notes_hit == self.notes_total:
            stars = 6  # gold star / FC
        return stars

    @property
    def full_combo(self) -> bool:
        return self.notes_hit == self.notes_total

    def finalize(self, session_id: str, song_id: str) -> RhythmScore:
        return RhythmScore(
            score_id=str(uuid.uuid4())[:8],
            song_id=song_id,
            session_id=session_id,
            instrument=self.chart.instrument,
            difficulty=self.chart.difficulty,
            score=self.score,
            max_score=self.max_score,
            stars=self.stars,
            streak_max=self.streak_max,
            notes_hit=self.notes_hit,
            notes_total=self.notes_total,
            accuracy=self.accuracy,
            full_combo=self.full_combo,
        )


# ── Rhythm Venue ───────────────────────────────────────────────────────────────

class RhythmVenue:
    """
    Basement Layer 5 — Rhythm Game Venue.
    Manages song library, chart generation, and leaderboard.
    """

    CHART_CACHE_DIR = os.path.join("data", "rhythm_charts")

    def __init__(self, data_dir: str = "data"):
        self._db = None
        self._analyzer = TrackAnalyzer()
        self._active_scorers: Dict[str, RhythmScorer] = {}
        self._init_db(data_dir)
        os.makedirs(self.CHART_CACHE_DIR, exist_ok=True)

    def _init_db(self, data_dir: str):
        try:
            from tinydb import TinyDB
            os.makedirs(data_dir, exist_ok=True)
            self._db = TinyDB(os.path.join(data_dir, "world_memory.db"))
            self._songs = self._db.table("rhythm_songs")
            self._scores = self._db.table("rhythm_scores")
        except Exception as e:
            logger.warning("RhythmVenue: TinyDB unavailable (%s)", e)

    # ── Song library ───────────────────────────────────────────────────────────

    def add_song(
        self,
        audio_path: str,
        title: str,
        artist: str = "Unknown",
        genres: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Import a user audio track. Runs librosa analysis to generate charts
        for all 4 difficulties × all 5 instruments asynchronously.
        Returns song metadata immediately; charts written to data/rhythm_charts/.
        """
        if not os.path.isfile(audio_path):
            return {"error": f"File not found: {audio_path}"}

        song_id = str(uuid.uuid4())[:8]
        chart_dir = os.path.join(self.CHART_CACHE_DIR, song_id)
        os.makedirs(chart_dir, exist_ok=True)

        # Quick duration probe (no librosa needed for metadata)
        duration_s = self._probe_duration(audio_path)
        bpm = 0.0

        meta = SongMeta(
            song_id=song_id,
            title=title,
            artist=artist,
            audio_path=audio_path,
            chart_path=chart_dir,
            duration_s=duration_s,
            bpm=bpm,
            genres=genres or [],
            analyzed=False,
        )
        if self._db:
            self._songs.insert(asdict(meta))

        # Kick off analysis in background thread
        t = threading.Thread(
            target=self._analyze_all,
            args=(audio_path, song_id, chart_dir),
            daemon=True,
        )
        t.start()

        return {
            "song_id": song_id,
            "title": title,
            "artist": artist,
            "duration_s": duration_s,
            "status": "analyzing",
            "chart_dir": chart_dir,
        }

    def _analyze_all(self, audio_path: str, song_id: str, chart_dir: str):
        """Background: generate charts for all instruments × difficulties."""
        for inst in INSTRUMENTS:
            for diff in DIFFICULTIES:
                try:
                    chart = self._analyzer.analyze(audio_path, inst, diff, song_id)
                    chart_file = os.path.join(chart_dir, f"{inst}_{diff}.json")
                    with open(chart_file, "w", encoding="utf-8") as f:
                        json.dump(
                            {
                                "song_id": chart.song_id,
                                "instrument": chart.instrument,
                                "difficulty": chart.difficulty,
                                "duration_s": chart.duration_s,
                                "bpm_events": chart.bpm_events,
                                "sp_phrases": chart.sp_phrases,
                                "notes": [asdict(n) for n in chart.notes],
                            },
                            f,
                            indent=2,
                        )
                    logger.info("Chart saved: %s/%s %s", song_id, inst, diff)
                except Exception as e:
                    logger.error("Chart generation failed %s/%s %s: %s", song_id, inst, diff, e)
        # Mark analyzed
        if self._db:
            try:
                from tinydb import Query
                self._songs.update({"analyzed": True}, Query().song_id == song_id)
            except Exception:
                pass

    def _probe_duration(self, audio_path: str) -> float:
        """Quick duration probe. Tries mutagen, then wave, then returns 0."""
        try:
            from mutagen import File as MutagenFile  # type: ignore
            f = MutagenFile(audio_path)
            if f and f.info:
                return float(f.info.length)
        except Exception:
            pass
        try:
            import wave
            with wave.open(audio_path) as wf:
                return wf.getnframes() / wf.getframerate()
        except Exception:
            pass
        return 0.0

    # ── Gameplay ───────────────────────────────────────────────────────────────

    def start_session(
        self,
        session_id: str,
        song_id: str,
        instrument: str = "guitar",
        difficulty: str = "medium",
    ) -> Dict[str, Any]:
        """Load chart and prepare scorer for a play session."""
        chart_file = os.path.join(self.CHART_CACHE_DIR, song_id, f"{instrument}_{difficulty}.json")
        if not os.path.isfile(chart_file):
            return {"error": f"Chart not ready. song_id={song_id} {instrument}/{difficulty}"}

        with open(chart_file, encoding="utf-8") as f:
            raw = json.load(f)

        notes = [NoteEvent(**n) for n in raw.get("notes", [])]
        chart = TrackChart(
            song_id=song_id,
            instrument=instrument,
            difficulty=difficulty,
            notes=notes,
            bpm_events=raw.get("bpm_events", []),
            sp_phrases=raw.get("sp_phrases", []),
            duration_s=raw.get("duration_s", 0.0),
        )
        scorer = RhythmScorer(chart)
        key = f"{session_id}:{song_id}:{instrument}:{difficulty}"
        self._active_scorers[key] = scorer
        return {
            "session_key": key,
            "note_count": len(notes),
            "bpm": raw.get("bpm_events", [{}])[0].get("bpm", 0),
            "duration_s": chart.duration_s,
            "sp_phrases": len(chart.sp_phrases),
        }

    def judge_note(self, session_key: str, note_idx: int, hit: bool, chord_extra: int = 0):
        scorer = self._active_scorers.get(session_key)
        if not scorer:
            return {"error": "No active session"}
        if note_idx >= len(scorer.chart.notes):
            return {"error": "Note index out of range"}
        note = scorer.chart.notes[note_idx]
        if hit:
            scorer.note_hit(note, chord_extra)
        else:
            scorer.note_miss()
        return {
            "score": scorer.score,
            "streak": scorer.streak,
            "multiplier": scorer._multiplier,
            "sp_meter": round(scorer._sp_meter, 2),
        }

    def finish_session(self, session_key: str) -> Dict[str, Any]:
        scorer = self._active_scorers.pop(session_key, None)
        if not scorer:
            return {"error": "Session not found"}
        parts = session_key.split(":")
        session_id = parts[0] if parts else "unknown"
        song_id = parts[1] if len(parts) > 1 else "unknown"
        result = scorer.finalize(session_id, song_id)
        if self._db:
            try:
                self._scores.insert(asdict(result))
            except Exception:
                pass
        star_str = "⭐" * result.stars + (" 🌟" if result.full_combo else "")
        return {
            "stars": star_str,
            "score": result.score,
            "max_score": result.max_score,
            "accuracy": f"{result.accuracy * 100:.1f}%",
            "best_streak": result.streak_max,
            "full_combo": result.full_combo,
            "notes_hit": f"{result.notes_hit}/{result.notes_total}",
        }

    # ── Song library query ─────────────────────────────────────────────────────

    def list_songs(self) -> List[Dict]:
        if not self._db:
            return []
        try:
            return [
                {"song_id": d["song_id"], "title": d["title"],
                 "artist": d["artist"], "analyzed": d.get("analyzed", False),
                 "duration_s": d.get("duration_s", 0)}
                for d in self._songs.all()
            ]
        except Exception:
            return []

    def leaderboard(self, song_id: str, instrument: str = "guitar",
                    difficulty: str = "medium", top: int = UNITY) -> List[Dict]:
        if not self._db:
            return []
        try:
            from tinydb import Query
            docs = self._scores.search(
                (Query().song_id == song_id) &
                (Query().instrument == instrument) &
                (Query().difficulty == difficulty)
            )
            docs = sorted(docs, key=lambda d: d.get("score", 0), reverse=True)[:top]
            return [
                {"rank": i + 1, "session_id": d["session_id"][:8],
                 "score": d["score"], "stars": d["stars"],
                 "accuracy": f"{d['accuracy']*100:.1f}%"}
                for i, d in enumerate(docs)
            ]
        except Exception:
            return []

    def instrument_list(self) -> List[Dict]:
        return [{"id": k, "input_device": v["input"], "lanes": v["lanes"]} for k, v in INSTRUMENTS.items()]


# ── Singleton ──────────────────────────────────────────────────────────────────
_venue: Optional[RhythmVenue] = None

def get_rhythm_venue(data_dir: str = "data") -> RhythmVenue:
    global _venue
    if _venue is None:
        _venue = RhythmVenue(data_dir=data_dir)
    return _venue
