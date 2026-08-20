"""Memory domain management — personal vs. collective, namespaced routing."""


class MemoryDomains:
    """Manages memory domains and namespaces for routed access."""
    
    # Personal domains
    PERSONAL_EPISODIC = "personal.episodic"    # Aurion's experiences, conversations, moments
    PERSONAL_CONVERSATION = "personal.conversation"  # Direct conversation history
    PERSONAL_IMAGE = "personal.image"          # Image references + linked contexts
    
    # Collective domains
    COLLECTIVE_REGIONAL = "collective.regional"      # Regional state + ecosystems
    COLLECTIVE_FESTIVAL = "collective.festival"      # Festival atmospheres + events
    COLLECTIVE_ECONOMY = "collective.economy"        # Trade, resources, markets
    COLLECTIVE_ECOSYSTEM = "collective.ecosystem"    # Ecology, species, nature
    
    # Knowledge domains
    KNOWLEDGE_SKILL = "knowledge.skill"        # Techniques, abilities, how-tos
    KNOWLEDGE_FACT = "knowledge.fact"          # Definitions, concepts, information
    KNOWLEDGE_RULE = "knowledge.rule"          # Laws, principles, constraints
    
    # Namespaces within domains (for isolation)
    DEFAULT_NAMESPACE = "default"
    
    @staticmethod
    def is_personal(domain):
        """Check if domain is personal memory."""
        return domain.startswith("personal.")
    
    @staticmethod
    def is_collective(domain):
        """Check if domain is collective memory."""
        return domain.startswith("collective.")
    
    @staticmethod
    def is_knowledge(domain):
        """Check if domain is knowledge memory."""
        return domain.startswith("knowledge.")
    
    @staticmethod
    def parse_domain(domain_str):
        """Parse 'type.domain[.namespace]' → (type, domain, namespace)."""
        parts = domain_str.split(".")
        if len(parts) >= 2:
            return parts[0], parts[1], ".".join(parts[2:]) or MemoryDomains.DEFAULT_NAMESPACE
        return None, None, MemoryDomains.DEFAULT_NAMESPACE


class RoutedMemoryStore:
    """Wrapper around memory system that enforces domain routing for access patterns."""
    
    def __init__(self, memory_system, memory_router):
        self.memory_system = memory_system
        self.router = memory_router
        self._domain_stats = {}  # Track domain access patterns
    
    def store_routed(self, content, domain=None, namespace=None, **metadata):
        """Store content in routed domain; auto-route if domain not specified."""
        if not domain:
            route = self.router.extract_route_hint(content)
            domain = f"{route['type']}.{route['domain']}"
            if namespace is None:
                namespace = route.get("region") or MemoryDomains.DEFAULT_NAMESPACE
        
        namespace = namespace or MemoryDomains.DEFAULT_NAMESPACE
        
        # Parse domain to extract type and subdomain
        type_part, domain_part, _ = MemoryDomains.parse_domain(domain)
        
        # Track domain access
        key = f"{domain}:{namespace}"
        self._domain_stats[key] = self._domain_stats.get(key, 0) + 1
        
        # Add domain metadata
        metadata["_routed_domain"] = domain
        metadata["_routed_namespace"] = namespace
        
        # Store in underlying memory system
        # (actual storage depends on memory_system implementation)
        return {
            "id": f"{domain}:{namespace}:{metadata.get('id', 'auto')}",
            "type": type_part,
            "domain": domain,
            "namespace": namespace,
            "content": content,
            "metadata": metadata,
        }
    
    def retrieve_from_domain(self, domain, namespace=None, limit=10):
        """Retrieve entries from a specific domain/namespace."""
        namespace = namespace or MemoryDomains.DEFAULT_NAMESPACE
        key = f"{domain}:{namespace}"
        # In real implementation, queries memory_system for entries with this domain:namespace tag
        return []
    
    def route_and_retrieve(self, query_text, limit=10):
        """Analyze query; retrieve from most relevant domain."""
        routes = self.router.route_text(query_text)
        results = []
        
        for route in routes[:3]:  # Check top 3 routes
            domain = f"{route['type']}.{route['domain']}"
            namespace = MemoryDomains.DEFAULT_NAMESPACE
            entries = self.retrieve_from_domain(domain, namespace, limit)
            results.extend([{**e, "_route_confidence": route["confidence"]} for e in entries])
        
        return sorted(results, key=lambda r: r.get("_route_confidence", 0), reverse=True)[:limit]
    
    def get_domain_stats(self):
        """Return domain access statistics."""
        return {
            "domains_accessed": len(self._domain_stats),
            "access_counts": self._domain_stats,
            "personal_accesses": sum(v for k, v in self._domain_stats.items() if k.startswith("personal.")),
            "collective_accesses": sum(v for k, v in self._domain_stats.items() if k.startswith("collective.")),
            "knowledge_accesses": sum(v for k, v in self._domain_stats.items() if k.startswith("knowledge.")),
        }
