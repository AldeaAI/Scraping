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

        script_tags = soup.find_all("script", type="application/json")
        if script_tags:
            for script_tag in script_tags:
                try:
                    json_data = json.loads(script_tag.string)
                    return json_data
                except json.JSONDecodeError as e:
                    logging.error(f"JSON Decode Error on {url}: {e}")
                    return None
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
    if json_data and 'props' in json_data and 'initialProps' in json_data['props']:
        initial_props = json_data['props']['initialProps']
        if 'pageProps' in initial_props and 'realEstate' in initial_props['pageProps']:
            real_estate = initial_props['pageProps']['realEstate']
            try:
                details = {
                     'propertyId'   : real_estate.get('propertyId'),
                     'propertyType' : real_estate.get('propertyType'),
                     # 'businessType' : real_estate.get('businessType'),
                     'salePrice'     : real_estate.get('salePrice'),
                     'area':real_estate.get('area'),
                     'areac':real_estate.get('areac'),
                     'rooms':real_estate.get('rooms'),
                     'bathrooms':real_estate.get('bathrooms'),
                     'garages':real_estate.get('garages'),
                     'city': real_estate.get('city'),
                     'zone': real_estate.get('zone'),
                     # 'sector': real_estate.get('sector'),
                     'neighborhood':real_estate.get('neighborhood'),
                     'commonNeighborhood':real_estate.get('commonNeighborhood'),
                     'adminPrice': real_estate['detail'].get('adminPrice'),
                     'companyName':real_estate.get('companyName'),
                     'propertyState': real_estate.get('propertyState'),
                     'coordinates': real_estate.get('coordinates'),
                     'link':real_estate.get('link'),
                     'builtTime':real_estate.get('builtTime'),
                     'stratum':real_estate.get('stratum'),
                     'Extraction Date':datetime.now().strftime("%Y-%m-%d"),
                }
                return details
            except (KeyError, TypeError) as e:
                logging.error(f"Error extracting specific data from {url}: {e}")
                return None
        else:
            logging.warning(f"'realEstate' key not found in JSON on {url}")
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
        driver = webdriver.Chrome(options=options)
        driver.get(url_main)

        wait = WebDriverWait(driver, timeout)
        # Find all card headers that contain the property links
        card_headers = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "card-header")))

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
    main_url = f"https://www.metrocuadrado.com/apartaestudio-apartamento/venta/{city}/"
    df = get_property_links_selenium(main_url, limit=None)  # Limit for testing

    if df is not None:
        # Create filename with date
        extraction_date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"data/Apartments/listings_data_m2_{city}_{extraction_date_str}.csv"  # Filename with date
        df.to_csv(filename, index=False, encoding="utf-8")  # Saves the dataframe to a csv file
        print(f"Data saved to {filename}") #Prints the filename
        logging.info("Property data saved to property_data.csv")
    else:
        logging.info("Could not retrieve property links or create DataFrame.")

