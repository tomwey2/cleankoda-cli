TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List the files in a directory. Folders end with /.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory to list, e.g. '.'"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of the file to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a text file with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of the file to write"},
                    "content": {"type": "string", "description": "Full contents of the file"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Run a shell command and return its output. The user approves it first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run"},
                },
                "required": ["command"],
            },
        },
    },
]
