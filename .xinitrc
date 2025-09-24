#!/bin/bash
xset -dpms          # gasi power management
xset s off          # gasi screen saver
xset s noblank      # gasi blank ekran

source ./venv/bin/activate
exec python3 ./main.py
