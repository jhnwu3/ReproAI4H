import os
import PyPDF2
import json
import re
import spacy
import csv
from collections import defaultdict, Counter

# Load the more accurate transformer-based model
nlp = spacy.load("en_core_web_trf")

def extract_pdf_content(filename):
    try:
        with open(filename, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                text += page_text
                
                if re.search(r'\n(References|Bibliography|Works Cited|Literature Cited)', page_text, re.IGNORECASE):
                    split_text = re.split(r'\n(References|Bibliography|Works Cited|Literature Cited)', text, maxsplit=1, flags=re.IGNORECASE)
                    text = split_text[0]
                    break
                
        return text
    except Exception as e:
        print(f"Error extracting content from {filename}: {str(e)}")
        return None

def is_likely_name(text):
    doc = nlp(text)
    return any(ent.label_ == "PERSON" for ent in doc.ents)


def clean_title(title):
    # Remove all spaces
    title = re.sub(r'\s', '', title)
    
    # Remove proceedings information
    title = re.sub(r'Proceedingsof.*?20\d{2}', '', title, flags=re.IGNORECASE)
    
    # Remove conference names and years
    conferences = ['MachineLearningforHealthcare', 'MachineLearningforHealth', 'ML4H', 'ClinicalAbstract,Software,andDemoTrack',
                   'ConferenceonHealth,Inference,andLearning', 'CHIL', 'MLHC', 'NeurIPS',
                   'MachineLearningforHealthcare', 'ProceedingsofMachineLearningResearch', '1–26,2 0 1 8 M a c h i n eL e r gf o rH l t', 'M a c h i n eL e r gf o rH l t ']
    for conf in conferences:
        title = re.sub(rf'{conf}.*?20\d{{2}}', '', title, flags=re.IGNORECASE)
        title = re.sub(rf'{conf}', '', title, flags=re.IGNORECASE)
    
    # Remove workshop information
    title = re.sub(r'Workshop', '', title, flags=re.IGNORECASE)
    
    # Remove years (2000-2099)
    title = re.sub(r'20\d{2}', '', title)
    
    # Remove page numbers and other common artifacts
    title = re.sub(r'\d+[-–]\d+,?20\d{2}', '', title)
    
    # Remove any remaining numbers and punctuation at the start or end
    title = re.sub(r'^[\d\W]+|[\d\W]+$', '', title)
    
    # Reinsert spaces before capital letters (except at the start of the title)
    title = re.sub(r'(?<!^)(?=[A-Z])', ' ', title)
    
    # Remove duplicate words (case-insensitive)
    words = title.split()
    title = ' '.join(word for i, word in enumerate(words) if word.lower() not in [w.lower() for w in words[:i]])
    
    return title.strip()

def extract_title(lines):
    title_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if is_likely_name(line):
            break
        title_lines.append(line)

    title = ' '.join(title_lines)
    # Clean up title
    title = re.sub(r'\s+', ' ', title).strip()
    title = re.sub(r'^[^a-zA-Z]+', '', title)  # Remove leading non-alphabetic characters
    
    # Apply additional cleaning
    title = clean_title(title)
    return title

def extract_authors(lines):
    authors = []
    author_section_started = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if 'ABSTRACT' in line.upper():
            break
        if is_likely_name(line) or '@' in line:
            author_section_started = True
            authors.append(line)
        elif author_section_started:
            # Include affiliations or other information right after author names
            authors.append(line)
        if len(authors) > 15:  # Limit to avoid processing the entire document
            break
    return authors

def extract_abstract(text):
    # Find the start of the abstract
    abstract_start = re.search(r'\bABSTRACT\b', text, re.IGNORECASE)
    if not abstract_start:
        return ""
    
    # Find the start of the introduction
    intro_start = re.search(r'\b(1\s*\.?\s*)?INTRODUCTION\b', text[abstract_start.end():], re.IGNORECASE)
    
    if intro_start:
        # Extract text from end of "ABSTRACT" to start of "INTRODUCTION"
        abstract = text[abstract_start.end():abstract_start.end() + intro_start.start()]
    else:
        # If no introduction found, extract a reasonable amount of text
        abstract = text[abstract_start.end():abstract_start.end() + 2000]  # Limit to 2000 characters
    
    # Clean up the abstract
    abstract = re.sub(r'\s+', ' ', abstract).strip()
    
    return abstract


def count_mentions(text, terms):
    if text is None:
        return 0
    text = text.lower()
    return sum(1 for term in terms if term.lower() in text)

def create_dataset_mapping(dataset_terms):
    mapping = {}
    for term_group in dataset_terms:
        key = term_group[0].lower().replace(' ', '_')
        mapping[key] = [term.lower() for term in term_group]
    return mapping



def process_pdf(content, dataset_mapping):
    lines = content.split('\n')
    title = extract_title(lines)
    authors = extract_authors(lines)
    abstract = extract_abstract(content)
    
    result = {
        'title': title,
        'authors': authors,
        'abstract': abstract,
        'code_count': count_mentions(content, ['github', "gitlab", "zenodo", "colab"]),
        'gitlab_count': count_mentions(content, ['gitlab']),
        'zenodo_count': count_mentions(content, ['Zenodo']),
    }
    
    # Add individual counts for each dataset term
    for key, terms in dataset_mapping.items():
        result[f"{key}_count"] = count_mentions(content, terms)
    
    # Calculate total dataset count
    result['dataset_count'] = sum(result[f"{key}_count"] for key in dataset_mapping)
    
    return result

def process_pdf_directory(directory, year, dataset_mapping):
    results = []
    for filename in os.listdir(directory):
        if filename.endswith('.pdf'):
            filepath = os.path.join(directory, filename)
            content = extract_pdf_content(filepath)
            
            if content:
                result = process_pdf(content, dataset_mapping)
                result['year'] = year
                result['filename'] = filename
                results.append(result)
                print(f"Processed {filename}")
    
    return results

def process_conference_directories(conference_dirs, conference_name, dataset_mapping):
    all_results = []
    for directory in conference_dirs:
        year = directory.split('/')[-1][:4]  # Extract year from directory name
        print(f"\nProcessing {directory}...")
        results = process_pdf_directory(directory, year, dataset_mapping)
        all_results.extend(results)
    
    return all_results

def write_to_csv(all_results, dataset_mapping, filename='extracted_data.csv'):
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['year', 'title', 'authors', 'abstract', 'code_count', 'gitlab_count', 'zenodo_count', 'dataset_count']
        fieldnames.extend([f"{key}_count" for key in dataset_mapping])
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL, escapechar='\\')
        writer.writeheader()
        
        for result in all_results:
            try:
                row = {
                    'year': result['year'],
                    'title': result['title'],
                    'authors': ', '.join(result['authors']),
                    'abstract': result['abstract'],
                    'code_count': result['code_count'],
                    'gitlab_count': result['gitlab_count'],
                    'zenodo_count': result['zenodo_count'],
                    'dataset_count': result['dataset_count']
                }
                for key in dataset_mapping:
                    row[f"{key}_count"] = result[f"{key}_count"]
                
                # Replace any newline characters in string fields
                for key, value in row.items():
                    if isinstance(value, str):
                        row[key] = value.replace('\n', ' ').replace('\r', '')
                
                writer.writerow(row)
            except Exception as e:
                print(f"Error writing row: {e}")
                print(f"Problematic row: {result}")
                continue

