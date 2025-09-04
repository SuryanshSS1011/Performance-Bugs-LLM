#!/bin/bash
# setup_environment.sh - Setup the environment for performance bugs research
# =========================================================================

set -e

echo "============================================"
echo "Performance Bugs Research Environment Setup"
echo "============================================"

# Check Python version
echo -n "Checking Python version... "
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    echo "OK (Python $python_version)"
else
    echo "ERROR: Python 3.8+ required, found $python_version"
    exit 1
fi

# Check Java version
echo -n "Checking Java version... "
if command -v java &> /dev/null; then
    java_version=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}' | awk -F '.' '{print $1"."$2}')
    if [[ "$java_version" == "1.8" ]] || [[ "$java_version" == "8" ]]; then
        echo "OK (Java 8)"
    else
        echo "WARNING: Java 8 required for Defects4J, found Java $java_version"
    fi
else
    echo "ERROR: Java not found. Please install Java 8"
    exit 1
fi

# Check Git
echo -n "Checking Git... "
if command -v git &> /dev/null; then
    git_version=$(git --version | awk '{print $3}')
    echo "OK (Git $git_version)"
else
    echo "ERROR: Git not found"
    exit 1
fi

# Check Maven
echo -n "Checking Maven... "
if command -v mvn &> /dev/null; then
    mvn_version=$(mvn -version | head -n1 | awk '{print $3}')
    echo "OK (Maven $mvn_version)"
else
    echo "ERROR: Maven not found"
    exit 1
fi

# Create virtual environment
echo
echo "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo
echo "Installing Python requirements..."
pip install -r requirements.txt

# Install additional Java parsing library
echo
echo "Installing Java parsing library..."
pip install javalang

# Create runtime output directories
echo
echo "Creating output directories..."
directories=(
    "results/visualizations"
    "data/training"
    "data/explanations"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
    echo "  Created: $dir"
done

# Check for .env file
echo
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env and add your OpenAI API key"
else
    echo ".env file already exists"
fi

# Defects4J check (only required for reproducing extraction)
echo
if command -v defects4j &> /dev/null; then
    echo "Defects4J found on PATH"
else
    echo "Defects4J not on PATH. Only needed if reproducing bug extraction."
    echo "  See https://github.com/rjust/defects4j for setup."
fi

echo
echo "============================================"
echo "Environment setup complete!"
echo "============================================"
echo
echo "Next steps:"
echo "1. Edit .env and add your OpenAI API key"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Run the pipeline: python main.py"
echo "4. Regenerate figures from the paper: python scripts/generate_paper_figures.py"