"""RoboEyes - Animated robot eyes display with remote control support.

Usage:
    uv run main.py [OPTIONS]

Options:
    --rotate {0,90,180,270}   Screen rotation in degrees (default: 0)
    --port PORT               UDP port for remote commands (default: 5005)
    --bind ADDRESS            Bind address for UDP (default: 127.0.0.1)
    --color R,G,B             Eye color (default: 0,255,255)
    --bgcolor R,G,B           Background color (default: 0,0,0)
    --width WIDTH             Canvas width in pixels (default: 640)
    --height HEIGHT           Canvas height in pixels (default: 480)
    --fullscreen              Run in fullscreen mode
"""

import sys
import argparse
import socket
import json
from roboeyes.app import main as run_app

def send_command(cmd_str, port=5005, bind_address="127.0.0.1"):
    try:
        # Validate JSON
        json.loads(cmd_str)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(cmd_str.encode('utf-8'), (bind_address, port))
    except Exception as e:
        print(f"Error sending command: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="RoboEyes: Animated robot eyes.")
    subparsers = parser.add_subparsers(dest="command")

    # 'run' subcommand (or default if no args)
    run_parser = subparsers.add_parser("run", help="Start the eye display.")
    run_parser.add_argument("--rotate", type=int, default=0, choices=[0, 90, 180, 270])
    run_parser.add_argument("--port", type=int, default=5005)
    run_parser.add_argument("--bind", type=str, default="127.0.0.1")
    run_parser.add_argument("--color", type=str, default="0,255,255")
    run_parser.add_argument("--bgcolor", type=str, default="0,0,0")
    run_parser.add_argument("--width", type=int, default=640)
    run_parser.add_argument("--height", type=int, default=480)
    run_parser.add_argument("--fullscreen", action="store_true")

    # 'send' subcommand
    send_parser = subparsers.add_parser("send", help="Send a command to a running RoboEyes instance.")
    send_parser.add_argument("json_cmd", help="JSON command string.")
    send_parser.add_argument("--port", type=int, default=5005)
    send_parser.add_argument("--bind", type=str, default="127.0.0.1")

    # Handle default 'run' case
    if len(sys.argv) == 1:
        run_app()
        return

    # If first arg is not a subcommand but looks like a flag, assume 'run'
    if len(sys.argv) > 1 and sys.argv[1].startswith("--") and sys.argv[1] != "--help":
        run_app()
        return

    args = parser.parse_args()
    if args.command == "send":
        send_command(args.json_cmd, args.port, args.bind)
    else:
        # Re-parse sys.argv for the run_app's argparse (legacy compatibility)
        sys.argv.remove("run") if "run" in sys.argv else None
        run_app()

if __name__ == "__main__":
    main()
