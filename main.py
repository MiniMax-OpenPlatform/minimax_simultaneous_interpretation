"""
Main entry point for the real-time translator application.
"""

import uvicorn
import logging
from backend.app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main entry point"""
    app = create_app()

    # Run with HTTPS
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="certs/key.pem",
        ssl_certfile="certs/cert.pem"
    )

if __name__ == "__main__":
    main()
