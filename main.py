from tempfile import mkdtemp
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
import json
import requests
import os
import boto3
import hashlib
import uuid
import logging
import time
from urllib.parse import urlparse, urlunparse
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


S3_BUCKET = os.getenv("S3_BUCKET", None)
REGION_NAME = os.getenv("AWS_REGION", "us-east-1")


## This code is from: https://medium.com/@kroeze.wb/running-selenium-in-aws-lambda-806c7e88ec64 / https://github.com/wbytedev/wbyte-selenium-lambda
def initialise_driver():
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-tools")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument(f"--user-data-dir={mkdtemp()}")
    chrome_options.add_argument(f"--data-path={mkdtemp()}")
    chrome_options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    chrome_options.add_argument("--remote-debugging-pipe")
    chrome_options.add_argument("--verbose")
    chrome_options.add_argument("--log-path=/tmp")
    chrome_options.binary_location = "/opt/chrome/chrome-linux64/chrome"

    service = Service(
        executable_path="/opt/chrome-driver/chromedriver-linux64/chromedriver",
        service_log_path="/tmp/chromedriver.log"
    )

    driver = webdriver.Chrome(
        service=service,
        options=chrome_options
    )

    return driver


def lambda_handler(event, context):
    driver = initialise_driver()

    s3_client = boto3.client("s3", region_name=REGION_NAME)

    for message in event.get("Records", []):
        logger.debug(f"Processing Record... {message}")
        record = {}
        try:
            record = json.loads(message.get("body", "{}"))
        except Exception as e:
            logger.warning("Failed to parse message body as json. Continuing with blank record...")
        logger.debug(f"Processing Record {record}")

        site_url = record.get("url", None)
        response = {"body": "", "title": "", "url": site_url}
        if site_url is not None:
            logger.info(f"Fetching URL: {site_url}")
            driver.get(site_url)
            time.sleep(3) # sleep to wait for page to load
            all_text = driver.find_element(By.TAG_NAME, "body").text
            logger.debug(f"Found text {all_text}")
            response["body"] = all_text
            page_title = driver.title
            if page_title is not None:
                response["title"] = page_title
            else:
                title = driver.find_element(By.TAG_NAME, "title").text
                if title is not None:
                    response["title"] = title
                else:
                    response["title"] = site_url
        else:
            logger.warning("Site URL is None...")

        s3_path = urlparse(site_url)
        s3_path = urlunparse(s3_path._replace(query=""))
        logger.debug(f"Attempting to upload file to {S3_BUCKET}/{s3_path}")
        try:
            s3_client.put_object(Body=json.dumps(response), ContentType="application/json", Bucket=S3_BUCKET, Key=s3_path, Metadata={"url": site_url})
        except Exception as e:
            logger.error(f"Caught Exception while trying to upload file to S3 Bucket {e}")
        logger.info(f"Successfully Uploaded file to bucket...")
    driver.quit()
