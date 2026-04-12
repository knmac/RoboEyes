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

from roboeyes.app import main

if __name__ == "__main__":
    main()
