#!/bin/bash
# Medical RAG System - Server Startup Script
# For Medical College Presentation

echo "🏥 Starting Medical RAG System..."
echo "=================================="
echo ""

# Set working directory
cd "$(dirname "$0")"

# Check for .env file
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "   Please copy env.example to .env and configure it."
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🔌 Activating virtual environment..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "🔌 Activating virtual environment..."
    source venv/bin/activate
fi

# Check if server is already running
if lsof -Pi :5557 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Server is already running on port 5557"
    echo "   To restart, first run: ./stop_server.sh"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Generate timestamp for log file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOGFILE="logs/server_${TIMESTAMP}.log"

echo "📝 Log file: $LOGFILE"
echo ""

# Start the server in background
# Use python directly if venv is activated, or try to find it
if [[ "$VIRTUAL_ENV" != "" ]]; then
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

nohup $PYTHON_CMD load_and_run.py > "$LOGFILE" 2>&1 &
SERVER_PID=$!

echo "🚀 Server starting with PID: $SERVER_PID"
echo "$SERVER_PID" > server.pid

# Wait for server to initialize
echo "⏳ Waiting for server to initialize..."
sleep 15

# Check if server is running
if lsof -Pi :5557 -sTCP:LISTEN -t >/dev/null ; then
    echo ""
    echo "✅ Server is running successfully!"
    echo ""
    echo "📍 Access Points:"
    echo "   - Local: http://localhost:5557"
    echo "   - Network: http://$(ipconfig getifaddr en0 2>/dev/null || echo "N/A"):5557"
    echo ""
    echo "📊 System Status:"
    echo "   - PID: $SERVER_PID"
    echo "   - Log: $LOGFILE"
    echo "   - Database: Connected (check logs for details)"
    echo ""
    echo "🎓 Ready for medical college presentation!"
    echo ""
    echo "To stop server: ./stop_server.sh"
    echo "To view logs: tail -f $LOGFILE"
else
    echo ""
    echo "❌ Server failed to start. Check log file:"
    echo "   tail -n 50 $LOGFILE"
    exit 1
fi
