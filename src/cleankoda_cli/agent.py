import json
import os

from cleankoda_cli.commands import CommandContext, registry
from cleankoda_cli.llm import client, model_name
from cleankoda_cli.memory import Memory
from cleankoda_cli.tools import *

SYSTEM_PROMPT = """You are a coding agentrunning in the user's terminal.
You can list files, read files, write files, and run shell commands.
Use your tools to complete the user's task, then briefly summarize what you did.
The working dyrectory is the folder the user launched you from."""

def run_tool(tool_call: dict) -> str:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    try:
        return str(TOOLS[name](**args))
    except Exception as error:
        return f"Error: {error}"


def run_agent(memory: Memory) -> str | None:
    while True:
        response = client.chat.complete(
            model=model_name,
            messages=memory.messages,
            tools=TOOL_SCHEMAS,
        )
        message = response.choices[0].message
        memory.add_message(message)

        if not message.tool_calls:
            return message.content

        for tool_call in message.tool_calls:
            result = run_tool(tool_call)
            memory.add_tool_message(tool_call_id=tool_call.id, content=result)


def agentloop():
    memory = Memory(system_prompt=SYSTEM_PROMPT)

    print("mini-code ready. Type '/help' for commands or '/exit' to quit.")
    while True:
        user_input = input("\nYou: ")
        if user_input.startswith("/"):
            ctx = CommandContext(memory=memory)
            result = registry.dispatch(user_input, ctx)
            if result.output:
                print(f"\nSystem: {result.output}")
            if result.should_exit:
                break
            continue

        if user_input.strip().lower() in ("exit", "quit"):
            break
        memory.add_user(user_input)
        reply = run_agent(memory)
        print(f"\nAgent: {reply}")


if __name__ == "__main__":
    agentloop()
