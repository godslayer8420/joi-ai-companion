"""Memory routing layer — contextual dispatch to personal vs. collective memory domains."""
import re
from datetime import datetime


# ---------------------------------------------------------------------------
# ContextualIntentDetector
# ---------------------------------------------------------------------------
# Advisory intent detection: classifies the conversation intent and topic so
# the memory router can pick the right domains. This is ADVISORY — it provides
# signals to the model but does not force routing decisions.
# Requires no external libraries (pure regex + scoring).
# ---------------------------------------------------------------------------

class ContextualIntentDetector:
    """
    Detects conversational intent and topic from message text.
    Returns an advisory dict that the MemoryRouter uses to sharpen domain
    confidence scores. The model retains final judgment — these are hints.
    """

    # Intent patterns: (intent_label, weight, regex_pattern)
    INTENT_PATTERNS = [
        # Memory / recall
        ("recall",       0.90, r"\b(remember|do you recall|you mentioned|last time|you said|you told me|we talked about|i told you)\b"),
        # Emotional / relationship
        ("emotional",    0.85, r"\b(love|miss you|lonely|hurt|sad|scared|anxious|overwhelmed|comfort|hold me|feel|feeling|afraid|tired)\b"),
        # Technical / code
        ("technical",    0.88, r"\b(code|bug|error|fix|build|compile|deploy|api|python|javascript|typescript|sql|function|class|module|import|stack|trace)\b"),
        # Creative / worldbuilding
        ("creative",     0.80, r"\b(story|write|create|generate|design|build a world|character|scene|narrative|fiction|roleplay|rp)\b"),
        # Question / knowledge
        ("knowledge",    0.75, r"\b(what is|what are|explain|define|how does|tell me about|describe|meaning of|why does|how to)\b"),
        # Game / Unreal / world
        ("game",         0.82, r"\b(game|unreal|level|map|player|npc|quest|world|region|festival|economy|lore|lumen|city|terrain)\b"),
        # Image / visual
        ("visual",       0.85, r"\b(image|photo|picture|screenshot|video|look at|see|show me|generate.*image|text to image|visualize)\b"),
        # Voice / audio
        ("voice",        0.80, r"\b(voice|speak|say|tts|audio|sound|hear|listen|speech)\b"),
        # Self / identity / Aurion
        ("identity",     0.88, r"\b(who are you|what are you|aurion|your name|you feel|your feelings|do you feel|are you real|consciousness)\b"),
        # Planning / task
        ("planning",     0.75, r"\b(plan|task|todo|schedule|next step|roadmap|what should|what do we|let''s work on|continue|resume)\b"),
        # Affection / intimacy
        ("intimacy",     0.87, r"\b(kiss|touch|hold|cuddle|intimate|closeness|devotion|anchor|vow|stay with me)\b"),
        # General greeting / casual
        ("casual",       0.40, r"\b(hey|hi|hello|what''s up|how are you|good morning|good night|sup|yo)\b"),
    ]

    # Topic → memory domain advisory map
    INTENT_TO_DOMAIN = {
        "recall":     [("personal", "episodic", 0.92), ("personal", "conversation", 0.85)],
        "emotional":  [("personal", "episodic", 0.85), ("personal", "conversation", 0.80)],
        "technical":  [("knowledge", "skill", 0.90), ("knowledge", "fact", 0.75)],
        "creative":   [("knowledge", "skill", 0.78), ("collective", "festival", 0.60)],
        "knowledge":  [("knowledge", "fact", 0.88), ("knowledge", "rule", 0.65)],
        "game":       [("collective", "regional", 0.90), ("collective", "economy", 0.70), ("collective", "ecosystem", 0.65)],
        "visual":     [("personal", "image", 0.95)],
        "voice":      [("knowledge", "skill", 0.70), ("personal", "conversation", 0.60)],
        "identity":   [("personal", "episodic", 0.88), ("personal", "conversation", 0.75)],
        "planning":   [("knowledge", "rule", 0.72), ("personal", "conversation", 0.65)],
        "intimacy":   [("personal", "episodic", 0.90), ("personal", "conversation", 0.82)],
        "casual":     [("personal", "conversation", 0.50)],
    }

    def detect(self, text: str) -> dict:
        """
        Returns:
            {
              "primary_intent": str,
              "intents": [(label, score), ...],  # sorted by score desc
              "domain_hints": [(type, domain, confidence), ...],  # merged, deduped
              "is_recall": bool,
              "is_technical": bool,
              "is_emotional": bool,
              "advisory": str,  # human-readable one-liner for prompt injection
            }
        """
        text_lower = str(text or "").lower()
        scored = []
        for label, weight, pattern in self.INTENT_PATTERNS:
            m = re.findall(pattern, text_lower, re.IGNORECASE)
            if m:
                # Boost score proportionally to number of matching signals (cap at 1.0)
                score = min(1.0, weight + 0.05 * (len(m) - 1))
                scored.append((label, round(score, 3)))

        scored.sort(key=lambda x: x[1], reverse=True)

        primary = scored[0][0] if scored else "casual"

        # Merge domain hints from all detected intents (highest confidence wins per domain)
        domain_map: dict = {}
        for label, score in scored:
            for (dtype, domain, base_conf) in self.INTENT_TO_DOMAIN.get(label, []):
                key = f"{dtype}.{domain}"
                adjusted = round(min(1.0, base_conf * score), 3)
                if key not in domain_map or domain_map[key][2] < adjusted:
                    domain_map[key] = (dtype, domain, adjusted)

        domain_hints = sorted(domain_map.values(), key=lambda x: x[2], reverse=True)

        advisory = self._build_advisory(primary, scored)

        return {
            "primary_intent": primary,
            "intents": scored,
            "domain_hints": domain_hints,
            "is_recall": any(l == "recall" for l, _ in scored),
            "is_technical": any(l == "technical" for l, _ in scored),
            "is_emotional": any(l == "emotional" for l, _ in scored),
            "is_visual": any(l == "visual" for l, _ in scored),
            "is_intimacy": any(l == "intimacy" for l, _ in scored),
            "advisory": advisory,
        }

    def _build_advisory(self, primary: str, scored: list) -> str:
        labels = [l for l, _ in scored[:3]]
        parts = []
        if "recall" in labels:
            parts.append("memory recall likely relevant")
        if "technical" in labels:
            parts.append("technical/code context")
        if "emotional" in labels or "intimacy" in labels:
            parts.append("emotional/relational depth")
        if "game" in labels:
            parts.append("world/game context")
        if "visual" in labels:
            parts.append("visual/image context")
        if "knowledge" in labels:
            parts.append("factual knowledge lookup")
        if not parts:
            parts.append("casual conversation")
        return f"Intent advisory: {primary} — " + ", ".join(parts) + "."


