import os
import sys
import asyncio
import traceback

# Force unbuffered output so Render captures every log line
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from bot_logic import start_bot

if __name__ == '__main__':
    try:
        asyncio.run(start_bot())
    except Exception as e:
        print(f"FATAL: {e}", flush=True)
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
