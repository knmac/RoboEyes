"""RoboEyes - Animated robot eyes display with remote control support.

Usage:
    uv run main.py [OPTIONS]           Start the eye display
    uv run main.py send <JSON> [OPTS]  Send a UDP command to a running instance

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

import json
import socket
import sys


def send_command(json_str: str, host: str = "127.0.0.1", port: int = 5005) -> None:
    """Send a JSON command string to a running RoboEyes instance via UDP."""
    json.loads(json_str)  # validate
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(json_str.encode(), (host, port))


def main() -> None:
    # If first positional arg is "send", handle it directly
    if len(sys.argv) > 1 and sys.argv[1] == "send":
        import argparse
        parser = argparse.ArgumentParser(prog="main.py send",
                                         description="Send a UDP command to RoboEyes")
        parser.add_argument("json_cmd", help="JSON command string")
        parser.add_argument("--port", type=int, default=5005)
        parser.add_argument("--bind", default="127.0.0.1")
        args = parser.parse_args(sys.argv[2:])
        send_command(args.json_cmd, args.bind, args.port)
    else:
        # Default: run the display (pass all args through to app.main's argparse)
        from roboeyes.app import main as run_app
        run_app()


if __name__ == "__main__":
    main()
