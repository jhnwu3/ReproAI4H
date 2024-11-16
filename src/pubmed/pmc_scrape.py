import pandas as pd 
import pickle 
import csv
import json
import pmidcite
from pmidcite.icite.downloader import get_downloader
import requests
import time
import metapub as mp
from src.pubmed.pmc_scrape_func import parse_bioc_xml, parse_bioc_xml_year, parse_bioc_xml_abstract, parse_bioc_xml_authors, parse_bioc_xml_title

print(f"pmidcite version: {pmidcite.__version__}")
dnldr = get_downloader()

def get_citation_count(pmid):
    nih_entry = dnldr.get_icite(pmid)
    nih_dict = nih_entry.get_dict()
    return nih_dict["citation_count"]

def get_papers_year(dictionary, year):
    papers = {}
    for pmid, record in dictionary.items():
        # print(type(year))
        # print(type(record["year"]))
        if record["year"] == year:
            papers[pmid] = record 
    return papers 

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

def count_mentions_grouped(text, dataset_mapping):
    if text is None:
        return {}
    text = text.lower()
    counts = {key: 0 for key in dataset_mapping}
    for key, terms in dataset_mapping.items():
        counts[key] = sum(1 for term in terms if term in text)
    return counts

def get_counts_per_paper(year_papers, dataset_mapping):
    counts = {}
    for pmid, record in year_papers.items():
        text = record["content"]
        counts[pmid] = {}
        code_terms = ["github", "gitlab", "zenodo", "colab", "bitbucket", "docker", "jupyter", "kaggle"]
        dataset_counts = count_mentions_grouped(text, dataset_mapping)
        counts[pmid].update(dataset_counts)
        counts[pmid]["big_datasets"] = sum(dataset_counts.values())
        counts[pmid]["code"] = count_mentions(text, code_terms)
        counts[pmid]["ai"] = count_mentions(text, ["AI", "Artificial Intelligence", "Machine Learning", "Deep Learning", "Neural Network"])
        counts[pmid]["citation_count"] = get_citation_count(pmid)
        print(counts[pmid])
    return counts

def get_analysis(counts, dataset_mapping):
    stats = {
        'total_files': len(counts),
        'files_with_github': sum(1 for r in counts.values() if r['code'] > 0),
        'files_without_github': sum(1 for r in counts.values() if r['code'] == 0),
        'total_github_mentions': sum(r['code'] for r in counts.values()),
        'files_with_public_dataset': sum(1 for r in counts.values() if r['big_datasets'] > 0),
        'total_dataset_mentions': sum(r['big_datasets'] for r in counts.values()),
        'files_with_github_and_dataset': sum(1 for r in counts.values() if r['code'] > 0 and r['big_datasets'] > 0),
        'files_with_github_and_without_dataset': sum(1 for r in counts.values() if r['code'] > 0 and r['big_datasets'] == 0),
        'files_with_AI': sum(1 for r in counts.values() if r['ai'] > 0),
        'total_citations': sum(r['citation_count'] for r in counts.values() if r['citation_count'] is not None),
    }
    
    for key in dataset_mapping.keys():
        stats[f'files_with_{key}'] = sum(1 for r in counts.values() if r[key] > 0)
        stats[f'total_{key}_mentions'] = sum(r[key] for r in counts.values())
    
    return stats

def get_papers_across_years(dictionary, years, dataset_mapping):
    all_stats = {}
    all_paper_data = {}
    for year in years:
        
        papers = get_papers_year(dictionary, year)
        # print(papers.values())
        counts_each_paper = get_counts_per_paper(papers, dataset_mapping)
        # print(counts_each_paper.values())
        analysis = get_analysis(counts_each_paper, dataset_mapping)
        all_stats[year] = analysis 
        all_paper_data[year] = counts_each_paper

        print(f"Year: {year}, Papers: {len(papers)}")
        print(analysis)
    return all_stats, all_paper_data

