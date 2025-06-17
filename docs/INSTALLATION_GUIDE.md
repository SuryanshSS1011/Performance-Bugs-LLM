# Installation Guide

This guide provides detailed instructions for setting up the Performance Bugs research environment.

## Table of Contents
- [System Requirements](#system-requirements)
- [Quick Setup](#quick-setup)
- [Detailed Installation](#detailed-installation)
- [Troubleshooting](#troubleshooting)
- [Verification](#verification)

## System Requirements

### Hardware
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 50GB free space
- **GPU**: Not required (CPU inference is sufficient)

### Operating System
- Ubuntu 18.04+ (recommended)
- macOS 10.14+
- Windows 10+ with WSL2

### Software Prerequisites
- Python 3.8+
- Java 8 (required for Defects4J)
- Git 2.0+
- Maven 3.6+
- Node.js 14+ (optional, for notebooks)

## Quick Setup

For experienced users, run the automated setup:

```bash
# Clone the repository
git clone https://github.com/yourusername/performance-bugs-llm.git
cd performance-bugs-llm

# Run setup script
chmod +x scripts/setup_environment.sh
./scripts/setup_environment.sh

# Configure API keys
cp .env.example .env
# Edit .env and add your OpenAI API key

# Verify installation
source venv/bin/activate
python scripts/validate_dataset.py
```

## Detailed Installation

### Step 1: Install System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y \
    python3.8 python3.8-dev python3-pip \
    openjdk-8-jdk maven ant gradle \
    git curl wget build-essential \
    subversion perl
```

#### macOS
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.8 openjdk@8 maven ant gradle git svn perl
```

#### Windows (WSL2)
```bash
# In WSL2 Ubuntu terminal
sudo apt-get update
sudo apt-get install -y \
    python3.8 python3.8-dev python3-pip \
    openjdk-8-jdk maven ant gradle \
    git curl wget build-essential
```

### Step 2: Set Up Java 8

Defects4J requires Java 8 specifically:

```bash
# Verify Java version
java -version

# If not Java 8, set JAVA_HOME
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH

# Add to ~/.bashrc for persistence
echo 'export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64' >> ~/.bashrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
```

### Step 3: Clone Repository

```bash
git clone https://github.com/yourusername/performance-bugs-llm.git
cd performance-bugs-llm
```

### Step 4: Create Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### Step 5: Install Defects4J

```bash
# Run the installation script
chmod +x scripts/download_defects4j.sh
./scripts/download_defects4j.sh

# Or install manually
git clone https://github.com/rjust/defects4j.git
cd defects4j
./init.sh
cd ..

# Add to PATH
export PATH=$PATH:$(pwd)/defects4j/framework/bin
```

### Step 6: Configure API Keys

```bash
# Copy environment template
cp .env.example .env

# Edit .env file
nano .env  # or use your preferred editor
```

Add your OpenAI API key:
```
OPENAI_API_KEY=sk-...your-key-here...
```

### Step 7: Download Dataset

The dataset is included in the repository. Verify it:

```bash
python scripts/validate_dataset.py --dataset dataset/performance_bugs_490.json
```

## Verification

Run these commands to verify your installation:

```bash
# Check Python
python --version

# Check Java
java -version
javac -version

# Check Maven
mvn --version

# Check Git
git --version

# Check Defects4J
defects4j info -p Chart

# Check Python packages
python -c "import pandas, numpy, sklearn, openai; print('All packages installed')"

# Validate dataset
python scripts/validate_dataset.py
```

## Troubleshooting

### Common Issues

#### 1. Java Version Mismatch
```bash
# Error: Defects4J requires Java 8
# Solution: Install Java 8 and set JAVA_HOME
sudo update-alternatives --config java
# Select Java 8
```

#### 2. Permission Denied
```bash
# Error: Permission denied when running scripts
# Solution: Make scripts executable
chmod +x scripts/*.sh
chmod +x extraction/original_workflow/*.sh
```

#### 3. OpenAI API Error
```bash
# Error: OpenAI API key not found
# Solution: Ensure .env file exists and contains valid key
cat .env | grep OPENAI_API_KEY
```

#### 4. Memory Issues
```bash
# Error: Out of memory during extraction
# Solution: Increase Java heap size
export _JAVA_OPTIONS="-Xmx4g"
```

#### 5. Missing Dependencies
```bash
# Error: Module not found
# Solution: Reinstall requirements
pip install --force-reinstall -r requirements.txt
```

### Platform-Specific Issues

#### macOS
- If you encounter SSL certificate errors:
  ```bash
  pip install --upgrade certifi
  ```

#### Windows
- Use WSL2 for best compatibility
- Ensure line endings are LF, not CRLF:
  ```bash
  git config --global core.autocrlf false
  ```

#### Linux
- If you encounter locale errors:
  ```bash
  export LC_ALL=C.UTF-8
  export LANG=C.UTF-8
  ```

## Next Steps

After successful installation:

1. **Explore the dataset**:
   ```bash
   jupyter notebook notebooks/data_exploration.ipynb
   ```

2. **Run a simple bug detection**:
   ```bash
   python model/inference/detect_performance_bugs.py --file examples/Sample.java
   ```

3. **Fine-tune the model** (optional):
   ```bash
   python model/fine_tuning/fine_tune_gpt4o_mini.py --dataset dataset/performance_bugs_490.json
   ```

4. **Reproduce paper results**:
   ```bash
   ./scripts/reproduce_paper_results.sh
   ```

## Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Search existing [GitHub Issues](https://github.com/yourusername/performance-bugs-llm/issues)
3. Create a new issue with:
   - Your OS and Python version
   - Complete error message
   - Steps to reproduce

## Additional Resources

- [Defects4J Documentation](https://github.com/rjust/defects4j/wiki)
- [OpenAI Fine-tuning Guide](https://platform.openai.com/docs/guides/fine-tuning)
- [Paper: Fixing Performance Bugs Through LLM Explanations](https://arxiv.org/abs/your-paper)