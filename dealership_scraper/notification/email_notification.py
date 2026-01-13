"""
Email Notification Module
Sends email notifications using Mailgun API
"""
import json
import requests
import logging
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

MAILGUN_API_URL = os.getenv("MAILGUN_API_URL")
FROM_EMAIL_ADDRESS = os.getenv("FROM_EMAIL_ADDRESS")


def send_single_email(to_address: str, subject: str, message: str) -> bool:
    """
    Send a single email using Mailgun API

    Args:
        to_address: Recipient email address
        subject: Email subject
        message: Email body (plain text)

    Returns:
        True if email sent successfully, False otherwise
    """
    if not MAILGUN_API_URL or not FROM_EMAIL_ADDRESS:
        logging.error("Mailgun configuration missing. Set MAILGUN_API_URL and FROM_EMAIL_ADDRESS environment variables.")
        return False

    api_key = os.getenv("MAILGUN_API_KEY")
    if not api_key:
        logging.error("MAILGUN_API_KEY environment variable not set")
        return False

    try:
        response = requests.post(
            MAILGUN_API_URL,
            auth=("api", api_key),
            data={
                "from": FROM_EMAIL_ADDRESS,
                "to": to_address,
                "subject": subject,
                "text": message
            },
            timeout=10
        )

        if response.status_code == 200:
            logging.info(f"Email sent successfully to {to_address}")
            return True
        else:
            logging.error(f"Failed to send email. Status: {response.status_code}, Response: {response.text}")
            return False

    except Exception as e:
        logging.error(f"Error sending email: {str(e)}")
        return False


def send_scraper_completion_email(
    to_address: str,
    domain: str,
    vehicles_count: int,
    tools_detected: int,
    duration_minutes: int
) -> bool:
    """
    Send email notification when scraper completes

    Args:
        to_address: Recipient email
        domain: Domain that was scraped
        vehicles_count: Number of vehicles extracted
        tools_detected: Number of tools detected (out of 8)
        duration_minutes: How long the scrape took

    Returns:
        True if email sent successfully
    """
    subject = f"Scraper Complete: {domain}"

    message = f"""
Dealership Scraper Completed Successfully

Domain: {domain}
Duration: {duration_minutes} minutes

Results:
- Vehicles Extracted: {vehicles_count}
- Tools Detected: {tools_detected}/8

Output files saved to:
- output/inventory.json
- output/tools.json

Thank you for using the Dealership Scraper!
"""

    return send_single_email(to_address, subject, message)


def send_scraper_error_email(
    to_address: str,
    domain: str,
    error_message: str
) -> bool:
    """
    Send email notification when scraper encounters an error

    Args:
        to_address: Recipient email
        domain: Domain being scraped
        error_message: Error description

    Returns:
        True if email sent successfully
    """
    subject = f"Scraper Error: {domain}"

    message = f"""
Dealership Scraper Encountered an Error

Domain: {domain}

Error:
{error_message}

Please check the logs for more details.
"""

    return send_single_email(to_address, subject, message)


if __name__ == "__main__":
    # Test the email functionality
    print("Testing Mailgun email notification...")
    result = send_single_email(
        to_address="talhakhawar9292@gmail.com",
        subject="Test Email from Dealership Scraper",
        message="This is a test email to verify Mailgun integration."
    )

    if result:
        print("✓ Email sent successfully!")
    else:
        print("✗ Failed to send email. Check your configuration.")
