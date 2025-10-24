#!/usr/bin/env python3
"""
Development runner for the real-time translator application.
Provides easy startup with environment variable loading.
"""

import os
import sys
import uvicorn
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app import create_app

def main():
    """Main entry point for development server"""
    # Load environment variables
    load_dotenv()

    # Configure logging
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Real-time Translator development server...")

    # Check for required certificates
    ssl_keyfile = os.getenv("SSL_KEYFILE", "certs/key.pem")
    ssl_certfile = os.getenv("SSL_CERTFILE", "certs/cert.pem")

    if not os.path.exists(ssl_keyfile) or not os.path.exists(ssl_certfile):
        logger.error(f"SSL certificates not found: {ssl_keyfile}, {ssl_certfile}")
        logger.info("Please run: openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj '/C=US/ST=CA/L=SF/O=RealTimeTranslator/CN=localhost'")
        sys.exit(1)

    # Create the FastAPI app
    app = create_app()

    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    logger.info(f"Server will start at https://{host}:{port}")
    logger.info("Access the web interface at: https://localhost:8000/frontend")
    logger.info("API documentation at: https://localhost:8000/docs")

    # Run the server
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            reload=False,  # Disable reload for production-like behavior
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()