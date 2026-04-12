"""Application entry point: display setup, main loop, and keyboard handling."""

from __future__ import annotations

import argparse
import json
import socket

import pygame

from roboeyes.commands import handle_command, parse_color
from roboeyes.eyes import RoboEyes
from roboeyes.overlay import clear_cache, draw_help_overlay
from roboeyes.types import (
    Color,
    MAX_UDP_MESSAGES_PER_FRAME,
    Position,
    Shape,
)


def setup_display(
    fullscreen: bool, width: int, height: int, rotate: int,
    bg_color: Color, eye_color: Color,
    desktop_size: tuple[int, int] | None = None,
) -> tuple[pygame.Surface, pygame.Surface, RoboEyes]:
    """Creates the window, draw surface, and RoboEyes instance."""
    if fullscreen:
        if desktop_size is None:
            info = pygame.display.Info()
            desk_w, desk_h = info.current_w, info.current_h
        else:
            desk_w, desk_h = desktop_size
        if rotate in (90, 270):
            draw_width, draw_height = desk_h, desk_w
        else:
            draw_width, draw_height = desk_w, desk_h
        window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        draw_width, draw_height = width, height
        if rotate in (90, 270):
            win_w, win_h = draw_height, draw_width
        else:
            win_w, win_h = draw_width, draw_height
        window = pygame.display.set_mode((win_w, win_h))

    pygame.display.set_caption("RoboEyes Simulation")
    draw_surface = pygame.Surface((draw_width, draw_height))

    robo_eyes = RoboEyes(draw_surface, width=draw_width, height=draw_height,
                         bg_color=bg_color, eye_color=eye_color)
    robo_eyes.begin()
    return window, draw_surface, robo_eyes


def main() -> None:
    """Entry point: parses arguments, starts pygame, and runs the main loop."""
    parser = argparse.ArgumentParser(
        description="RoboEyes - Animated robot eyes display",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--rotate", type=int, default=0, choices=[0, 90, 180, 270],
                        help="Rotation angle in degrees (default: 0)")
    parser.add_argument("--port", type=int, default=5005,
                        help="UDP port for remote commands (default: 5005)")
    parser.add_argument("--bind", default="127.0.0.1",
                        help="Bind address for UDP (default: 127.0.0.1)")
    parser.add_argument("--color", type=parse_color, default="0,255,255",
                        help="Eye color as R,G,B (default: 0,255,255)")
    parser.add_argument("--bgcolor", type=parse_color, default="0,0,0",
                        help="Background color as R,G,B (default: 0,0,0)")
    parser.add_argument("--width", type=int, default=640,
                        help="Canvas width in pixels (default: 640)")
    parser.add_argument("--height", type=int, default=480,
                        help="Canvas height in pixels (default: 480)")
    parser.add_argument("--fullscreen", action="store_true",
                        help="Run in fullscreen mode")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setblocking(False)
        sock.bind((args.bind, args.port))
        print(f"Listening for commands on UDP {args.bind}:{args.port}")

        pygame.init()
        try:
            info = pygame.display.Info()
            desktop_size: tuple[int, int] = (info.current_w, info.current_h)

            is_fullscreen: bool = args.fullscreen
            window, draw_surface, robo_eyes = setup_display(
                is_fullscreen, args.width, args.height, args.rotate,
                args.bgcolor, args.color, desktop_size,
            )
            robo_eyes.set_shape(Shape.DEFAULT)
            robo_eyes.set_autoblinker(True, interval=2, variation=3)
            robo_eyes.set_idle_mode(True, interval=5, variation=5)
            robo_eyes.set_curiosity(True)

            show_help = False
            clock = pygame.time.Clock()

            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            return
                        elif event.key == pygame.K_0:
                            robo_eyes.set_shape(Shape.DEFAULT)
                        elif event.key == pygame.K_1:
                            robo_eyes.set_shape(Shape.DROOPY)
                        elif event.key == pygame.K_2:
                            robo_eyes.set_shape(Shape.FROWN)
                        elif event.key == pygame.K_3:
                            robo_eyes.set_shape(Shape.CHEERFUL)
                        elif event.key == pygame.K_4:
                            robo_eyes.set_shape(Shape.SQUINT)
                        elif event.key == pygame.K_5:
                            robo_eyes.set_shape(Shape.CLOSED)
                        elif event.key == pygame.K_c:
                            robo_eyes.anim_confused()
                        elif event.key == pygame.K_l:
                            robo_eyes.anim_laugh()
                        elif event.key == pygame.K_s:
                            robo_eyes.anim_breathing()
                        elif event.key == pygame.K_b:
                            robo_eyes.blink()
                        elif event.key == pygame.K_q:
                            robo_eyes.wink_left()
                        elif event.key == pygame.K_e:
                            robo_eyes.wink_right()
                        elif event.key == pygame.K_LEFT:
                            robo_eyes.set_position(Position.W)
                        elif event.key == pygame.K_RIGHT:
                            robo_eyes.set_position(Position.E)
                        elif event.key == pygame.K_UP:
                            robo_eyes.set_position(Position.N)
                        elif event.key == pygame.K_DOWN:
                            robo_eyes.set_position(Position.S)
                        elif event.key == pygame.K_SPACE:
                            robo_eyes.set_position(Position.CENTER)
                        elif event.key == pygame.K_f:
                            is_fullscreen = not is_fullscreen
                            clear_cache()
                            old = robo_eyes
                            window, draw_surface, robo_eyes = setup_display(
                                is_fullscreen, args.width, args.height,
                                args.rotate, old.bg_color, old.eye_color,
                                desktop_size,
                            )
                            robo_eyes.set_shape(old.current_shape)
                            robo_eyes.set_autoblinker(
                                old.autoblinker,
                                interval=old.blink_interval // 1000,
                                variation=old.blink_interval_variation // 1000,
                            )
                            robo_eyes.set_idle_mode(
                                old.idle,
                                interval=old.idle_interval // 1000,
                                variation=old.idle_interval_variation // 1000,
                            )
                            robo_eyes.set_curiosity(old.curious)
                            robo_eyes.set_cyclops(old.cyclops)
                        elif event.key == pygame.K_SLASH and (event.mod & pygame.KMOD_SHIFT):
                            show_help = not show_help

                # Process UDP commands (bounded per frame)
                for _ in range(MAX_UDP_MESSAGES_PER_FRAME):
                    try:
                        data, _ = sock.recvfrom(1024)
                        try:
                            cmd = json.loads(data.decode())
                            handle_command(cmd, robo_eyes)
                        except (json.JSONDecodeError, ValueError):
                            pass
                    except BlockingIOError:
                        break

                robo_eyes.update()

                if args.rotate:
                    rotated = pygame.transform.rotate(draw_surface, -args.rotate)
                    window.fill(robo_eyes.bg_color)
                    window.blit(rotated, rotated.get_rect(center=window.get_rect().center))
                else:
                    window.blit(draw_surface, (0, 0))

                if show_help:
                    draw_help_overlay(window)

                pygame.display.flip()
                clock.tick(50)
        finally:
            pygame.quit()
    finally:
        sock.close()
