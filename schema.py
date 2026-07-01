BOIS_SCHEMA = {
    "version": "0.1",
    "fields": ["input", "bois", "reasoning", "output"],
    "output": {
        "input": ["raw", "intent", "risk", "uncertainty"],
        "bois": ["intent", "risk", "uncertainty", "route"],
        "reasoning": ["raw"],
        "output": ["answer", "key_points"],
    },
}
