def __getattr__(name):
    if name == "Mind2Web":
        from .task import Mind2Web

        return Mind2Web
    raise AttributeError(name)
