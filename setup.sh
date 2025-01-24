#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define the directory for the virtual environment
VENV_DIR=".venv"

# Check if the .venv directory already exists
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists. Skipping creation."
else
    # Create a virtual environment
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv $VENV_DIR
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source $VENV_DIR/bin/activate

# Upgrade pip to the latest version
echo "Upgrading pip..."
pip install --upgrade pip

# Install the required packages
if [ -f "requirements.txt" ]; then
    echo "Installing packages from requirements.txt..."
    pip install -r requirements.txt
else
    echo "requirements.txt not found. Skipping package installation."
fi

# Additional setup tasks can be added here
# For example, setting environment variables or other configurations
echo "Performing additional setup tasks..."
# export SOME_ENV_VAR=some_value

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file with template values..."
    cat > .env << EOL
# JIRA Settings
JIRA_API_TOKEN=your_base64_encoded_token_here
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your_email@example.com

# Google Cloud Settings
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json

# Vertex AI Settings
GCP_PROJECT_ID=your-project-id
VERTEX_MODEL_VERSION=gemini-1.5-pro
VERTEX_LOCATION=us-central1
VERTEX_API_ENDPOINT=us-central1-aiplatform.googleapis.com
EOL
    echo "Created .env file with template values. Please update with your actual values."
fi

# Create necessary directories
echo "Creating required directories..."
mkdir -p execution_plans
mkdir -p proposed_tickets
mkdir -p logs

echo "Setup complete! Don't forget to update the .env file with your actual credentials."
