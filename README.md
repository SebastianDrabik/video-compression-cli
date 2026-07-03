# Simple Compressor (scomp)

Simple CLI tool that compresses videos to a **target file size** using **ffmpeg** under the hood.

![GitHub](https://img.shields.io/github/license/SebastianDrabik/video-compression-cli)
![Release](https://github.com/SebastianDrabik/video-compression-cli/actions/workflows/release.yml/badge.svg)
![GitHub release](https://img.shields.io/github/v/release/SebastianDrabik/video-compression-cli)
![Python](https://img.shields.io/badge/Python-3.14+%2B-%233776AB?logo=python&logoColor=white)

## Installation

### Quick Install

Copy and paste the command below to your terminal. This detects your OS, downloads and installs the correct binary from the [latest release](https://github.com/SebastianDrabik/video-compression-cli/releases) 

```bash
curl -fsSL https://raw.githubusercontent.com/SebastianDrabik/video-compression-cli/main/install.sh | bash
```

### Manual Install

Download the binary for your platform from the [Releases page](https://github.com/SebastianDrabik/video-compression-cli/releases), then:

```bash
# make the file executable
chmod +x scomp-<platform>-<arch>

# optional
sudo mv scomp-<platform>-<arch> /usr/local/bin/scomp
```

### Requirements

This tool uses `ffmpeg` and `ffprobe` under the hood and requires both to be installed and accessible on your `PATH`

```cmd
# macOS
brew install ffmpeg

# Debian / Ubuntu
sudo apt install ffmpeg

# Arch
sudo pacman -S ffmpeg
```

## Usage

Simple usage - this command will compress `input.mp4` down to ~25MB, saving the compressed video to `output.mp4`

```bash
scomp -i input.mp4 -s 25
```

### Options

| Flag | Description |
|------|-------------|
| `-i`, `--input` | Path to the input video file (required) |
| `-s`, `--size` | Target output size in MB (required) |
| `-o`, `--output` | Path to the output file (default: `./output<ext>`) |
| `-v`, `--version` | Print the version and exit |
| `-h`, `--help` | Show help and exit |

### Examples

Compress a video down to 10MB, using custom output path (ready to upload to discord)

```bash
scomp -i clip.mp4 -s 8 -o clip_compressed.mp4
```