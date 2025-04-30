#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time
import logging
import pandas as pd
import sys
import random
# import pprint

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_json_data(driver, url, timeout=10):
    """Extracts JSON data from a <script type="application/json"> tag.

    Args:
        driver: Selenium WebDriver instance.
        url: URL of the page.
        timeout: Timeout in seconds for waiting for the page to load.

    Returns:
        dict: Parsed JSON data, or None if not found or on error.
    """
    try:
        driver.get(url)
        wait = WebDriverWait(driver, timeout)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        script_tags = soup.find_all("script")
        # print(script_tags)
        if script_tags:
            for script_tag in script_tags:
                # try:
                if script_tag.string and '{\\"data\\"' in script_tag.string:
                    start_index = script_tag.string.find('{\\"data\\"')
                    end_index = script_tag.string.rfind("}}]]}],") + 5
                    json_string = script_tag.string[start_index:end_index]
                    json_string = json_string.replace("\\", "")
                    json_string = json_string[:-3]
                    json_data = json.loads(json_string)
                    return json_data
                # except json.JSONDecodeError as e:
                #     logging.error(f"JSON Decode Error on {url}: {e}")
                #     return None
        return None  # No script tag found

    except TimeoutException:
        logging.error(f"Timeout on {url}")
        return None
    except Exception as e:
        logging.exception(f"Error extracting JSON on {url}: {e}")
        return None

def extract_property_details(driver, url, timeout=10):
    """Extracts specific property details from the JSON data.

    Args:
        driver: Selenium WebDriver instance.
        url: URL of the property page.
        timeout: Timeout in seconds.

    Returns:
        dict: Extracted property details, or None if not found or on error.
    """
    json_data = extract_json_data(driver, url, timeout)
    if json_data:
        json_data = json_data.get('data', None)
        try:
            details = {
                     'propertyId'   :      json_data.get('propertyId', None),
                     'propertyType' :      json_data.get('propertyType', None),
                     # 'businessType' :    real_estate.get('businessType', None),
                     'salePrice'     :     json_data.get('salePrice', None),
                     'area':               json_data.get('area', None),
                     'areac':              json_data.get('areac', None),
                     'rooms':              json_data.get('rooms', None),
                     'bathrooms':          json_data.get('bathrooms', None),
                     'garages':            json_data.get('garages', None),
                     'city':               json_data.get('city', None),
                     'zone':               json_data.get('zone', None),
                     # 'sector': real_estate.get('sector', None),
                     'neighborhood':       json_data.get('neighborhood', None),
                     'commonNeighborhood': json_data.get('commonNeighborhood', None),
                     'adminPrice':         json_data['detail'].get('adminPrice', None),
                     'companyName':        json_data.get('companyName', None),
                     'propertyState':      json_data.get('propertyState', None),
                     'coordinates':        json_data.get('coordinates', None),
                     'link':               json_data.get('link', None),
                     'builtTime':          json_data.get('builtTime', None),
                     'stratum':            json_data.get('stratum', None),
                     'Extraction Date':datetime.now().strftime("%Y-%m-%d"),
                    }
            return details

        except (KeyError, TypeError, AttributeError) as e:
            logging.error(f"Error extracting specific data from {url}: {e}")
            return None

    return None

def get_property_links_selenium(url_main, timeout=10, limit=None):
    """Extracts property links and details, excluding "proyecto" links, and returns a pandas DataFrame.

    Args:
        url_main: Main URL to start scraping.
        timeout: Timeout for Selenium waits.
        limit: Maximum number of links to process.

    Returns:
        pandas.DataFrame: DataFrame containing property details, or None on error.
    """
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')  # Run Chrome in headless mode (no browser window)
        user_agents = [
                            # Chrome/Chromium on Ubuntu
                            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36", # Basic Chrome on Linux
                            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36", # More specific to Ubuntu
                            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chromium/114.0.0.0 Safari/537.36", # Chromium
                            ]
        user_agent = random.choice(user_agents)
        options.add_argument(f"user-agent={user_agent}")
        driver = webdriver.Chrome(options=options)
        driver.get(url_main)

        wait = WebDriverWait(driver, timeout)
        #scroll to the bottom to load objects
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Find all card headers that contain the property links
        card_headers = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "property-card__content")))

        links = []
        for card_header in card_headers:
            a_tags = card_header.find_elements(By.TAG_NAME, "a")
            for a_tag in a_tags:
                href = a_tag.get_attribute("href")
                # Exclude links containing "proyecto" (project/new development properties)
                if href and "proyecto" not in href.lower():
                    links.append(href)

        extracted_data = []
        for i, link in enumerate(links):
            if limit and i >= limit:  # Stop if the limit is reached
                break
            logging.info(f"Extracting data from link {i+1}/{len(links)}: {link}")
            data = extract_property_details(driver, link)
            if data:
                extracted_data.append(data)

        driver.quit()

        if extracted_data:  # Create a pandas DataFrame if data was extracted
            df = pd.DataFrame(extracted_data)
            return df
        else:
            logging.info("No property details extracted.")
            return None

    except TimeoutException:
        logging.error(f"Timed out waiting for elements after {timeout} seconds.")
        return None
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:  # Check if any arguments were provided
        city = sys.argv[1]  # The first argument (after the script name)
    
    # city = 'medellin'
    # city = 'la-estrella'
    # city = 'caldas'
    # city = 'sabaneta'
    # city = 'envigado'
    # city = 'itagui'
    # city = 'bello'
    # city = 'copacabana'
    # city = 'girardota'
    # city = 'barbosa'
    main_url = f"https://www.metrocuadrado.com/oficina/venta/{city}/"
    df = get_property_links_selenium(main_url, limit=None, timeout=120)  # Limit for testing

    if df is not None:
        # Create filename with date
        extraction_date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"data/Offices/listings_data_m2_{city}_{extraction_date_str}.csv"  # Filename with date
        df.to_csv(filename, index=False, encoding="utf-8")  # Saves the dataframe to a csv file
        print(f"Data saved to {filename}") #Prints the filename
        logging.info(f"Property data saved to {filename}")
    else:
        logging.info("Could not retrieve property links or create DataFrame.")
        sys.exit(1)

