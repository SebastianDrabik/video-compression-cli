import argparse
import subprocess
import os
import sys

__version__ = '0.2'

def get_video_duration(input_file):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_file
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except subprocess.CalledProcessError:
        print(f"Error: Can't read {input_file}. Is ffmpeg/ffprobe installed?")
        sys.exit(1)


def get_file_size_mb(path):
    return os.path.getsize(path) / (1024 * 1024)


def compress_video(input_file, output_file, target_size_mb):
    duration = get_video_duration(input_file)

    total_bitrate_kbps = (target_size_mb * 8192) / duration
    audio_bitrate_kbps = 128
    video_bitrate_kbps = total_bitrate_kbps - audio_bitrate_kbps

    if video_bitrate_kbps <= 0:
        print("Error: Output size is too small")
        sys.exit(1)

    print(f"[/] Duration: {duration:.2f} s")
    print(f"[/] Output size: {target_size_mb} MB")
    print(f"[/] Calculated video bitrate: {video_bitrate_kbps:.2f} kbps")

    null_out = os.devnull

    print("\n[/] Analysing...")
    pass1_cmd = [
        "ffmpeg", "-y", "-i", input_file, "-c:v", "libx264",
        "-b:v", f"{video_bitrate_kbps}k", "-pass", "1", "-an", "-f", "mp4", null_out
    ]
    subprocess.run(pass1_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("[/] Compression... (might take a while)")
    pass2_cmd = [
        "ffmpeg", "-y", "-i", input_file, "-c:v", "libx264",
        "-b:v", f"{video_bitrate_kbps}k", "-pass", "2", "-c:a", "aac",
        "-b:a", f"{audio_bitrate_kbps}k", output_file
    ]
    subprocess.run(pass2_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists("ffmpeg2pass-0.log"):
        os.remove("ffmpeg2pass-0.log")
    if os.path.exists("ffmpeg2pass-0.log.mbtree"):
        os.remove("ffmpeg2pass-0.log.mbtree")

    output_size = os.path.getsize(output_file)

    print(f"\n[+] Success: saved output file in: {output_file}({(output_size / (1024 * 1024)):.2f}MB)")


def main():
    parser = argparse.ArgumentParser(
        description="Simple CLI tool for video compression using ffmpeg.",
        epilog=f'-- v{__version__}'
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    parser.add_argument("-i", "--input", required=True, help="input file path")
    parser.add_argument("-o", "--output", required=False, help="output file path, (./output) by default")
    parser.add_argument("-s", "--size", required=True, type=float, help="output size in MB")

    # TODO
    # parser.add_argument("-r", "--resolution", required=False, help="output file resolution")

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
            f"the input file's current size ({input_size_mb:.2f} MB)."
        )
        sys.exit(1)

    if not args.output:
        _, extension = os.path.splitext(args.input)
        args.output = f"./output{extension}"

    compress_video(args.input, args.output, args.size)


if __name__ == "__main__":
    main()