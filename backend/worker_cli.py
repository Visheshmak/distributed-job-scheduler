import argparse
import asyncio
import signal
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.logging import setup_logging, logger
from app.worker.engine import WorkerEngine
from app.db.init_db import init_db


async def main():
    parser = argparse.ArgumentParser(description="Distributed Job Scheduler Dedicated Worker CLI")
    parser.add_argument("--worker-id", type=str, default=None, help="Unique worker ID")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent execution slots")
    parser.add_argument("--polling-interval-ms", type=int, default=1000, help="Polling interval in milliseconds")
    parser.add_argument("--heartbeat-interval-ms", type=int, default=5000, help="Heartbeat interval in milliseconds")
    parser.add_argument("--batch-size", type=int, default=5, help="Max jobs to claim per transaction")
    
    args = parser.parse_args()

    setup_logging()
    logger.info(f"Starting standalone worker process...")
    
    # Ensure database schema is ready
    await init_db()

    engine = WorkerEngine(
        worker_id=args.worker_id,
        concurrency=args.concurrency,
        polling_interval_ms=args.polling_interval_ms,
        heartbeat_interval_ms=args.heartbeat_interval_ms,
        batch_size=args.batch_size,
    )

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handle_signal():
        logger.info("Signal received. Initiating worker shutdown...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            # Signal handling on Windows
            pass

    await engine.start()

    try:
        if sys.platform == "win32":
            while not stop_event.is_set():
                await asyncio.sleep(0.5)
        else:
            await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Keyboard interrupt received.")
    finally:
        await engine.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
