"""Memory routing layer — contextual dispatch to personal vs. collective memory domains."""
import re
from datetime import datetime


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
    
    def route_text(self, text):
        """Analyze text; return routing directive (domain, namespace, confidence)."""
        routes = []
        
        # Check personal keywords
        for domain, pattern in self.PERSONAL_KEYWORDS.items():
            if re.search(pattern, text, re.IGNORECASE):
                routes.append({"type": "personal", "domain": domain, "confidence": 0.8})
        
        # Check collective keywords
        for domain, pattern in self.COLLECTIVE_KEYWORDS.items():
            if re.search(pattern, text, re.IGNORECASE):
                routes.append({"type": "collective", "domain": domain, "confidence": 0.8})
        
        # Check knowledge keywords
        for domain, pattern in self.KNOWLEDGE_KEYWORDS.items():
            if re.search(pattern, text, re.IGNORECASE):
                routes.append({"type": "knowledge", "domain": domain, "confidence": 0.7})
        
        # If no routes found, default to personal episodic
        if not routes:
            routes.append({"type": "personal", "domain": "episodic", "confidence": 0.3})
        
        return sorted(routes, key=lambda r: r["confidence"], reverse=True)
    
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
    
    def extract_route_hint(self, text):
        """Extract strongest route hint from text (e.g., "lumen_city" → regional)."""
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
