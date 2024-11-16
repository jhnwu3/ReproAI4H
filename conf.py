# Main Script for Aggregating Conference Papers and Extracting Content
from src.conf_proc.scrape_conf import ConferenceDownloader
from src.conf_proc.clean_conf import ConferencePaperCleaner
from src.conf_proc.measure_conf import PDFContentProcessor
from src.conf_proc.pathing import ConferencePathManager


def start_debug():
    print("Starting debug mode...")
    
    # Initialize path manager in debug mode
    path_manager = ConferencePathManager(base_dir="data", debug=True)
    
    # Set up debug environment with 5 random papers from ML4H 2023
    path_manager.setup_debug_environment(conference='ml4h')
    
    # Initialize processors with debug path manager
    downloader = ConferenceDownloader(path_manager)
    processor = PDFContentProcessor(path_manager)
    
    
    # Process only ML4H in debug mode
    conference = 'ml4h'
    print(f"\nProcessing {conference.upper()} in debug mode...")
    downloader.process_conference(conference)
    print("Download Functionality Complete!")
    processor.process_conference(conference)
    print("Processing Functionality Complete!")
    cleaner = ConferencePaperCleaner(path_manager, device="cuda:0")
    cleaner.clean_conference_papers(conference)
    print("Cleaning Functionality Complete!")


def main():

    debug = True 
    if debug:
        return start_debug()
    else:
        print("Downloading and processing conference papers...")
        path_manager = ConferencePathManager(base_dir="data")
        
        # Initialize processors with path manager
        downloader = ConferenceDownloader(path_manager)
        processor = PDFContentProcessor(path_manager)
        cleaner = ConferencePaperCleaner(path_manager, device="cuda:0")
        
        for conference in ['chil', 'ml4h', 'mlhc']:
            print(f"\nProcessing {conference.upper()}...")
            downloader.process_conference(conference)
            processor.process_conference(conference)
            cleaner.clean_conference_papers(conference)

if __name__ == "__main__":
    main()