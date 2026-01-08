def compress_tool_result(tool_name: str, result, max_items=5, max_chars=800):
    if result is None:
        return f"{tool_name}: no result"

    # Lists (parks, plots, pois)
    if isinstance(result, list):
        sample = result[:max_items]
        return (
            f"{tool_name}: {len(result)} total results. "
            f"Sample: {sample}"
        )

    # Dict
    if isinstance(result, dict):
        text = str(result)
        return text[:max_chars]

    # Fallback
    return str(result)[:max_chars]
