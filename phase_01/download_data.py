import os
import tarfile
from huggingface_hub import hf_hub_download

# Configuration
REPO_ID = "your-hf-username/your-dataset-name" # Change this!
FILENAME = "dataset.tar.gz"
EXTRACT_DIR = "./data" # Where you want the images to live locally

def main():
    print(f"Downloading {FILENAME} from Hugging Face...")
    
    # If your dataset is PRIVATE, you must log in first using:
    # huggingface-cli login
    # in your terminal before running this script.
    try:
        file_path = hf_hub_download(
            repo_id=REPO_ID, 
            filename=FILENAME, 
            repo_type="dataset"
        )
        print(f"Download complete! File saved to Hugging Face cache.")
    except Exception as e:
        print(f"Failed to download: {e}")
        return

    print("Extracting images...")
    os.makedirs(EXTRACT_DIR, exist_ok=True)
    
    with tarfile.open(file_path, "r:gz") as tar:
        tar.extractall(path=EXTRACT_DIR)
        
    print(f"Extraction complete! Images are ready in {EXTRACT_DIR}/")

if __name__ == "__main__":
    main()