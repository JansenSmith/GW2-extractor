import subprocess
from datetime import datetime
import os

# Generate timestamp
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
output_file = f"Full/{timestamp}-full.csv"

# Determine which API keys file to use
if os.path.exists("api_keys_full.txt"):
    api_keys_file = "api_keys_full.txt"
else:
    api_keys_file = "api_keys.txt"
    print("WARNING: api_keys_full.txt not found, defaulting to api_keys.txt")

# Run the extractor with all get_foo flags enabled
subprocess.run([
    "python", "GW2-extractor.py",
    "--api-keys", api_keys_file,
    "--get-unfiltered",
    "--get-shared",
    "--get-materials",
    "--get-bank",
    "--get-wallet",
    "--output", output_file,
    "--verbose"
])
