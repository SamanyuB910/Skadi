"""Demo data generator that posts telemetry to the API."""
import asyncio
import httpx
from datetime import datetime
from ingestors.mock_generators import MockDataGenerator
from core.logging import logger
from core.config import settings


async def run_demo_generator(api_url: str = "http://localhost:8000", duration_minutes: int = 60):
    """Generate and post mock telemetry to the API.
    
    Args:
        api_url: Base URL of the API
        duration_minutes: How long to run (0 = infinite)
    """
    generator = MockDataGenerator()
    rack_ids = generator.get_rack_ids()
    
    logger.info(f"🚀 Starting demo data generator...")
    logger.info(f"   Posting to: {api_url}")
    logger.info(f"   Racks: {len(rack_ids)}")
    logger.info(f"   Duration: {duration_minutes} minutes" if duration_minutes > 0 else "   Duration: infinite")
    logger.info(f"   Tick rate: {settings.mock_data_tick_s}s")
    
    start_time = datetime.utcnow()
    ticks = 0
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            while True:
                # Check duration
                if duration_minutes > 0:
                    elapsed = (datetime.utcnow() - start_time).total_seconds() / 60.0
                    if elapsed >= duration_minutes:
                        logger.info(f"✅ Duration reached: {duration_minutes} minutes")
                        break
                
                # Generate batch
                ts = datetime.utcnow()
                samples = generator.generate_batch(ts, rack_ids)
                
                # Post to API
                try:
                    response = await client.post(
                        f"{api_url}/telemetry",
                        json={"samples": samples}
                    )
                    
                    if response.status_code == 200:
                        ticks += 1
                        if ticks % 10 == 0:
                            logger.info(f"✓ Posted {len(samples)} samples (tick #{ticks})")
                    else:
                        logger.error(f"❌ POST failed: {response.status_code}")
                
                except Exception as e:
                    logger.error(f"❌ Error posting telemetry: {e}")
                
                # Sleep
                await asyncio.sleep(settings.mock_data_tick_s)
        
        except KeyboardInterrupt:
            logger.info(f"⏹️  Stopped by user after {ticks} ticks")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Demo data generator for Skadi')
    parser.add_argument('--api-url', default='http://localhost:8000', help='API base URL')
    parser.add_argument('--duration', type=int, default=0, help='Duration in minutes (0=infinite)')
    
    args = parser.parse_args()
    
    asyncio.run(run_demo_generator(args.api_url, args.duration))
