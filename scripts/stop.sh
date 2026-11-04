#!/bin/bash
if pkill -f "python server/app.py" 2>/dev/null; then
    echo "Radar stopped."
else
    echo "Radar was not running."
fi
