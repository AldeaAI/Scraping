#!/usr/bin/env python

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re
import pandas as pd
from datetime import datetime

def get_total_pages(url):
    """
    Fetches the given URL and extracts the total number of pages from the pagination.

    Args:
        url (str): The URL of the website to scrape.

    Returns:
        int: The total number of pages if found, None otherwise.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.content, 'html.parser')

        last_page_link = soup.select_one(".pagination li:last-child a") #Selects the last page link

        if last_page_link:
            try:
                last_page_text = last_page_link.text.strip()
                if last_page_text == "»": #Handles the case where the last page is represented by »
                    last_page_link = soup.select(".pagination li:nth-last-child(2) a") #Selects the second to last element
                    if last_page_link:
                        last_page_text = last_page_link[0].text.strip()
                return int(last_page_text)
            except ValueError:
                return None  # Return None if the last page text is not a valid integer
        else:
            return None  # Return None if no pagination is found

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def get_all_page_links(base_url, total_pages):
    """
    Creates a list of URLs for all pages based on the base URL and total number of pages.

    Args:
        base_url (str): The base URL of the website.
        total_pages (int): The total number of pages.

    Returns:
        list: A list of URLs for all pages.
    """
    all_links = [base_url]  # Start with the base URL
    for page_num in range(2, total_pages + 1):
        page_url = f"{base_url}/pagina/{page_num}"
        all_links.append(page_url)
    return all_links

def get_listing_links(page_url, base_url):
    """
    Extracts listing links and their codes from a given page, excluding those containing "Ambos".

    Args:
        page_url (str): The URL of the page to scrape.
        base_url (str): The base URL of the website.

    Returns:
        list: A list of dictionaries, each containing 'link' and 'code' for a listing.
    """
    try:
        response = requests.get(page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        listing_elements = soup.find_all(id="ruta32") #Find all elements with the id ruta32
        listings = []
        for element in listing_elements:
            relative_link = element.get('href') #Gets the href of the element
            if relative_link:
                full_link = urljoin(base_url, relative_link) #Joins the relative link with the base url
                if "Ambos" not in full_link: #Checks that the link does not contain the word Ambos
                    match = re.search(r"/inmueble/(\d+)/", full_link) #Extracts the code using regex
                    property_code = match.group(1) if match else None #Gets the code from the regex match
                    listings.append({"link": full_link, "code": property_code}) #Appends a dictionary with the link and the code
        return listings

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

def get_listing_data(listing_info):
    """
    Fetches data from a single listing page and adds the extraction date.

    Args:
        listing_info (dict): A dictionary containing the 'link' and 'code' of the listing.

    Returns:
        dict: A dictionary containing the extracted data, or None if an error occurs or data is incomplete.
    """
    try:
        listing_url = listing_info["link"]
        response = requests.get(listing_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        data = listing_info.copy()
        price_element = soup.find(class_="property-price")
        data["Precio"] = price_element.text.strip() if price_element else None

        data["Baños"] = extract_value(soup, "Baños")
        data["Área"] = extract_value(soup, "Área")
        data["Habitaciones"] = extract_value(soup, "Habitaciones")
        data["Garajes"] = extract_value(soup, "Garajes")
        data["Closets"] = extract_value(soup, "Closets")

        # Extract and Split Location
        location_element = soup.find(class_="listing-address")
        location = location_element.text.strip() if location_element else None
        if location:
            parts = location.split(",", 1)  # Split at the first comma only
            data["Municipio"] = parts[0].strip()
            data["Barrio"] = parts[1].strip() if len(parts) > 1 else None #Handles cases where there is no barrio
        else:
            data["Municipio"] = None
            data["Barrio"] = None

        if all(data.values()) and "-" not in data["Precio"]:
            data["Extraction Date"] = datetime.now().strftime("%Y-%m-%d")
            return data
        else:
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching listing URL: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while parsing: {e}")
        return None
        
def extract_value(soup, label):
    """
    Extracts a value based on a label from the page HTML using multiple strategies.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object representing the page HTML.
        label (str): The label to search for.

    Returns:
        str: The extracted value, or None if not found.
    """
    try:
        label_element = soup.find(string=re.compile(rf"\s*{label}\s*", re.IGNORECASE)) #Finds the label using regex ignoring case
        if label_element:
            value_element = label_element.find_next(string=True) #Gets the next string
            if value_element:
                return value_element.strip()

        label_element = soup.find('strong', string=re.compile(rf"\s*{label}\s*", re.IGNORECASE)) #Finds the label inside strong tags using regex ignoring case
        if label_element:
            value_element = label_element.find_next(string=True) #Gets the next string
            if value_element:
                return value_element.strip()

        value_element = soup.find('span', class_=re.compile(rf".*{label}.*", re.IGNORECASE)) #Finds the value in a span tag with a class that contains the label using regex ignoring case
        if value_element:
            return value_element.text.strip()
        
        return None
    except:
        return None

# Main execution block
if __name__ == "__main__":
    base_url = "https://www.lalonjapropiedadraiz.com/inmuebles/Venta/clases_Casa"
    total_pages = get_total_pages(base_url)

    if total_pages:
        all_page_links = get_all_page_links(base_url, total_pages)
        all_listings = []
        for page_link in all_page_links:
            print(f"Scraping listings from: {page_link}")
            listings_from_page = get_listing_links(page_link, base_url)
            all_listings.extend(listings_from_page)
            time.sleep(1)

        all_listings_data = []

        for listing_info in all_listings:
            print(f"Scraping data from: {listing_info['link']}")
            listing_data = get_listing_data(listing_info)
            if listing_data:
                all_listings_data.append(listing_data)
            time.sleep(1)

        if all_listings_data:
            df = pd.DataFrame(all_listings_data) # Creates the pandas dataframe
            # print("\nExtracted data in Pandas DataFrame:")
            # print(df) # Prints the dataframe

            # Create filename with date
            extraction_date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"data/Houses/listings_data_{extraction_date_str}.csv"  # Filename with date
            df.to_csv(filename, index=False, encoding="utf-8")  # Saves the dataframe to a csv file
            print(f"Data saved to {filename}") #Prints the filename
        else:
            print("No listings with all the required data and a valid price were found.")

    elif total_pages == 0:
        print("There are no pages")
    else:
        print("Could not determine the total number of pages.")






