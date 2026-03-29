import time
import subprocess
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s | daemon | %(message)s')

POLL_INTERVAL_SECONDS = 3600  # Run every hour

def run_agent():
    logging.info("Triggering Gmail Triage Agent run...")
    
    # We call main.py as a subprocess to ensure memory and file locks are completely cleared
    try:
        result = subprocess.run([sys.executable, "main.py", "run"], capture_output=True, text=True, check=False)
        
        # Log the output from the subprocess
        for line in result.stdout.splitlines():
            if line.strip():
                logging.info(f"[main] {line}")
                
        if result.returncode != 0:
            logging.error(f"Agent failed with exit code {result.returncode}:\n{result.stderr}")
            for line in result.stderr.splitlines():
                if line.strip():
                    logging.error(f"[main-err] {line}")
        else:
            logging.info("Agent run completed successfully.")
            
    except Exception as e:
        logging.critical(f"Failed to execute main.py: {e}")

if __name__ == "__main__":
    logging.info("Starting Gmail Triage Agent Docker Daemon...")
    while True:
        run_agent()
        logging.info(f"Sleeping for {POLL_INTERVAL_SECONDS // 60} minutes until next run...")
        time.sleep(POLL_INTERVAL_SECONDS)
