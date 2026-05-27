def __getattr__(name):
    if name == "CardGame":
        from .task import CardGame

        return CardGame
    raise AttributeError(name)
