from dataclasses import dataclass

@dataclass(frozen=True)
class SandboxImageChoice:
    id: str
    name: str
    description: str
    is_host: bool = False

SANDBOX_IMAGES: list[SandboxImageChoice] = [
    SandboxImageChoice("python:3.11-slim", "Python 3.11", "Python 3.11 (Standard Environment)"),
    SandboxImageChoice("python:3.12-slim", "Python 3.12", "Python 3.12 (Modern Python)"),
    SandboxImageChoice("node:20-slim", "Node.js 20", "Node.js 20 LTS"),
    SandboxImageChoice("rust:latest", "Rust", "Rust & Cargo Environment"),
    SandboxImageChoice("golang:1.22", "Go 1.22", "Go Environment"),
    SandboxImageChoice("ubuntu:24.04", "Ubuntu 24.04", "Generic Ubuntu Base"),
    SandboxImageChoice("host", "Host System", "Host System (No Sandbox, direct execution)", is_host=True),
]
