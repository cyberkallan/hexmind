"""
AutoAgent: Semantic Tool Retriever
"""

class SemanticToolRetriever:
    def __init__(self, memory):
        self.memory = memory

    def retrieve_tools(self, query: str, limit: int = 5) -> list:
        """
        Dynamically fetch the most relevant tools for a user query.
        Instead of loading 100+ tools into context, this gets the top N
        based on keyword overlap with the tool's description.
        """
        query_words = set(query.lower().split())
        scored_tools = []

        # Analyze tool memory
        for tool in self.memory.tool_memory:
            desc = tool.get("usage", "").lower()
            name = tool.get("name", "").lower()
            
            # Simple term frequency scoring
            score = 0
            for w in query_words:
                if w in name: score += 3
                if w in desc: score += 1
                
            if score > 0:
                scored_tools.append((score, tool))
                
        # Sort by score descending
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        
        # Return top N tool dictionaries
        return [t[1] for t in scored_tools[:limit]]
    
    def format_retrieved_tools_for_prompt(self, tools: list) -> str:
        """Format the top tools for injection into the system prompt."""
        if not tools:
            return ""
            
        res = "RELEVANT TOOLS FOUND IN TOOL_MEMORY:\n"
        for t in tools:
            res += f"- {t.get('name')}: {t.get('usage')}\n"
        return res
