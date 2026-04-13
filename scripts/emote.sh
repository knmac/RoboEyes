#!/usr/bin/env bash
# Express an emotion on a running RoboEyes instance via UDP.
# Usage: emote.sh <emotion> [--color R,G,B] [--duration SECS] [--port PORT] [--bind ADDR]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROBO_DIR="$SCRIPT_DIR/.."
SOUNDS_DIR="$ROBO_DIR/sounds"
COLORSCHEME="$SCRIPT_DIR/colorschemes/default.conf"

# ── Load color scheme ──
lookup_color() {
    grep -E "^$1=" "$COLORSCHEME" | head -1 | cut -d= -f2
}

HOST="127.0.0.1"
PORT=5005
COLOR=""
DURATION=""

# ── Emotion table: shape|anim|sound|duration|color_name|overlay ──
#
#   Emotion      Shape     Anim       Sound            Dur  Color     Overlay
#   ---------    -------   ---------  --------------   ---  --------  --------
#   neutral      default   blink      (none)             0  sky       (none)
#   happy        smile     blink      happy_sound        4  pink      blush
#   tired        tired     blink      tired_sound        4  overlay1  stress
#   angry        angry     shake      angry_sound        4  red       (none)
#   squint       squint    blink      squint_sound       4  peach     (none)
#   sleeping     sleep     breathing  (none)             0  lavender  bubbles
#   laughing     smile     bounce     happy_sound        4  green     (none)
#   surprised    default   shake      surprised_sound    4  yellow    (none)
#   witty        smile     wink_left  (none)             3  teal      (none)
#
get_emotion() {
    case "$1" in
        #              shape    anim       sound            dur  color     overlay
        neutral)   echo "default|blink||0|sky|"                    ;;
        happy)     echo "smile|blink|happy_sound|4|pink|blush"       ;;
        tired)     echo "tired|blink|tired_sound|4|overlay1|stress"   ;;
        angry)     echo "angry|shake|angry_sound|4|red|"           ;;
        squint)    echo "squint|blink|squint_sound|4|peach|"       ;;
        sleeping)  echo "sleep|breathing||0|lavender|bubbles"      ;;
        laughing)  echo "smile|bounce|happy_sound|4|green|"        ;;
        surprised) echo "default|shake|surprised_sound|4|yellow|"  ;;
        witty)     echo "smile|wink_left||3|teal|"                 ;;
        *) return 1;;
    esac
}

send_udp() {
    echo -n "$1" | nc -u -w0 "$HOST" "$PORT"
}

play_sound() {
    [ -z "$1" ] && return
    local path="$SOUNDS_DIR/${1}.wav"
    [ -f "$path" ] || return
    if command -v afplay &>/dev/null; then
        afplay "$path" &
    elif command -v paplay &>/dev/null; then
        paplay "$path" &
    elif command -v aplay &>/dev/null; then
        aplay -q "$path" &
    fi
}

usage() {
    echo "Usage: emote.sh <emotion> [OPTIONS]"
    echo ""
    echo "Emotions: neutral happy tired angry squint sleeping laughing surprised witty"
    echo ""
    echo "Options:"
    echo "  --color R,G,B      Override eye color"
    echo "  --duration SECS    Override auto-reset duration"
    echo "  --port PORT        UDP port (default: 5005)"
    echo "  --bind ADDR        UDP address (default: 127.0.0.1)"
    exit 1
}

# ── Parse args ──
EMOTION=""
while [ $# -gt 0 ]; do
    case "$1" in
        --color)    COLOR="$2"; shift 2;;
        --duration) DURATION="$2"; shift 2;;
        --port)     PORT="$2"; shift 2;;
        --bind)     HOST="$2"; shift 2;;
        --help|-h)  usage;;
        -*)         echo "Unknown option: $1"; usage;;
        *)          EMOTION="$1"; shift;;
    esac
done

[ -z "$EMOTION" ] && usage

# ── Look up emotion ──
EMO=$(get_emotion "$EMOTION") || { echo "Unknown emotion: $EMOTION"; usage; }

IFS='|' read -r SHAPE ANIM SOUND DUR COLOR_NAME OVERLAY <<< "$EMO"

# Resolve color from scheme
EMO_COLOR="$(lookup_color "$COLOR_NAME")"

# Apply overrides
[ -n "$DURATION" ] && DUR="$DURATION"

# Build JSON command
HAS_COLOR=false
CMD="{\"shape\":\"$SHAPE\",\"anim\":\"$ANIM\""
if [ -n "$COLOR" ]; then
    IFS=',' read -r R G B <<< "$COLOR"
    CMD="$CMD,\"color\":[$R,$G,$B]"
    HAS_COLOR=true
elif [ -n "$EMO_COLOR" ]; then
    IFS=',' read -r R G B <<< "$EMO_COLOR"
    CMD="$CMD,\"color\":[$R,$G,$B]"
    HAS_COLOR=true
fi
if [ -n "$OVERLAY" ]; then
    CMD="$CMD,\"overlay\":\"$OVERLAY\""
else
    CMD="$CMD,\"overlay\":null"
fi
CMD="$CMD}"

# Play sound and send command
play_sound "$SOUND"
send_udp "$CMD"

# Auto-reset after duration
if [ "$DUR" != "0" ] && [ -n "$DUR" ]; then
    (
        sleep "$DUR"
        RESET="{\"shape\":\"default\",\"anim\":\"blink\",\"overlay\":null"
        if [ "$HAS_COLOR" = true ]; then
            DEF="$(lookup_color sky)"
            DEF="${DEF:-0,255,255}"
            IFS=',' read -r R G B <<< "$DEF"
            RESET="$RESET,\"color\":[$R,$G,$B]"
        fi
        RESET="$RESET}"
        echo -n "$RESET" | nc -u -w0 "$HOST" "$PORT"
    ) &
fi
