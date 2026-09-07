from dataclasses import dataclass


@dataclass(frozen=True)
class SandboxImageOption:
    id: str           # z. B. "python:3.11-slim" oder "host"
    name: str         # Sprechender Titel im Menü
    description: str  # Kurzbeschreibung für den Auswahldialog


DEFAULT_IMAGE = "python:3.11-slim"

AVAILABLE_IMAGES: list[SandboxImageOption] = [
    SandboxImageOption("python:3.11-slim", "Python 3.11", "Standard Python Environment"),
    SandboxImageOption("ghcr.io/astral-sh/uv:python3.11-bookworm-slim", "Python 3.11 + uv", "Python 3.11 from Astral with uv Package Manager"),
    SandboxImageOption("python:3.12-slim", "Python 3.12", "Modern Python Environment"),
    SandboxImageOption("node:20-slim", "Node.js 20 LTS", "JavaScript & TypeScript Runtime"),
    SandboxImageOption("rust:latest", "Rust", "Cargo & Rust Toolchain"),
    SandboxImageOption("golang:1.22", "Go 1.22", "Go Development Environment"),
    SandboxImageOption("ubuntu:24.04", "Ubuntu 24.04", "Allgemeine Linux-Basisumgebung"),
    SandboxImageOption("host", "Host (Keine Sandbox)", "Direkte Ausführung auf dem Host-System"),
]
