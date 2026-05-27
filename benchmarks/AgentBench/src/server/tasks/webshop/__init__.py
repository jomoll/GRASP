def __getattr__(name):
    if name == "WebShop":
        from .task import WebShop

        return WebShop
    raise AttributeError(name)
