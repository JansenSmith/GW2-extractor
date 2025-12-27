import subprocess
from datetime import datetime
import os
import sys

# Check for item_ids.txt file
if not os.path.exists("item_ids.txt"):
    print("ERROR: item_ids.txt not found")
    print("Create item_ids.txt with one item ID per line, e.g.:")
    print("70093")
    print("18729")
    print("12345")
    sys.exit(1)

# Generate timestamp
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
output_file = f"Items/{timestamp}-items.csv"

# Determine which API keys file to use
if os.path.exists("api_keys_items.txt"):
    api_keys_file = "api_keys_items.txt"
else:
    api_keys_file = "api_keys.txt"
    print("WARNING: api_keys_items.txt not found, defaulting to api_keys.txt")

# Run the extractor with item_ids from file
subprocess.run([
    "python", "GW2-extractor.py",
    "--api-keys", api_keys_file,
    "--item-ids", "item_ids.txt",
    "--get-shared",
    "--get-materials",
    "--get-bank",
    "--get-wallet",
    "--output", output_file,
    "--verbose"
])