def write_stats_to_csv(all_stats, dataset_mapping, filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        header = ['Statistic'] + list(all_stats.keys())
        writer.writerow(header)
        
        stats_keys = [
            'total_files', 
            'files_with_github', 'files_without_github', 'total_github_mentions',
            'files_with_public_dataset', 'total_dataset_mentions',
            'files_with_github_and_dataset',
            'files_with_github_and_without_dataset',
            'files_with_AI',
            'total_citations'
        ]
        
        for key in dataset_mapping.keys():
            stats_keys.extend([f'files_with_{key}', f'total_{key}_mentions'])
        
        for key in stats_keys:
            row = [key.replace('_', ' ').title()]
            for year in all_stats.keys():
                row.append(all_stats[year].get(key, ''))
            writer.writerow(row)

 # Update the save_paper_data function to include title, authors, and abstract
def save_paper_data(all_paper_data, json_filename, pkl_filename, bioc_dicts):
    # Create a new dictionary with all the data
    full_paper_data = {}
    for year, papers in all_paper_data.items():
        full_paper_data[year] = {}
        for pmid, data in papers.items():
            full_paper_data[year][pmid] = {
                **data,
                "title": bioc_dicts[pmid]["title"],
                "authors": bioc_dicts[pmid]["authors"],
                "abstract": bioc_dicts[pmid]["abstract"]
            }
    
    with open(json_filename, 'w') as f:
        json.dump(full_paper_data, f, indent=4)
    
    with open(pkl_filename, 'wb') as f:
        pickle.dump(full_paper_data, f)

def pmid2biocxml(pmid):
    start_time = time.time()
    # note to self their old API is the one we shoudl use.
    # base_url = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pubmed.cgi/BioC_xml/{pmid}/unicode"
    # base_url = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pubmed.cgi/BioC_json/{pmid}/unicode"
    base_url = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/{pmid}/unicode"
    if not isinstance(pmid, list):
        pmid = [pmid]
    res = []
    api_status = "up"
    for pmid_ in pmid:
        request_url = base_url.format(pmid=pmid_)
        try:
            response = requests.get(request_url, timeout=10)
            response.raise_for_status()
            res.append(response.text)
            print(f"PMID {pmid_}: Response length = {len(response.text)} characters")
            # print(response.text)
        except requests.exceptions.RequestException as e:
            print(f"Error accessing the API for PMID {pmid_}: {str(e)}")
            api_status = "down"
            break
    end_time = time.time()
    print(f"pmid2biocxml execution time: {end_time - start_time:.2f} seconds")
    print(f"API Status: {'Up' if api_status == 'up' else 'Down'}")
    return res

# def pmid2biocxml(pmid):
#     base_url = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/{pmid}/unicode"
#     if not isinstance(pmid, list): pmid = [pmid]
#     res = []
#     for pmid_ in pmid:
#         request_url = base_url.format(pmid=pmid_)
#         response = requests.get(request_url)
#         res.append(response.text)
#     return res


def read_pmids_from_csv(filename):
    start_time = time.time()
    pmids = []
    with open(filename, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip the header row
        for row in reader:
            pmids.append(row[0])
    end_time = time.time()
    print(f"read_pmids_from_csv execution time: {end_time - start_time:.2f} seconds")
    return pmids

def save_to_pickle(data, filename):
    with open(filename, 'wb') as f:
        pickle.dump(data, f)

def load_from_pickle(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)

def flatten_passages(bioc_dict):
    flattened_str = ""
    for section in bioc_dict["passage"]:
        flattened_str += " " + section["content"]
    return flattened_str

import time
import os

def main(venue="pubmed", n=10000):
    start_time = time.time()
    print("Starting BioC scraping for venue:", venue.upper())
    # Create directories if they don't exist
    os.makedirs(f"{venue}_content", exist_ok=True)
    os.makedirs("processed_data", exist_ok=True)

    # Step 1: Read PMIDs and fetch BioC XML
    filename = f"{venue}_ai_ml_pmids.csv"
    read_pmids = read_pmids_from_csv(filename)
    bioc_xmls = pmid2biocxml(read_pmids[:n])
    print("Read PMIDs:", len(read_pmids))
    save_to_pickle(bioc_xmls, f"{venue}_content/bioc_xmls.pkl")

    # Step 2: Process BioC XML
    bioc_xmls = load_from_pickle(f"{venue}_content/bioc_xmls.pkl")
    pubmed_dates = []
    for bioc_xml in bioc_xmls:
        article_year = parse_bioc_xml_year(bioc_xml)
        pubmed_dates.append(article_year)

    my_processed_dict = {}
    parse_start_time = time.time()
    for idx, bioc_xml in enumerate(bioc_xmls):
        pmid = read_pmids[idx]
        year = pubmed_dates[idx]
        print(f"Processing {venue.upper()} ID:", pmid)
        
        # Add check to ensure bioc_xml is a non-empty string
        if isinstance(bioc_xml, str) and len(bioc_xml) > 0 and "xml" in bioc_xml:
            dictionary = parse_bioc_xml(bioc_xml)
            flattened = flatten_passages(dictionary)
            title = parse_bioc_xml_title(bioc_xml)
            authors = parse_bioc_xml_authors(bioc_xml)
            abstract = parse_bioc_xml_abstract(bioc_xml)
            my_processed_dict[pmid] = {
                "content": flattened,
                "year": year,
                "title": title,
                "authors": authors,
                "abstract": abstract
            }
        else:
            print(f"Warning: Empty or invalid BioC XML for {venue.upper()} ID {pmid}")

    save_to_pickle(my_processed_dict, f"{venue}_content/paper_content_flattened.pkl")
    parse_end_time = time.time()
    print(f"parse_bioc_xml execution time: {parse_end_time - parse_start_time:.2f} seconds")

    # Step 3: Analyze processed data
    bioc_dicts = load_from_pickle(f"{venue}_content/paper_content_flattened.pkl")
    print(len(bioc_dicts))
    print(bioc_dicts.keys())
    print(list(bioc_dicts.values())[0].keys())

    years = ["2018", "2019", "2020", "2021", "2022", "2023", "2024"]
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
    all_stats, all_paper_data = get_papers_across_years(bioc_dicts, years, dataset_mapping)

    # Write stats to CSV
    write_stats_to_csv(all_stats, dataset_mapping, f"processed_data/{venue}_stats.csv")

    # Save paper data to JSON and PKL, including title, authors, and abstract
    save_paper_data(all_paper_data, f"processed_data/{venue}_paper_data.json", f"processed_data/{venue}_paper_data.pkl", bioc_dicts)

    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    # Run for PubMed
    main(venue="pubmed")
    
    # Run for AMIA
    # main(venue="amia")

   

# if __name__ == "__main__":
#     main()