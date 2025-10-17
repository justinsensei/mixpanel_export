#!/usr/bin/env python3
"""
Mixpanel to PostHog Export Tool

Exports historical event data from Mixpanel and saves it as uncompressed JSONL files
for PostHog S3 import with automatic Mixpanel transformation.

Usage:
    python export_mixpanel.py

The script will prompt for date range interactively.
"""

import os
import sys
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv


# ============================================================================
# Configuration Loading
# ============================================================================

def load_config():
    """Load and validate environment variables from .env file.

    Returns:
        dict: Configuration dictionary with credentials and settings

    Raises:
        SystemExit: If required environment variables are missing
    """
    # Load .env file
    load_dotenv()

    # Required variables
    required_vars = {
        'MIXPANEL_SERVICE_ACCOUNT_USERNAME': os.getenv('MIXPANEL_SERVICE_ACCOUNT_USERNAME'),
        'MIXPANEL_SERVICE_ACCOUNT_SECRET': os.getenv('MIXPANEL_SERVICE_ACCOUNT_SECRET'),
        'MIXPANEL_PROJECT_ID': os.getenv('MIXPANEL_PROJECT_ID')
    }

    # Check for missing required variables
    missing = [key for key, value in required_vars.items() if not value]
    if missing:
        print("❌ Error: Missing Configuration")
        print(f"   Details: The following required environment variables are missing: {', '.join(missing)}")
        print("   Action: Check your .env file and ensure all required variables are set")
        sys.exit(1)

    # Optional variables with defaults
    config = {
        'username': required_vars['MIXPANEL_SERVICE_ACCOUNT_USERNAME'],
        'secret': required_vars['MIXPANEL_SERVICE_ACCOUNT_SECRET'],
        'project_id': required_vars['MIXPANEL_PROJECT_ID'],
        'api_base_url': os.getenv('MIXPANEL_API_BASE_URL', 'https://data.mixpanel.com/api/2.0'),
        'output_dir': os.getenv('EXPORT_OUTPUT_DIR', './exports')
    }

    return config


# ============================================================================
# Date Validation Functions
# ============================================================================

def validate_date_format(date_string):
    """Validate date string is in YYYY-MM-DD format and is a valid date.

    Args:
        date_string (str): Date string to validate

    Returns:
        datetime or None: Parsed datetime object if valid, None otherwise
    """
    try:
        parsed_date = datetime.strptime(date_string, '%Y-%m-%d')
        return parsed_date
    except ValueError:
        return None


def get_date_input(prompt):
    """Prompt user for a date and validate format.

    Args:
        prompt (str): Prompt message to display

    Returns:
        str: Valid date string in YYYY-MM-DD format
    """
    while True:
        date_string = input(prompt).strip()
        parsed_date = validate_date_format(date_string)

        if not parsed_date:
            print("❌ Invalid format. Please use YYYY-MM-DD (e.g., 2024-01-01)")
            continue

        # Check if date is in the future
        today = datetime.now().date()
        if parsed_date.date() > today:
            print(f"❌ Date cannot be in the future (today is {today.strftime('%Y-%m-%d')})")
            continue

        return date_string


def validate_date_range(from_date, to_date):
    """Validate that the date range is logical and warn if > 365 days.

    Args:
        from_date (str): Start date in YYYY-MM-DD format
        to_date (str): End date in YYYY-MM-DD format

    Returns:
        bool: True if user confirms to continue, False to re-enter dates
    """
    from_dt = datetime.strptime(from_date, '%Y-%m-%d')
    to_dt = datetime.strptime(to_date, '%Y-%m-%d')

    # Check end date is not before start date
    if to_dt < from_dt:
        print("❌ End date must be on or after start date")
        return False

    # Calculate range in days
    delta = to_dt - from_dt
    days = delta.days + 1  # Inclusive

    # Warn if range exceeds 365 days
    if days > 365:
        print(f"\n⚠️  Warning: Date range is {days} days ({days / 365:.1f} years)")
        print("    PostHog S3 imports support maximum 1-year ranges.")
        print("    You will need to split this file before importing to PostHog.")
        print()
        response = input("Continue with export? (y/n): ").strip().lower()
        if response != 'y':
            return False

    print(f"✓ Date range validated: {days} days")
    return True


