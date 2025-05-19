# chatbot/tasks.py
from celery import shared_task
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_scheduled_tasks():
    """Task to trigger the scheduled_tasks endpoint for tips, nudges, and meal plans"""
    try:
        url = f"{settings.SITE_URL}/scheduled_tasks/"
        logger.info(f"Sending request to scheduled_tasks endpoint: {url}")
        response = requests.post(url, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Scheduled tasks executed successfully: {response.json()}")
            return response.json()
        else:
            logger.error(f"Failed to execute scheduled tasks: {response.status_code} - {response.text}")
            raise Exception(f"HTTP {response.status_code}: {response.text}")
            
    except requests.RequestException as e:
        logger.error(f"Error calling scheduled_tasks endpoint: {str(e)}")
        raise Exception(f"Request error: {str(e)}")