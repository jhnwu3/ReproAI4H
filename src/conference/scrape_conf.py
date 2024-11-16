import requests
from bs4 import BeautifulSoup
import PyPDF2
import io
from urllib.parse import urljoin, urlparse
import time
import random
import os
import shutil

def create_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
    return session

def scrape_webpage(url, session):
    response = session.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        pdf_links = []
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and href.lower().endswith('.pdf'):
                full_url = urljoin(url, href)
                pdf_links.append((full_url, link.text))
        return pdf_links
    else:
        print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
        return []

def download_pdf(pdf_url, session, year_folder, all_folder):
    max_retries = 3
    retry_delay = 5

    # Create the folders if they don't exist
    for folder in [year_folder, all_folder]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    # Generate a filename from the URL
    filename = os.path.basename(urlparse(pdf_url).path)
    year_filename = os.path.join(year_folder, filename)
    all_filename = os.path.join(all_folder, filename)

    for attempt in range(max_retries):
        response = session.get(pdf_url)
        if response.status_code == 200:
            # Save in year-specific folder
            with open(year_filename, 'wb') as f:
                f.write(response.content)
            # Save in 'all' folder
            with open(all_filename, 'wb') as f:
                f.write(response.content)
            print(f"Successfully downloaded: {filename}")
            return year_filename
        elif response.status_code == 429:
            print(f"Rate limited. Waiting {retry_delay} seconds before retrying...")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
        else:
            print(f"Failed to download the PDF. Status code: {response.status_code}")
            return None

    print(f"Max retries reached for {pdf_url}")
    return None

def extract_pdf_content(filename):
    try:
        with open(filename, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        print(f"Error extracting content from {filename}: {str(e)}")
        return None

# Configuration
conferences = {
    'amia': {
'base_urls': []
    },
    'chil': {
        'base_urls': [
            "https://proceedings.mlr.press/v174/",
            "https://proceedings.mlr.press/v209/",
            "https://proceedings.mlr.press/v248/"
        ],
        'years': [2022, 2023, 2024],
        'folder_prefix': 'chil'
    },
    'mlhc': {
        'base_urls': [
            "https://www.mlforhc.org/2018",
            "https://www.mlforhc.org/2019-conference"
        ],
        'years': [2018, 2019],
        'folder_prefix': 'mlhc'
    },
    'ml4h': {
        'base_urls': [
            "https://proceedings.mlr.press/v116/",
            "https://proceedings.mlr.press/v136/",
            "https://proceedings.mlr.press/v158/",
            "https://proceedings.mlr.press/v193/",
            "https://proceedings.mlr.press/v225/"
        ],
        'years': [2019, 2020, 2021, 2022, 2023],
        'folder_prefix': 'ml4h'
    }
}

# Main execution
session = create_session()

for conference, config in conferences.items():
    print(f"Processing {conference.upper()} conference papers...")
    for idx, base_url in enumerate(config['base_urls']):
        year = config['years'][idx]
        year_folder = f"{config['folder_prefix']}/{year}pdf"
        all_folder = f"{config['folder_prefix']}/pdf"

        pdf_links = scrape_webpage(base_url, session)

        for pdf_url, pdf_title in pdf_links:
            print(f"Downloading: {pdf_title}")
            time.sleep(random.uniform(1, 3))  # Random delay between requests
            filename = download_pdf(pdf_url, session, year_folder, all_folder)
            if filename:
                print(f"Extracting content from: {filename}")
                pdf_content = extract_pdf_content(filename)
                if pdf_content:
                    print(f"Content of {pdf_url}:")
                    print(pdf_content[:500])  # Print first 500 characters
                else:
                    print(f"Failed to extract content from {filename}")
            else:
                print(f"Failed to download {pdf_url}")
            print("---")

    print(f"Finished processing {conference.upper()} conference papers.")
    print("==="*20)