def get_date_range_from_user():
    """Interactive prompts for date range with validation.

    Returns:
        tuple: (from_date, to_date) as strings in YYYY-MM-DD format
    """
    print("\nEnter export date range:")
    print()

    while True:
        from_date = get_date_input("From date (YYYY-MM-DD): ")
        to_date = get_date_input("To date (YYYY-MM-DD): ")

        if validate_date_range(from_date, to_date):
            return from_date, to_date
        print()


# ============================================================================
# Mixpanel API Integration
# ============================================================================

def export_from_mixpanel(config, from_date, to_date):
    """Call Mixpanel API and retrieve raw event data.

    Args:
        config (dict): Configuration with credentials and settings
        from_date (str): Start date in YYYY-MM-DD format
        to_date (str): End date in YYYY-MM-DD format

    Returns:
        str: JSONL response body from Mixpanel

    Raises:
        SystemExit: If API request fails
    """
    url = f"{config['api_base_url']}/export"

    params = {
        'project_id': config['project_id'],
        'from_date': from_date,
        'to_date': to_date,
        'time_in_ms': 'true'  # Millisecond precision timestamps
    }

    headers = {
        'Accept': 'text/plain'  # Expecting JSONL response
    }

    # Use HTTP Basic Auth with service account credentials
    auth = (config['username'], config['secret'])

    print("\nExporting data from Mixpanel...")

    try:
        response = requests.get(url, params=params, headers=headers, auth=auth, timeout=300)

        # Handle different response codes
        if response.status_code == 200:
            print("✓ API request successful")
            return response.text
        elif response.status_code == 401:
            print("❌ Error: API Authentication Failed (401)")
            print("   Details: Invalid service account credentials")
            print("   Action: Verify credentials in .env are correct and not expired")
            sys.exit(1)
        elif response.status_code == 429:
            print("❌ Error: Rate Limit Exceeded (429)")
            print("   Details: Mixpanel API rate limit reached (60 requests/hour)")
            print("   Action: Wait before retrying (limits reset hourly)")
            sys.exit(1)
        else:
            print(f"❌ Error: API Request Failed ({response.status_code})")
            print(f"   Details: {response.text[:200]}")
            print("   Action: Check API documentation or contact support")
            sys.exit(1)

    except requests.exceptions.Timeout:
        print("❌ Error: Request Timeout")
        print("   Details: API request took longer than 5 minutes")
        print("   Action: Try a smaller date range or retry later")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: Network Error")
        print(f"   Details: {str(e)}")
        print("   Action: Check your internet connection and try again")
        sys.exit(1)


# ============================================================================
# File Operations
# ============================================================================

