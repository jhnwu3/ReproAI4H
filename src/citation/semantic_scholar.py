import os
import requests
import time
import pandas as pd

S2_API_KEY = "6LNk9us0q082en0aRoUmc9eURiWmtqwW5pFQtQ5H"
RESULT_LIMIT = 10
BASE_URL = 'https://api.semanticscholar.org/graph/v1/paper/search'
DELAY = 2.2

def search_papers(query):
    params = {
        'query': query,
        'limit': RESULT_LIMIT,
        'fields': 'title,url,abstract,authors,year,citationCount'
    }
    headers = {'X-API-KEY': S2_API_KEY}
    
    max_retries = 3
    retry_delay = DELAY

    for attempt in range(max_retries):
        try:
            response = requests.get(BASE_URL, params=params, headers=headers)
            response.raise_for_status()
            results = response.json()
            time.sleep(DELAY)
            
            # Check if 'data' key exists in the results
            if 'data' in results:
                print("Found results for query:", query)
                return results['data']
            else:
                print(f"Warning: 'data' key not found in API response for query: {query}")
                return []
        except requests.RequestException as e:
            if response.status_code == 429:
                print(f"Rate limit exceeded. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"An error occurred: {e}")
                return []
    
    print(f"Max retries reached. Unable to fetch results for query: {query}")
    return []


def get_citation_count(title, n_words=3):
    papers = search_papers(title)
    
    if not papers:
        print(f"No papers found for title: {title}")
        return None

    # Check for title overlap
    title_words = title.lower().split()
    for paper in papers:
        paper_title_words = paper['title'].lower().split()
        
        # Check if any n consecutive words from the original title appear in the paper title
        for i in range(len(title_words) - n_words + 1):
            if ' '.join(title_words[i:i+n_words]) in ' '.join(paper_title_words):
                return paper['citationCount']
    
    print(f"No matching paper found for title: {title}")
    return None

def process_dataframe(df, title_column='cleaned_title', output_file='chil_semantic_scholar_citations.csv'):
    df['citation_count'] = df[title_column].apply(get_citation_count)
    
    # Save the updated DataFrame
    df.to_csv(output_file, index=False)
    print(f"Updated DataFrame saved to {output_file}")
    
    return df


def get_citation_count(title, n_words=3):
    papers = search_papers(title)
    
    if not papers:
        print(f"No papers found for title: {title}")
        return None

    # Check for title overlap
    title_words = title.lower().split()
    for paper in papers:
        paper_title_words = paper['title'].lower().split()
        
        # Check if any n consecutive words from the original title appear in the paper title
        for i in range(len(title_words) - n_words + 1):
            if ' '.join(title_words[i:i+n_words]) in ' '.join(paper_title_words):
                return paper['citationCount']
    
    print(f"No matching paper found for title: {title}")
    return None

def process_dataframe(df, title_column='cleaned_title', output_file='chil_semantic_scholar_citations.csv'):
    df['citation_count'] = df[title_column].apply(get_citation_count)
    
    # Save the updated DataFrame
    df.to_csv(output_file, index=False)
    print(f"Updated DataFrame saved to {output_file}")
    
    return df


def process_conference_dataframes(dataframes_dict, output_dir="processed_data/"):
    """
    Process multiple dataframes for different conferences and save results.
    
    :param dataframes_dict: A dictionary where keys are conference names and values are dataframes
    :param output_dir: Directory to save the processed files
    :return: A dictionary of processed dataframes
    """
    processed_dataframes = {}
    
    for conference_name, df in dataframes_dict.items():
        print(f"Processing {conference_name} data...")
        
        # Add citation counts
        df['citation_count'] = df['cleaned_title'].apply(get_citation_count)
        
        # Save the updated DataFrame
        output_file = os.path.join(output_dir, f"{conference_name}_semantic_scholar_citations.csv")
        df.to_csv(output_file, index=False)
        print(f"Updated {conference_name} DataFrame saved to {output_file}")
        
        processed_dataframes[conference_name] = df
        
        # Add a delay to respect rate limits
        time.sleep(1)
    
    return processed_dataframes


all_chil_data = pd.read_csv("processed_data/cleaned_chil_extracted_info.csv")
all_ml4h_data = pd.read_csv("processed_data/cleaned_ml4h_extracted_info.csv")
all_mlhc_data = pd.read_csv("processed_data/cleaned_mlhc_extracted_info.csv")

conference_data = {
    "chil": all_chil_data,
    "ml4h": all_ml4h_data,
    "mlhc": all_mlhc_data
}
processed_dataframes = process_conference_dataframes(conference_data)

for conference, df in processed_dataframes.items():
    print(f"\n{conference.upper()} Citation Summary:")
    print(df['citation_count'].describe())
    print(f"Number of papers without citations: {df['citation_count'].isna().sum()}")

# Usage
# chil_data = pd.read_csv('processed_data/cleaned_chil_extracted_info.csv')
# updated_df = process_dataframe(chil_data)
# print(updated_df[['cleaned_title', 'citation_count']])