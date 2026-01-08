def normalize_state(state: str) -> str:
    if not state:
        return state
    return state.strip().lower().replace(" ", "_")
