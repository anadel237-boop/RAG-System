#!/bin/bash
# Medical RAG System - Server Stop Script

echo "🛑 Stopping Medical RAG System..."
echo ""

# Check if PID file exists
if [ -f server.pid ]; then
    PID=$(cat server.pid)
    
    if ps -p $PID > /dev/null; then
        echo "Stopping server (PID: $PID)..."
        kill $PID
        sleep 2
        
        # Force kill if still running
        if ps -p $PID > /dev/null; then
            echo "Force stopping server..."
            kill -9 $PID
        fi
        
        rm server.pid
        echo "✅ Server stopped successfully"
    else
        echo "⚠️  Server not running (PID: $PID not found)"
        rm server.pid
    fi
else
    # Try to find and kill process on port 5557
    PID=$(lsof -ti :5557)
    if [ ! -z "$PID" ]; then
        echo "Found server on port 5557 (PID: $PID)"
        kill $PID
        sleep 2
        echo "✅ Server stopped"
    else
        echo "ℹ️  No server running on port 5557"
    fi
fi

echo ""
