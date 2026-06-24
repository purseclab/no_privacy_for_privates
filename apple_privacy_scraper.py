from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import csv
import re

def init_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)

def export_all_privacy_data_to_csv(data_by_app, filename="all_privacy_data_nonMM.csv"):
    with open(filename, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["App Name", "Section", "Purpose", "Category", "Item"])

        for app_name, privacy_data in data_by_app.items():
            for section, purposes in privacy_data.items():
                for purpose, categories in purposes.items():
                    for category in categories:
                        cat_name = category["category"]
                        items = category["items"] or [""]
                        for item in items:
                            writer.writerow([app_name, section, purpose, cat_name, item])


def parse_privacy_data(soup):
    modal = soup.find("div", {"id": "modal-container"})
    if not modal:
        return {}

    sections = {}
    current_section = None
    current_purpose = None
    current_category = None

    for tag in modal.find_all(["h2", "h3", "h4", "ul"]):
        if tag.name == "h2":
            current_section = tag.get_text(strip=True)
            sections[current_section] = {}
        elif tag.name == "h3" and current_section:
            current_purpose = tag.get_text(strip=True)
            sections[current_section][current_purpose] = []
        elif tag.name == "h4" and current_section and current_purpose:
            current_category = {
                "category": tag.get_text(strip=True),
                "items": []
            }
            sections[current_section][current_purpose].append(current_category)
        elif tag.name == "ul" and current_category:
            items = [li.get_text(strip=True) for li in tag.find_all("li")]
            current_category["items"].extend(items)

    return sections


def search_and_get_app_link(app_name):
    search_url = f"https://www.apple.com/us/search/{app_name}?src=serp"
    driver = init_driver()
    driver.get(search_url)

    try:
        # Wait up to 10 seconds for the first result to appear
        wait = WebDriverWait(driver, 10)
        result = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.rf-serp-productname-link")))

        app_link = result.get_attribute("href")
        print(f"[+] Found App URL: {app_link}")
        return app_link
    except Exception as e:
        print("[-] Could not find app link:", e)
        return None
    finally:
        driver.quit()


def scrape_privacy_details_and_return(app_url):
    driver = init_driver()
    driver.get(app_url)
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)

    try:
        wait = WebDriverWait(driver, 10)
        details_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[text()='See Details']")
        ))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", details_button)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", details_button)
        time.sleep(2)
    except Exception as e:
        print("[-] Could not click 'See Details' button:", e)
        driver.quit()
        return None, None

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Extract real app name from page
    try:
        header = soup.select_one("h1.product-header__title")
        if header:
            raw_title = header.get_text(separator=" ", strip=True)
            real_app_name = re.sub(r"\d+\+\s*$", "", raw_title).strip()
        else:
            real_app_name = "Unknown App"
    except:
        real_app_name = "Unknown App"

    privacy_data = parse_privacy_data(soup)
    driver.quit()
    return real_app_name, privacy_data

def main(app_list_file):
    all_privacy_data = {}

    with open(app_list_file, "r", encoding="utf-8") as f:
        app_names = [line.strip() for line in f if line.strip()]

    for app_name in app_names:
        print(f"\n[~] Processing: {app_name}")
        app_url = search_and_get_app_link(app_name)
        if app_url and "apps.apple.com" in app_url:
            real_name, data = scrape_privacy_details_and_return(app_url)
            if data:
                all_privacy_data[real_name] = data
        else:
            print(f"[-] No valid App Store link found for '{app_name}'")

    export_all_privacy_data_to_csv(all_privacy_data)
    print("[+] Combined CSV saved as 'all_privacy_data_2.csv'")

if __name__ == "__main__":
    main("apps2.txt")

    