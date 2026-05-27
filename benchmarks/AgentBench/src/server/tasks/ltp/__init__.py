def __getattr__(name):
    if name == "LateralThinkingPuzzle":
        from .task import LateralThinkingPuzzle
        return LateralThinkingPuzzle
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")