def main():
    dataset_terms = [
        ["MIMIC", "Medical Information Mart for Intensive Care"],
        ["eICU", "eICU Collaborative Research Database"],
        ["UK Biobank"],
        ["Chest X-Ray14", "NIH Chest X-ray"],
        ["ADNI", "Alzheimer's Disease Neuroimaging Initiative"],
        ["PhysioNet"],
        ["OASIS", "Open Access Series of Imaging Studies"],
        ["TCGA", "The Cancer Genome Atlas Program"],
        ["GDC", "Genomic Data Commons"],
        ["SEER", "Surveilance Epidemiology and End Results"],
        ["TUH EEG Corpus", "TUEG"],
        ["TUH Abnormal EEG Corpus", "TUAB"],
        ["TUH EEG Artifact Corpus", "TUAR"],
        ["TUH EEG Epilepsy Corpus", "TUEP"],
        ["TUH EEG Events Corpus", "TUEV"],
        ["TUH EEG Seizure Corpus", "TUSV"],
        ["TUH EEG Slowing Corpus", "TUSL"]
    ]

    dataset_mapping = create_dataset_mapping(dataset_terms)

    conferences = {
        "CHIL": ["chil/2020pdf", "chil/2021pdf", "chil/2022pdf", "chil/2023pdf", "chil/2024pdf"],
        "ML4H": ["ml4h/2019pdf", "ml4h/2020pdf", "ml4h/2021pdf", "ml4h/2022pdf", "ml4h/2023pdf"],
        "MLHC": ["mlhc/2017pdf", "mlhc/2018pdf", "mlhc/2019pdf", "mlhc/2020pdf", "mlhc/2021pdf", "mlhc/2022pdf", "mlhc/2023pdf"]
    }

    for conference_name, dirs in conferences.items():
        all_results = process_conference_directories(dirs, conference_name, dataset_mapping)
        output_filename = f"processed_data/{conference_name.lower()}_extracted_info.csv"
        write_to_csv(all_results, dataset_mapping, filename=output_filename)
        print(f"\nExtracted data for {conference_name} has been written to {output_filename}")

if __name__ == "__main__":
    main()