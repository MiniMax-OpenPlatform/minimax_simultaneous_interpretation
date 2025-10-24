#!/bin/bash
# Real-time Translator Server Restart Script

echo "🔄 Restarting Real-time Translator Server..."

# Stop existing server processes
echo "🛑 Stopping existing server processes..."
pkill -f "python run_remote.py" 2>/dev/null || true
sleep 2

# Force kill if still running
echo "🔪 Force killing any remaining processes on port 8867..."
fuser -k 8867/tcp 2>/dev/null || true
sleep 1

# Change to project directory
cd "$(dirname "$0")"
echo "📁 Working directory: $(pwd)"

# Start server
echo "🚀 Starting server on port 8867..."
python run_remote.py &

# Get the new process ID
sleep 2
PID=$(pgrep -f "python run_remote.py")

if [ ! -z "$PID" ]; then
    echo "✅ Server started successfully!"
    echo "🆔 Process ID: $PID"
    echo "🌐 Access URL: https://10.43.1.247:8867/frontend"
    echo "📚 API Docs: https://10.43.1.247:8867/docs"
    echo ""
    echo "To stop the server, run: kill $PID"
else
    echo "❌ Failed to start server!"
    exit 1
fi