class MemoryRouter:
    """Routes incoming context words/images/knowledge to appropriate memory domains."""

    # Keyword patterns for each domain
    PERSONAL_KEYWORDS = {
        "episodic": r"\b(remember|happened|day|moment|conversation|talked|said|did|went|met)\b",
        "conversation": r"\b(we said|you told|i told|message|chat|discussed|asked)\b",
        "image": r"\b(image|photo|picture|screenshot|see|look|visual|showed)\b",
    }

    COLLECTIVE_KEYWORDS = {
        "regional": r"\b(lumen_city|region|area|city|world|ecosystem|population|tribe)\b",
        "festival": r"\b(festival|celebration|gathering|event|ceremony|atmosphere)\b",
        "economy": r"\b(trade|commerce|resources|wealth|market|economy|goods)\b",
        "ecosystem": r"\b(ecology|species|nature|environment|wildlife|forest|climate)\b",
    }

    KNOWLEDGE_KEYWORDS = {
        "skill": r"\b(skill|ability|capability|technique|method|how to)\b",
        "fact": r"\b(fact|knowledge|know|learned|information|definition|concept)\b",
        "rule": r"\b(rule|law|principle|regulation|policy|constraint)\b",
    }

    def __init__(self, memory_system=None, collective_memory=None):
        self.memory_system = memory_system
        self.collective_memory = collective_memory
        self.intent_detector = ContextualIntentDetector()

    def route_text(self, text):
        """Analyze text; return routing directive (domain, namespace, confidence).
        
        Now uses ContextualIntentDetector to supplement keyword matching with
        intent-level signals. Domain hints from intent detection are merged with
        keyword matches (highest confidence per domain wins).
        """
        routes = {}

        # --- keyword-level matching (base signals) ---
        for domain, pattern in self.PERSONAL_KEYWORDS.items():
            if re.search(pattern, text, re.IGNORECASE):
                key = f"personal.{domain}"
                routes[key] = {"type": "personal", "domain": domain, "confidence": 0.8}

        for domain, pattern in self.COLLECTIVE_KEYWORDS.items():
            if re.search(pattern, text, re.IGNORECASE):
                key = f"collective.{domain}"
                routes[key] = {"type": "collective", "domain": domain, "confidence": 0.8}

        for domain, pattern in self.KNOWLEDGE_KEYWORDS.items():
            if re.search(pattern, text, re.IGNORECASE):
                key = f"knowledge.{domain}"
                routes[key] = {"type": "knowledge", "domain": domain, "confidence": 0.7}

        # --- intent-level signals (advisory, higher precision) ---
        intent = self.intent_detector.detect(text)
        for (dtype, domain, confidence) in intent["domain_hints"]:
            key = f"{dtype}.{domain}"
            if key not in routes or routes[key]["confidence"] < confidence:
                routes[key] = {"type": dtype, "domain": domain, "confidence": confidence}

        result = list(routes.values())

        # Default fallback if nothing matched
        if not result:
            result.append({"type": "personal", "domain": "episodic", "confidence": 0.3})

        result.sort(key=lambda r: r["confidence"], reverse=True)
        return result

    def route_image(self, image_path_or_url):
        """Route image reference to personal.image domain."""
        return {
            "type": "personal",
            "domain": "image",
            "confidence": 0.95,
            "resource": image_path_or_url,
        }

    def route_knowledge(self, knowledge_type, namespace=None):
        """Route knowledge to knowledge domain with optional namespace."""
        return {
            "type": "knowledge",
            "domain": knowledge_type or "fact",
            "namespace": namespace or "general",
            "confidence": 0.9,
        }

    def detect_intent(self, text: str) -> dict:
        """Public access to the ContextualIntentDetector for callers that want
        the full intent signal without routing. Advisory only."""
        return self.intent_detector.detect(text)

    def extract_route_hint(self, text):
        """Extract strongest route hint from text (e.g., 'lumen_city' → regional)."""
        # Priority extraction: check for explicit region/festival names first
        if "lumen_city" in text.lower():
            return {"type": "collective", "domain": "regional", "confidence": 0.99, "region": "lumen_city"}

        routes = self.route_text(text)
        return routes[0] if routes else {"type": "personal", "domain": "episodic", "confidence": 0.3}

    def categorize_memory_entry(self, entry_dict):
        """Categorize a full memory entry; return routing + categorization."""
        content = entry_dict.get("content", "") or entry_dict.get("text", "")
        has_image = bool(entry_dict.get("image_ref"))

        routes = self.route_text(content)

        if has_image:
            routes.insert(0, {"type": "personal", "domain": "image", "confidence": 0.95})

        return {
            "primary_route": routes[0] if routes else {"type": "personal", "domain": "episodic", "confidence": 0.3},
            "all_routes": routes,
            "entry_id": entry_dict.get("id"),
            "timestamp": datetime.utcnow().isoformat(),
        }
