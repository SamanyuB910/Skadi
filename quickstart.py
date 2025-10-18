"""Quick start script for Skadi demo."""
import asyncio
from datetime import datetime
from ingestors.mock_generators import MockDataGenerator
from core.logging import logger


async def generate_mock_data():
    """Generate mock telemetry data continuously."""
    generator = MockDataGenerator()
    rack_ids = generator.get_rack_ids()
    
    logger.info(f"Starting mock data generation for {len(rack_ids)} racks...")
    
    try:
        while True:
            # Generate batch
            ts = datetime.utcnow()
            samples = generator.generate_batch(ts, rack_ids)
            
            # In production, would POST to /telemetry
            # For now, just log
            logger.info(f"Generated {len(samples)} samples at {ts}")
            
            # Sleep based on tick rate
            from core.config import settings
            await asyncio.sleep(settings.mock_data_tick_s)
    
    except KeyboardInterrupt:
        logger.info("Mock data generation stopped")


if __name__ == '__main__':
    asyncio.run(generate_mock_data())
