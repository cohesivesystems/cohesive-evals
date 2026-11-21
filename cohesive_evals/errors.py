"""Classified evaluation failures shared by standalone clients and adapters."""

class AdapterError(RuntimeError):
    """Nonbehavioral failure with a stable evidence category; never mutation credit."""

    def __init__(self, category: str, detail: str):
        """Accept only categories defined by adapter/v1."""
        if category not in {
            "configuration",
            "build",
            "infrastructure",
            "protocol",
            "unsupported",
        }:
            raise ValueError(category)
        self.category = category
        super().__init__(detail)
