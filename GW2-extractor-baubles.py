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
    # Only the characters who actually hold some. A bauble hunt across a full roster is
    # mostly zero rows otherwise; the run prints how many it hid.
    "--hide-empty",
    "--output", output_file,
    "--verbose"
])
