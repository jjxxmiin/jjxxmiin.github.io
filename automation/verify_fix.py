import os

def test_makedirs_logic(save_path):
    print(f"Testing directory creation for: {save_path}")
    parent_dir = os.path.dirname(save_path)
    print(f"Parent directory: {parent_dir}")
    
    os.makedirs(parent_dir, exist_ok=True)
    
    if os.path.exists(parent_dir):
        print(f"SUCCESS: Directory '{parent_dir}' created.")
        with open(save_path, 'w') as f:
            f.write("test content")
        if os.path.exists(save_path):
            print(f"SUCCESS: File '{save_path}' written.")
            # Cleanup for test purposes
            os.remove(save_path)
            # Only remove if empty to avoid deleting other things, but here it's fine for the test directory
            try:
                 os.removedirs(parent_dir)
                 print(f"SUCCESS: Cleaned up '{parent_dir}'.")
            except OSError:
                 pass
    else:
        print(f"FAILURE: Directory '{parent_dir}' was NOT created.")

if __name__ == "__main__":
    # Simulate the failing path reported by the user
    test_path = "test_assets/papers/2602.19313/Figure/test_image.png"
    test_makedirs_logic(test_path)
