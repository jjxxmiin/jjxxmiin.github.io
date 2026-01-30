import os
import shutil
from daily_paper_bot import extract_arxiv_info, download_images, IMAGE_DIR

def test_extraction():
    # Use the paper ID we found earlier: 2601.18129
    paper_id = "2601.18129"
    
    print(f"Testing extraction for paper {paper_id}...")
    images = extract_arxiv_info(paper_id)
    
    if not images:
        print("FAIL: No images found.")
        return
        
    print(f"SUCCESS: Found {len(images)} images.")
    for img in images:
        print(f" - {img['src_filename']}: {img['caption'][:50]}...")
        
    print("\nTesting download...")
    # Use a temp test dir for this test to avoid cluttering actual assets if we want
    # But for now, let's just use the real one and clean up or inspect it.
    # Actually, let's let it run as is to verify full path creation.
    
    downloaded = download_images(images, paper_id)
    
    if not downloaded:
        print("FAIL: No images downloaded.")
        return
        
    print(f"SUCCESS: Downloaded {len(downloaded)} images.")
    
    target_dir = os.path.join(IMAGE_DIR, paper_id)
    if os.path.exists(target_dir):
        print(f"Verified directory exists: {target_dir}")
        print(f"Contents: {os.listdir(target_dir)}")
    else:
        print(f"FAIL: Directory {target_dir} not created.")
        
    # Optional: cleanup
    # shutil.rmtree(target_dir) 
    # print("Cleanup complete.")

if __name__ == "__main__":
    test_extraction()
