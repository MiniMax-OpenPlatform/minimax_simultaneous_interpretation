#!/usr/bin/env python3
"""
Remote access runner for the real-time translator application.
Configured for external network access.
"""

import os
import sys
import uvicorn
import logging
import socket
from pathlib import Path
from dotenv import load_dotenv

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app import create_app

def get_local_ip():
    """Get local IP address"""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def main():
    """Main entry point for remote access server"""
    # Load environment variables
    load_dotenv()

    # Configure logging
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Real-time Translator for REMOTE ACCESS...")

    # Check for required certificates
    ssl_keyfile = os.getenv("SSL_KEYFILE", "certs/key.pem")
    ssl_certfile = os.getenv("SSL_CERTFILE", "certs/cert.pem")

    # Get local IP for certificate generation guidance
    local_ip = get_local_ip()

    if not os.path.exists(ssl_keyfile) or not os.path.exists(ssl_certfile):
        logger.error(f"SSL certificates not found: {ssl_keyfile}, {ssl_certfile}")
        logger.info("Please generate SSL certificates with your actual IP address:")
        logger.info(f"openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj '/C=US/ST=CA/L=SF/O=RealTimeTranslator/CN={local_ip}' -addext 'subjectAltName=IP:{local_ip},IP:127.0.0.1,DNS:localhost'")
        sys.exit(1)

    # Create the FastAPI app
    app = create_app()

    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")  # Listen on all interfaces for remote access
    port = int(os.getenv("PORT", "8000"))  # Use configurable port

    # Get local IP for display
    local_ip = get_local_ip()

    logger.info(f"Server will start at https://0.0.0.0:{port}")
    logger.info("Access URLs:")
    logger.info(f"  - Local: https://localhost:{port}/frontend")
    logger.info(f"  - Network: https://{local_ip}:{port}/frontend")
    logger.info(f"  - API Docs: https://{local_ip}:{port}/docs")
    logger.info(f"  - Health Check: https://{local_ip}:{port}/health")
    logger.info("")
    logger.info("⚠️  IMPORTANT: Browsers will show security warnings for self-signed certificates.")
    logger.info("   Click 'Advanced' -> 'Proceed to [IP address] (unsafe)' to continue.")

    # Run the server
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            reload=False,
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()