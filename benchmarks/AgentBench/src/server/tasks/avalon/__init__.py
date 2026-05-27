def __getattr__(name):
    if name == "AvalonBench":
        from .task import AvalonBench

        return AvalonBench
    raise AttributeError(name)
