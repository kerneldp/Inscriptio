# RUN THIS ONCE: chmod +x start.sh

#!/bin/bash

echo "Initiating Inscriptio Launch Sequence..."

# Python Compatibility Checker 
echo "Checking Python compatibility..."

# First, explicitly check if python3.11 is installed
if command -v python3.11 &> /dev/null; then
    PYTHON_EXE="python3.11"
else
    # If not, check what the default python3 version is
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
    PY_MAJOR=$(echo $PY_VERSION | cut -d. -f1)
    PY_MINOR=$(echo $PY_VERSION | cut -d. -f2)

    if [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 9 ] && [ "$PY_MINOR" -le 11 ]; then
        PYTHON_EXE="python3"
    else
        echo "   ERROR: Incompatible Python version detected ($PY_VERSION)."
        echo "   TensorFlow requires Python 3.9, 3.10, or 3.11."
        echo "   Python 3.12 and above will cause the Machine Learning pipeline to crash."
        echo ""
        echo "   HOW TO FIX THIS (Mac):"
        echo "   Run this command in your terminal to install Python 3.11:"
        echo "   brew install python@3.11"
        echo ""
        echo "   After installing, run this launch script again!"
        exit 1
    fi
fi

echo "Valid Python found: using $PYTHON_EXE"
echo "----------------------------------------"

# 1. Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_EXE -m venv .venv
fi

# 2. Activate the virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# 3. Install requirements (Fast bypass)
echo "Checking and installing dependencies..."
pip install --prefer-binary -r inscriptio/python/requirements.txt


# 4. Trap Ctrl+C to cleanly shut down both servers at once
cleanup() {
    echo ""
    echo "Shutting down Inscriptio servers..."
    kill 0
}
trap cleanup EXIT

# 5. Start the Frontend Server (The '&' runs it concurrently)
echo "Starting Frontend Server (Port 5500)..."
python3 -m http.server 5500 &

# 6. Start the Backend API (The '&' runs it concurrently)
echo "Starting Backend API (Port 8000)..."
cd inscriptio/python
python -m uvicorn main:app --reload --port 8000 &

# 7. Wait 3 seconds for the ML model to load, then open the browser
sleep 3
echo "Opening Inscriptio..."
open "http://localhost:5500/inscriptio/html/01_authentication_portal.html"

# Keep the script running to hold the servers open
wait

# RUN THIS: ./start.sh