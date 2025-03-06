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

# Check for parent jira-tool directory
PARENT_JIRA_TOOL="../jira-tool"
if [ -d "$PARENT_JIRA_TOOL" ]; then
    echo "Found parent jira-tool directory..."
    
    # Check for and copy .env file from parent jira-tool directory
    if [ -f "$PARENT_JIRA_TOOL/.env" ]; then
        echo "Found .env file in parent jira-tool directory. Copying..."
        cp "$PARENT_JIRA_TOOL/.env" ./.env
        echo "Copied .env file from parent directory."
    fi
    
    # Check for and copy config directory
    if [ -d "$PARENT_JIRA_TOOL/config" ]; then
        echo "Found config directory in parent jira_tool. Copying..."
        mkdir -p ./config
        cp -R "$PARENT_JIRA_TOOL/config/"* ./config/
        echo "Copied config directory from parent."
    fi
    
    # Check for and copy assets directory
    if [ -d "$PARENT_JIRA_TOOL/assets" ]; then
        echo "Found assets directory in parent jira_tool. Copying..."
        mkdir -p ./assets
        cp -R "$PARENT_JIRA_TOOL/assets/"* ./assets/
        echo "Copied assets directory from parent."
    fi
    
    # Check for and copy helm directory
    if [ -d "$PARENT_JIRA_TOOL/helm" ]; then
        echo "Found helm directory in parent jira_tool. Copying..."
        mkdir -p ./helm
        cp -R "$PARENT_JIRA_TOOL/helm/"* ./helm/
        echo "Copied helm directory from parent."
    fi
    
    # Check for and copy Dockerfile
    if [ -f "$PARENT_JIRA_TOOL/Dockerfile" ]; then
        echo "Found Dockerfile in parent jira_tool. Copying..."
        cp "$PARENT_JIRA_TOOL/Dockerfile" ./Dockerfile
        echo "Copied Dockerfile from parent."
    fi
    
    # Check for and copy pipeline.yaml
    if [ -f "$PARENT_JIRA_TOOL/pipeline.yaml" ]; then
        echo "Found pipeline.yaml in parent jira_tool. Copying..."
        cp "$PARENT_JIRA_TOOL/pipeline.yaml" ./pipeline.yaml
        echo "Copied pipeline.yaml from parent."
    fi
    
    # Check for and copy specific files from llm directory
    if [ -d "$PARENT_JIRA_TOOL/llm" ]; then
        echo "Found llm directory in parent jira_tool."
        mkdir -p ./llm
        
        # Check and copy specific files
        for file in c_vertex.py m2m_helper.py vertexinit.py anthropicllm.py; do
            if [ -f "$PARENT_JIRA_TOOL/llm/$file" ]; then
                echo "Copying $file from parent llm directory..."
                cp "$PARENT_JIRA_TOOL/llm/$file" ./llm/
            fi
        done
        echo "Finished copying available llm files."
    fi
    
    # Check for and copy jira_auth_helper.py from jira_integration folder
    if [ -d "$PARENT_JIRA_TOOL/jira_integration" ]; then
        echo "Found jira_integration directory in parent jira_tool."
        
        if [ -f "$PARENT_JIRA_TOOL/jira_integration/jira_auth_helper.py" ]; then
            echo "Found jira_auth_helper.py in parent jira_integration directory. Copying..."
            mkdir -p ./jira_integration
            cp "$PARENT_JIRA_TOOL/jira_integration/jira_auth_helper.py" ./jira_integration/
            echo "Copied jira_auth_helper.py to local jira_integration directory."
        fi
    fi
fi

# Create .env file if it doesn't exist (after checking parent directory)
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
