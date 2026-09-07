from dataclasses import dataclass


@dataclass(frozen=True)
class SandboxImageOption:
    id: str           # z. B. "python:3.11-slim" oder "host"
    name: str         # Sprechender Titel im Menü
    description: str  # Kurzbeschreibung für den Auswahldialog


DEFAULT_IMAGE = "python:3.11-slim"

AVAILABLE_IMAGES: list[SandboxImageOption] = [
    # --- Python ---
    SandboxImageOption(
        id="ghcr.io/astral-sh/uv:python3.11-bookworm-slim",
        name="Python 3.11 + uv",
        description="Astral uv, pip, Python 3.11 (Debian Bookworm)",
    ),
    SandboxImageOption(
        id="ghcr.io/astral-sh/uv:python3.12-bookworm-slim",
        name="Python 3.12 + uv",
        description="Astral uv, pip, Python 3.12 (Debian Bookworm)",
    ),

    # --- Java / Spring Boot ---
    SandboxImageOption(
        id="maven:3.9-eclipse-temurin-21",
        name="Java 21 + Maven",
        description="Eclipse Temurin JDK 21 & Maven 3.9 (Ideal für Spring Boot 3)",
    ),
    SandboxImageOption(
        id="maven:3.9-eclipse-temurin-17",
        name="Java 17 + Maven",
        description="Eclipse Temurin JDK 17 & Maven 3.9 (Spring Boot LTS)",
    ),
    SandboxImageOption(
        id="gradle:jdk21",
        name="Java 21 + Gradle",
        description="Offizielles Gradle-Image mit JDK 21",
    ),

    # --- Node.js / React / Frontend ---
    SandboxImageOption(
        id="node:22-bookworm-slim",
        name="Node.js 22 LTS",
        description="Node 22, npm, npx, yarn (Vite, React, Next.js)",
    ),
    SandboxImageOption(
        id="node:20-bookworm-slim",
        name="Node.js 20 LTS",
        description="Node 20, npm, npx, yarn (Stabiles Frontend-Environment)",
    ),

    # --- System / Host ---
    SandboxImageOption(
        id="ubuntu:24.04",
        name="Ubuntu 24.04",
        description="Allgemeines Linux Base-Environment",
    ),
    SandboxImageOption(
        id="host",
        name="Host (Keine Sandbox)",
        description="Befehle direkt im Host-System ausführen",
    ),
]
