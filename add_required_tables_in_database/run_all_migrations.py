import os
import subprocess
import sys

def run_migrations():
    migrations_dir = os.path.dirname(os.path.abspath(__file__))
    files = [f for f in os.listdir(migrations_dir) if f.endswith('.py') and f != 'run_all_migrations.py' and f != '__init__.py']
    
    # Sort files to have some deterministic order
    files.sort()
    
    print(f"Found {len(files)} migration scripts.")
    
    for file in files:
        file_path = os.path.join(migrations_dir, file)
        print(f"\n{'='*50}")
        print(f"Running migration: {file}")
        print(f"{'='*50}")
        
        try:
            # Run the script using the same python interpreter
            result = subprocess.run([sys.executable, file_path], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"[SUCCESS] {file} completed successfully.")
                print(result.stdout)
            else:
                print(f"[ERROR] {file} failed with return code {result.returncode}.")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
        except Exception as e:
            print(f"[EXCEPTION] Failed to run {file}: {e}")

if __name__ == "__main__":
    run_migrations()
