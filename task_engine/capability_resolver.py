def resolve_capabilities(actor_id: str) -> set[str]:
    """
    Server-authoritative capability resolution.
    Temporary hardcoded logic.
    """

    if actor_id == "SYSTEM":
        return{
            "submit_for_review",
            "start_progress",
            "complete_task",
            "archive_task",
        }
    
    if actor_id == "USER":
        return {
            "submit_for_review",
            "start_progress",
            "complete_task",
        }

    return set()