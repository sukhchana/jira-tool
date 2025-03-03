import os

from utils.env_loader import load_environment


def print_env_status():
    """Print the status of environment variables"""
    print("\nEnvironment Variables Status:")
    print("-" * 50)

    variables = {
        "Google Cloud Settings": [
            "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLOUD_LOCATION"
        ],
        "JIRA Settings": [
            "JIRA_API_TOKEN",
            "JIRA_SERVER",
            "JIRA_EMAIL"
        ]
    }

    for section, vars in variables.items():
        print(f"\n{section}:")
        for var in vars:
            value = os.getenv(var)
            status = "✓" if value else "✗"
            if value and var == "GOOGLE_APPLICATION_CREDENTIALS":
                from pathlib import Path
                path = Path(value)
                exists = path.exists()
                status = "✓ (file exists)" if exists else "✗ (file not found)"
            print(f"{status} {var}: {value or 'Not set'}")


if __name__ == "__main__":
    if load_environment():
        print("\n✓ Successfully loaded .env file")
        print_env_status()
    else:
        print("\n✗ Failed to load environment variables")
        print_env_status()
