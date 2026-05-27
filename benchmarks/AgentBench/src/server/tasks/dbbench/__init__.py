def __getattr__(name):
    if name == "DBBenchTask":
        from .task import DBBenchTask

        return DBBenchTask
    raise AttributeError(name)
