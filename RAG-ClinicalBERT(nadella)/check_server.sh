#!/bin/bash
# Medical RAG System - Server Status Check

echo "🏥 Medical RAG System - Server Status"
echo "======================================"
echo ""

# Check if server is running on port 5557
if lsof -Pi :5557 -sTCP:LISTEN -t >/dev/null ; then
    PID=$(lsof -ti :5557)
    echo "✅ Server Status: RUNNING"
    echo ""
    echo "📊 Details:"
    echo "   - PID: $PID"
    echo "   - Port: 5557"
    echo "   - URL: http://localhost:5557"
    
    # Get network IP if available
    NETWORK_IP=$(ipconfig getifaddr en0 2>/dev/null)
    if [ ! -z "$NETWORK_IP" ]; then
        echo "   - Network: http://$NETWORK_IP:5557"
    fi
    
    # Check uptime
    if [ -f server.pid ]; then
        echo "   - PID File: Found"
    fi
    
    echo ""
    echo "🧪 Quick Test:"
    echo "   curl http://localhost:5557/api/health"
    echo ""
    
    # Try health check
    HEALTH=$(curl -s http://localhost:5557/api/health 2>/dev/null)
    if [ ! -z "$HEALTH" ]; then
        echo "   Response: $HEALTH"
    fi
    
else
    echo "❌ Server Status: NOT RUNNING"
    echo ""
    echo "To start server: ./start_server.sh"
fi

echo ""
