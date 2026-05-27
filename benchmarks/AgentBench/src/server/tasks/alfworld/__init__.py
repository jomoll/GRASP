def __getattr__(name):
    if name in ("ALFWorld", "AlfWorld"):
        from .task import ALFWorld

        return ALFWorld
    raise AttributeError(name)
