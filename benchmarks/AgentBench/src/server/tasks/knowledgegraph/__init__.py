def __getattr__(name):
    if name == "KnowledgeGraph":
        from .task import KnowledgeGraph

        return KnowledgeGraph
    raise AttributeError(name)
