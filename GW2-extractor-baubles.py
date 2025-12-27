import subprocess
from datetime import datetime

# Generate timestamp
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
output_file = f"Baubles/{timestamp}-baubles.csv"

# Run the extractor
subprocess.run([
    "python", "GW2-extractor.py",
    "--api-keys", "api_keys_baubles.txt",
    "--item-ids", "70093",
    "--output", output_file,
    "--verbose"
])
