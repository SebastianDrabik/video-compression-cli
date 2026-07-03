#!/usr/bin/env bash
set -euo pipefail

REPO="SebastianDrabik/video-compression-cli"
BIN_NAME="scomp"
INSTALL_DIR="${SCOMP_INSTALL_DIR:-/usr/local/bin}"

info()  { printf '\033[1;34m[*]\033[0m %s\n' "$1"; }
ok()    { printf '\033[1;32m[+]\033[0m %s\n' "$1"; }
error() { printf '\033[1;31m[!]\033[0m %s\n' "$1" >&2; }


OS="$(uname -s)"
case "$OS" in
    Linux)  PLATFORM="linux" ;;
    Darwin) PLATFORM="macos" ;;
    *)
        error "Unsupported OS: $OS"
        exit 1
        ;;
esac

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|amd64) ARCH="x86_64" ;;
    arm64|aarch64) ARCH="arm64" ;;
    *)
        error "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

if [ "$PLATFORM" = "linux" ] && [ "$ARCH" = "arm64" ]; then
    error "No Linux arm64 build is currently published for $BIN_NAME."
    exit 1
fi

ASSET_NAME="${BIN_NAME}-${PLATFORM}-${ARCH}"

info "Detected platform: ${PLATFORM}-${ARCH}"

info "Looking up latest release..."
API_URL="https://api.github.com/repos/${REPO}/releases/latest"

if command -v curl >/dev/null 2>&1; then
    RELEASE_JSON="$(curl -fsSL "$API_URL")"
elif command -v wget >/dev/null 2>&1; then
    RELEASE_JSON="$(wget -qO- "$API_URL")"
else
    error "Neither curl nor wget is available. Please install one and retry."
    exit 1
fi

DOWNLOAD_URL="$(printf '%s' "$RELEASE_JSON" \
    | grep -o "\"browser_download_url\": *\"[^\"]*${ASSET_NAME}\"" \
    | sed -E 's/.*"([^"]+)"$/\1/')"

if [ -z "$DOWNLOAD_URL" ]; then
    error "Could not find a release asset named '${ASSET_NAME}'."
    error "Check https://github.com/${REPO}/releases for available builds."
    exit 1
fi

TAG="$(printf '%s' "$RELEASE_JSON" | grep -o '"tag_name": *"[^"]*"' | sed -E 's/.*"([^"]+)"$/\1/')"
info "Latest version: ${TAG:-unknown}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

TMP_BIN="${TMP_DIR}/${BIN_NAME}"

info "Downloading ${ASSET_NAME}..."
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$DOWNLOAD_URL" -o "$TMP_BIN"
else
    wget -qO "$TMP_BIN" "$DOWNLOAD_URL"
fi

chmod +x "$TMP_BIN"

CHECKSUM_URL="${DOWNLOAD_URL}.sha256"
if command -v shasum >/dev/null 2>&1 || command -v sha256sum >/dev/null 2>&1; then
    info "Verifying checksum..."
    TMP_SHA="${TMP_DIR}/${ASSET_NAME}.sha256"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$CHECKSUM_URL" -o "$TMP_SHA" 2>/dev/null || true
    else
        wget -qO "$TMP_SHA" "$CHECKSUM_URL" 2>/dev/null || true
    fi

    if [ -s "$TMP_SHA" ]; then
        EXPECTED="$(awk '{print $1}' "$TMP_SHA")"
        if command -v shasum >/dev/null 2>&1; then
            ACTUAL="$(shasum -a 256 "$TMP_BIN" | awk '{print $1}')"
        else
            ACTUAL="$(sha256sum "$TMP_BIN" | awk '{print $1}')"
        fi

        if [ "$EXPECTED" != "$ACTUAL" ]; then
            error "Checksum mismatch! Expected $EXPECTED, got $ACTUAL."
            exit 1
        fi
        ok "Checksum verified."
    else
        info "No checksum file found, skipping verification."
    fi
fi

# --- Install ---
if [ -w "$INSTALL_DIR" ]; then
    mv "$TMP_BIN" "${INSTALL_DIR}/${BIN_NAME}"
else
    info "Elevated permissions needed to write to ${INSTALL_DIR}"
    sudo mv "$TMP_BIN" "${INSTALL_DIR}/${BIN_NAME}"
fi

ok "Installed ${BIN_NAME} to ${INSTALL_DIR}/${BIN_NAME}"

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
    error "ffmpeg/ffprobe not found on your system. ${BIN_NAME} requires both to run."
    error "Install them via your package manager (e.g. 'brew install ffmpeg' or 'apt install ffmpeg')."
fi

if command -v "$BIN_NAME" >/dev/null 2>&1; then
    ok "Run '${BIN_NAME} --version' to verify the install."
else
    info "Installed, but '${INSTALL_DIR}' isn't on your PATH. Add it, e.g.:"
    info "  export PATH=\"${INSTALL_DIR}:\$PATH\""
fi