import argparse
import subprocess
import os
import sys
import re
import time

__version__ = '0.2.2'

def get_video_duration(input_file):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_file
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return float(result.stdout.strip())
    except subprocess.CalledProcessError:
        print(f"Error: Can't read {input_file}. Is ffmpeg/ffprobe installed?")
        sys.exit(1)


def get_file_size_mb(path):
    return os.path.getsize(path) / (1024 * 1024)


def parse_time_to_seconds(time_str):
    h, m, s = time_str.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def format_eta(seconds):
    if seconds <= 0:
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def render_bar(progress, width=30):
    filled = int(progress * width)
    return "█" * filled + "░" * (width - filled)


MIN_BITRATES = {
    "3840x2160": 12000,
    "2560x1440": 7000,
    "1920x1080": 3500,
    "1280x720": 1800,
    "854x480": 900,
    "640x360": 500,
}

RES_ORDER = [
    (3840, 2160),
    (2560, 1440),
    (1920, 1080),
    (1280, 720),
    (854, 480),
    (640, 360),
]


def pick_resolution_for_bitrate(video_bitrate_kbps):
    for w, h in RES_ORDER:
        key = f"{w}x{h}"
        if video_bitrate_kbps >= MIN_BITRATES[key]:
            return w, h
    return 640, 360


def get_video_fps(input_file):
    cmd = [
        "ffprobe", "-v", "0",
        "-of", "csv=p=0",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        input_file
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )

    rate = result.stdout.strip()

    try:
        num, den = rate.split("/")
        return float(num) / float(den)
    except:
        return 30.0


def pick_fps(video_bitrate_kbps, original_fps):
    if video_bitrate_kbps < 500 and original_fps > 30:
        return 30
    if video_bitrate_kbps < 300 and original_fps > 24:
        return 24
    return original_fps


def compress_video(input_file, output_file, target_size_mb, adjust_resolution=False):
    duration = get_video_duration(input_file)

    total_bitrate_kbps = (target_size_mb * 8192) / duration
    audio_bitrate_kbps = 128
    video_bitrate_kbps = total_bitrate_kbps - audio_bitrate_kbps

    if video_bitrate_kbps <= 0:
        print("Error: Output size is too small")
        sys.exit(1)

    print(f"[/] Duration: {duration:.2f} s")
    print(f"[/] Target size: {target_size_mb} MB")
    print(f"[/] Video bitrate: {video_bitrate_kbps:.2f} kbps")

    if video_bitrate_kbps < 300:
        print("[!] WARNING: Extremely low bitrate. Expect heavy quality loss.")
    if video_bitrate_kbps < 150:
        print("[!!!] CRITICAL: Output will be barely watchable.")

    fps = get_video_fps(input_file)
    original_fps = fps

    scale_filter = None

    if adjust_resolution:
        w, h = pick_resolution_for_bitrate(video_bitrate_kbps)
        print(f"[/] Auto resolution: {w}x{h}")
        scale_filter = f"scale={w}:{h}"

    fps = pick_fps(video_bitrate_kbps, original_fps)

    if fps != original_fps:
        print(f"[/] FPS reduced: {original_fps:.2f} → {fps:.2f}")

    print("\n[/] Starting 2-pass encoding...\n")

    null_out = os.devnull

    print("[/] Pass 1: analysing...")
    pass1_cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-c:v", "libx264",
        "-b:v", f"{video_bitrate_kbps}k",
        "-pass", "1",
        "-an",
        "-f", "mp4",
        null_out
    ]

    subprocess.run(pass1_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("[/] Pass 2: encoding...\n")

    pass2_cmd = [
        "ffmpeg", "-y", "-i", input_file,
    ]

    if scale_filter:
        pass2_cmd += ["-vf", scale_filter]

    if fps != original_fps:
        pass2_cmd += ["-r", str(int(fps))]

    pass2_cmd += [
        "-c:v", "libx264",
        "-b:v", f"{video_bitrate_kbps}k",
        "-pass", "2",
        "-c:a", "aac",
        "-b:a", f"{audio_bitrate_kbps}k",
        output_file
    ]

    process = subprocess.Popen(
        pass2_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    current_time = 0
    start_time = time.time()

    for line in process.stdout:
        line = line.strip()

        match = re.search(r"time=(\d+:\d+:\d+\.\d+)", line)
        if match:
            current_time = parse_time_to_seconds(match.group(1))

            progress = min(current_time / duration, 1.0)

            elapsed = time.time() - start_time
            eta = (elapsed / progress - elapsed) if progress > 0 else 0

            bar = render_bar(progress)

            print(
                f"\r[/] [{bar}] {progress * 100:6.2f}% | ETA {format_eta(eta)}",
                end=""
            )

    print(
        f"\r[/] [{render_bar(1)}] {100:6.2f}% | ETA {format_eta(0)}",
        end=""
    )

    process.wait()
    print("\n")

    for f in ["ffmpeg2pass-0.log", "ffmpeg2pass-0.log.mbtree"]:
        if os.path.exists(f):
            os.remove(f)

    output_size = os.path.getsize(output_file)

    print(
        f"[+] Success: {output_file} "
        f"({output_size / (1024 * 1024):.2f} MB)"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Simple CLI tool for video compression using ffmpeg.",
        epilog=f"-- v{__version__}"
    )

    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", required=False)
    parser.add_argument("-s", "--size", required=True, type=float)

    parser.add_argument(
        "--adjust-resolution",
        action="store_true",
        help="Automatically reduce resolution based on target bitrate"
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: '{args.input}' doesn't exist.")
        sys.exit(1)

    if args.size <= 0:
        print("Error: Target size must be greater than 0 MB.")
        sys.exit(1)

    input_size_mb = get_file_size_mb(args.input)
    if args.size >= input_size_mb:
        print(
            f"Error: Target size ({args.size:.2f} MB) must be smaller than "
            f"input file ({input_size_mb:.2f} MB)."
        )
        sys.exit(1)

    if not args.output:
        _, ext = os.path.splitext(args.input)
        args.output = f"./output{ext}"

    compress_video(
        args.input,
        args.output,
        args.size,
        adjust_resolution=args.adjust_resolution
    )


if __name__ == "__main__":
    main()