def save_to_file(data, from_date, to_date, output_dir):
    """Write JSONL data to local file with descriptive filename.

    Args:
        data (str): JSONL content to write
        from_date (str): Start date in YYYY-MM-DD format
        to_date (str): End date in YYYY-MM-DD format
        output_dir (str): Directory to save the file

    Returns:
        str: Full path to the created file

    Raises:
        SystemExit: If file write fails
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"❌ Error: Failed to create output directory")
        print(f"   Details: {str(e)}")
        print("   Action: Check directory permissions")
        sys.exit(1)

    # Generate filename
    filename = f"mixpanel_export_{from_date}_to_{to_date}.jsonl"
    filepath = output_path / filename

    print(f"✓ Writing to file: {filepath}")

    # Write file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(data)
        return str(filepath.resolve())
    except Exception as e:
        print(f"❌ Error: Failed to write file")
        print(f"   Details: {str(e)}")
        print("   Action: Check disk space and permissions")
        sys.exit(1)


def get_file_stats(filepath):
    """Get file size and event count from JSONL file.

    Args:
        filepath (str): Path to the JSONL file

    Returns:
        tuple: (file_size_str, event_count)
    """
    # Get file size
    size_bytes = os.path.getsize(filepath)
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    # Count events (lines in file)
    with open(filepath, 'r', encoding='utf-8') as f:
        event_count = sum(1 for line in f if line.strip())

    return size_str, event_count


# ============================================================================
# User Interface
# ============================================================================

def display_welcome(config):
    """Display welcome message with loaded configuration."""
    print("╔════════════════════════════════════════════════╗")
    print("║   Mixpanel to PostHog Export Tool             ║")
    print("║   Export raw event data for S3 import         ║")
    print("╚════════════════════════════════════════════════╝")
    print()
    print("Loaded configuration:")
    print(f"  Project ID: {config['project_id']}")
    # Display abbreviated username (first 20 chars)
    username_display = config['username'][:20] + "..." if len(config['username']) > 20 else config['username']
    print(f"  Service Account: {username_display}")
    print(f"  Output Directory: {config['output_dir']}")


def confirm_export(from_date, to_date, config):
    """Display export summary and get user confirmation.

    Args:
        from_date (str): Start date
        to_date (str): End date
        config (dict): Configuration dictionary

    Returns:
        bool: True if user confirms, False otherwise
    """
    from_dt = datetime.strptime(from_date, '%Y-%m-%d')
    to_dt = datetime.strptime(to_date, '%Y-%m-%d')
    days = (to_dt - from_dt).days + 1

    filename = f"mixpanel_export_{from_date}_to_{to_date}.jsonl"

    print("\nExport Summary:")
    print(f"  Date Range: {from_date} to {to_date} ({days} days)")
    print(f"  Project ID: {config['project_id']}")
    print(f"  Output File: {filename}")
    print()

    response = input("Proceed with export? (y/n): ").strip().lower()
    return response == 'y'


def display_success(filepath, from_date, to_date):
    """Display success message with file details and next steps.

    Args:
        filepath (str): Path to the exported file
        from_date (str): Start date
        to_date (str): End date
    """
    size_str, event_count = get_file_stats(filepath)
    filename = os.path.basename(filepath)

    print("\n✅ Export completed successfully!")
    print()
    print("File Details:")
    print(f"  Path: {filepath}")
    print(f"  Size: {size_str}")
    print(f"  Events: {event_count:,} events")
    print()
    print("Next Steps:")
    print("  1. Verify the export file (check first/last lines)")
    print("  2. Upload to S3 bucket for PostHog import")
    print('  3. In PostHog import settings, set content type to "mixpanel"')
    print()
    print("Upload command (example):")
    print(f"  aws s3 cp {filename} \\")
    print("    s3://your-bucket-name/ \\")
    print("    --metadata content-type=mixpanel")
    print()


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main entry point for the export script."""
    try:
        # 1. Load and validate configuration
        config = load_config()

        # 2. Display welcome screen
        display_welcome(config)

        # 3. Get date range from user
        from_date, to_date = get_date_range_from_user()

        # 4. Confirm export
        if not confirm_export(from_date, to_date, config):
            print("\nExport cancelled by user.")
            sys.exit(0)

        # 5. Export data from Mixpanel
        data = export_from_mixpanel(config, from_date, to_date)

        # 6. Save to file
        filepath = save_to_file(data, from_date, to_date, config['output_dir'])

        # 7. Display success message
        display_success(filepath, from_date, to_date)

    except KeyboardInterrupt:
        print("\n\nExport cancelled by user (Ctrl+C).")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {str(e)}")
        print("   Action: Please report this issue if it persists")
        sys.exit(1)


if __name__ == "__main__":
    main()
