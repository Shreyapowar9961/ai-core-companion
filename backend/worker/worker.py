import asyncio
import logging
import sys
import os

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from worker.tasks import (
    process_scheduled_outbound_calls,
    process_failed_call_retries,
    process_alert_sla_monitor,
    process_daily_progress_and_summaries
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (Worker) %(message)s"
)
logger = logging.getLogger("worker")

async def run_worker():
    logger.info("AI Care Companion Background Worker started successfully.")
    logger.info("Monitoring scheduled calls, retries, alert SLAs, and progress scoring...")
    
    cycle = 0
    while True:
        try:
            # 1. Check Alert SLA violations every 30 seconds
            await process_alert_sla_monitor()

            # 2. Process failed call retries every 60 seconds
            if cycle % 2 == 0:
                await process_failed_call_retries()

            # 3. Process scheduled outbound calls every 2 minutes
            if cycle % 4 == 0:
                await process_scheduled_outbound_calls()

            # 4. Periodic progress score recalculation every 10 minutes
            if cycle % 20 == 0:
                await process_daily_progress_and_summaries()

            cycle += 1
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Worker cycle error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
