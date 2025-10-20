#!/usr/bin/env python3
"""
Test script to verify the asyncio fixes.
"""

import sys
import uvicorn
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app import create_app

def main():
    """Test server on port 8001"""
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)
    logger.info("🧪 Starting TEST server with async fixes...")

    app = create_app()

    logger.info("📡 Test server URLs:")
    logger.info("  - https://localhost:8001/frontend")
    logger.info("  - https://10.43.1.247:8001/frontend")

    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8001,
            ssl_keyfile="certs/key.pem",
            ssl_certfile="certs/cert.pem",
            reload=False,
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Test server stopped")
    except Exception as e:
        logger.error(f"Test server error: {e}")

if __name__ == "__main__":
    main()