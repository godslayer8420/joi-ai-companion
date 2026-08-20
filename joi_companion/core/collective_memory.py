"""Universe collective memory — shared world, regional, festival state."""
from datetime import datetime
from pathlib import Path
import json
import os


class CollectiveMemory:
    """Stores universe-wide state: regions, ecosystems, economies, experiences, festival atmospheres."""
    
    def __init__(self, storage_root=None):
        self.storage_root = Path(storage_root or os.getenv("AURION_COLLECTIVE_MEMORY_ROOT", ".aurion/collective"))
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.world_state_file = self.storage_root / "world_state.json"
        self.regions = {}
        self.festivals = {}
        self.world_meta = {}
        self._load_or_initialize()
    
    def _load_or_initialize(self):
        """Load collective memory from disk or initialize fresh."""
        if self.world_state_file.exists():
            try:
                with open(self.world_state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.world_meta = data.get("world_meta", {})
                    self.regions = data.get("regions", {})
                    self.festivals = data.get("festivals", {})
            except Exception as e:
                print(f"[CollectiveMemory] Load failed: {e}. Reinitializing.")
                self._initialize_fresh()
        else:
            self._initialize_fresh()
    
    def _initialize_fresh(self):
        """Create fresh collective memory with default world setup."""
        self.world_meta = {
            "created_at": datetime.utcnow().isoformat(),
            "world_name": "Aurion's Universe",
            "current_epoch": 1,
            "ecosystem_state": "stable",
        }
        self.regions = {
            "lumen_city": {
                "region_id": "lumen_city",
                "name": "Lumen City",
                "ecosystem_level": 1.0,
                "economy_state": {"wealth": 100, "trade_routes": []},
                "population": [],
                "experiences": [],
                "last_updated": datetime.utcnow().isoformat(),
            }
        }
        self.festivals = {}
        self.save()
    
    def save(self):
        """Persist collective memory to disk."""
        try:
            with open(self.world_state_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "world_meta": self.world_meta,
                    "regions": self.regions,
                    "festivals": self.festivals,
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"[CollectiveMemory] Save failed: {e}")
    
    def get_world_state(self):
        """Return full world state snapshot."""
        return {
            "meta": self.world_meta,
            "regions": self.regions,
            "festivals": self.festivals,
        }
    
    def update_region(self, region_id, updates):
        """Merge updates into a region (ecosystem, economy, population, experiences)."""
        if region_id not in self.regions:
            self.regions[region_id] = {
                "region_id": region_id,
                "name": region_id.replace("_", " ").title(),
                "ecosystem_level": 1.0,
                "economy_state": {},
                "population": [],
                "experiences": [],
                "last_updated": datetime.utcnow().isoformat(),
            }
        self.regions[region_id].update(updates)
        self.regions[region_id]["last_updated"] = datetime.utcnow().isoformat()
        self.save()
    
    def get_region(self, region_id):
        """Retrieve a region's state."""
        return self.regions.get(region_id)
    
    def get_festival(self, region_id, festival_name):
        """Retrieve a festival's state by region + name."""
        festival_key = f"{region_id}:{festival_name}"
        return self.festivals.get(festival_key)
    
    def update_festival(self, region_id, festival_name, updates):
        """Merge updates into a festival atmosphere (supports region + festival_name)."""
        festival_key = f"{region_id}:{festival_name}"
        if festival_key not in self.festivals:
            self.festivals[festival_key] = {
                "festival_id": festival_key,
                "region_id": region_id,
                "festival_name": festival_name,
                "name": festival_name.replace("_", " ").title(),
                "atmosphere": {},
                "affordances": [],
                "created_at": datetime.utcnow().isoformat(),
            }
        self.festivals[festival_key].update(updates)
        self.save()
    
    def add_experience(self, region_id, experience):
        """Record shared experience in a region."""
        if region_id not in self.regions:
            self.update_region(region_id, {})
        # Store with both timestamp and flattened event data for test compatibility
        exp_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "data": experience,
        }
        # Also flatten to root for easier access in tests
        exp_entry.update(experience)
        self.regions[region_id]["experiences"].append(exp_entry)
        self.save()
    
    def query_region_experiences(self, region_id, limit=10):
        """Fetch recent experiences from a region."""
        if region_id not in self.regions:
            return []
        exps = self.regions[region_id].get("experiences", [])
        return exps[-limit:] if exps else []
