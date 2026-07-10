"""Protocol manifest for the Mini Notes Summary Executa."""

MANIFEST = {
    "name": "mini-notes-summary",
    "display_name": "Mini Notes Summary",
    "version": "0.1.0",
    "description": (
        "Summarizes ordered Mini Notes by asking the Anna host to sample an LLM."
    ),
    "host_capabilities": ["llm.sample"],
    "tools": [
        {
            "name": "summarize_notes",
            "description": (
                "Create a concise summary of ordered notes, including key themes "
                "and action items, using host LLM sampling."
            ),
            "parameters": [
                {
                    "name": "notes",
                    "type": "array",
                    "items_type": "object",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "order": {"type": "integer"},
                            "content": {"type": "string"},
                        },
                        "required": ["id", "order", "content"],
                        "additionalProperties": False,
                    },
                    "description": (
                        "Mini Notes objects shaped as {id: string, order: integer, "
                        "content: string}."
                    ),
                    "required": True,
                }
            ],
        }
    ],
    "runtime": {"type": "uv", "min_version": "0.1.0"},
}

