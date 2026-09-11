#!/usr/bin/env bash
set -euo pipefail

# Configuration
APP_NAME="cleankoda"
GITHUB_REPO="tomwey2/cleankoda-cli"
INSTALL_DIR="${CLEANKODA_INSTALL_DIR:-$HOME/.local/bin}"
TMP_DIR=""

# Text formatting
info() { echo -e "\033[1;34m::\033[0m $*"; }
success() { echo -e "\033[1;32m✓\033[0m $*"; }
error() { echo -e "\033[1;31m✖ Error:\033[0m $*" >&2; exit 1; }

# Safe cleanup on exit
cleanup() {
    if [ -n "${TMP_DIR:-}" ] && [ -d "${TMP_DIR:-}" ]; then
        rm -rf "$TMP_DIR"
    fi
}
trap cleanup EXIT

# 1. Detect Operating System
detect_os() {
    local os
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    case "$os" in
        linux)  echo "linux" ;;
        darwin) echo "darwin" ;;
        *)      error "Unsupported operating system: $os. CleanKoda currently supports Linux and macOS." ;;
    esac
}

# 2. Detect CPU Architecture
detect_arch() {
    local arch
    arch="$(uname -m)"
    case "$arch" in
        x86_64|amd64)   echo "x86_64" ;;
        arm64|aarch64)  echo "arm64" ;;
        *)              error "Unsupported architecture: $arch. CleanKoda currently supports x86_64 and arm64." ;;
    esac
}

main() {
    local os arch filename download_url

    os="$(detect_os)"
    arch="$(detect_arch)"

    info "Detected platform: ${os}-${arch}"

    # Construct release archive filename
    filename="${APP_NAME}-${os}-${arch}.tar.gz"
    download_url="https://github.com/${GITHUB_REPO}/releases/latest/download/${filename}"

    # Ensure required tools are available
    command -v curl >/dev/null 2>&1 || error "'curl' is required but not installed."
    command -v tar >/dev/null 2>&1  || error "'tar' is required but not installed."

    # Create temporary scratch directory
    TMP_DIR="$(mktemp -d)"

    info "Downloading ${filename} from GitHub..."
    if ! curl -fsSL "$download_url" -o "${TMP_DIR}/${filename}"; then
        error "Failed to download asset from ${download_url}.\nPlease verify that a release exists with asset '${filename}'."
    fi

    # Prepare installation directory
    mkdir -p "$INSTALL_DIR"

    info "Extracting binary to ${INSTALL_DIR}..."
    tar -xzf "${TMP_DIR}/${filename}" -C "$TMP_DIR"

    if [ ! -f "${TMP_DIR}/${APP_NAME}" ]; then
        error "Archive did not contain executable '${APP_NAME}'."
    fi

    mv "${TMP_DIR}/${APP_NAME}" "${INSTALL_DIR}/${APP_NAME}"
    chmod +x "${INSTALL_DIR}/${APP_NAME}"

    success "Successfully installed ${APP_NAME} to ${INSTALL_DIR}/${APP_NAME}!"

    # Check if INSTALL_DIR is in user's PATH
    case ":$PATH:" in
        *":$INSTALL_DIR:"*) ;;
        *)
            echo ""
            info "Notice: '${INSTALL_DIR}' is not currently in your PATH."
            echo "Add it to your shell configuration (e.g., ~/.bashrc or ~/.zshrc):"
            echo ""
            echo "    export PATH=\"${INSTALL_DIR}:\$PATH\""
            echo ""
            ;;
    esac

    info "Run '${APP_NAME} --help' to get started."
}

main "$@"
