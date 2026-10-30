import logging
import os
import subprocess
import sys
import time
from pathlib import Path

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("logs/pipeline.log"), logging.StreamHandler()],
)
log = logging.getLogger("pipeline")

STEPS = ["generate", "ingest", "validate", "load"]
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 5


def run_step(name: str) -> None:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        log.info("step=%s attempt=%d start", name, attempt)
        start = time.time()
        result = subprocess.run([sys.executable, f"src/{name}.py"],
                                capture_output=True, text=True, encoding="utf-8",
                                env={**os.environ, "PYTHONUTF8": "1"},
                                )
        elapsed = time.time() - start
        if result.returncode == 0:
            log.info("step=%s ok in %.1fs | %s", name, elapsed,
                     result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "")
            return
        log.error("step=%s failed (attempt %d): %s", name, attempt, result.stderr.strip()[-500:])
        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF_SECONDS * attempt)
    raise RuntimeError(f"step {name} failed after {MAX_ATTEMPTS} attempts")


if __name__ == "__main__":
    try:
        for step in STEPS:
            run_step(step)
        log.info("pipeline finished successfully")
    except RuntimeError as e:
        log.error("pipeline aborted: %s", e)
        sys.exit(1)