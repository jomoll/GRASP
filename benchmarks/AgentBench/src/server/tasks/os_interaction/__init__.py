def __getattr__(name):
    if name == "OSInteraction":
        from .task import OSInteraction

        return OSInteraction
    raise AttributeError(name)
