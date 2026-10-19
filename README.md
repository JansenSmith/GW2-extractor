# GW2-extractor

Extract Guild Wars 2 inventory data across accounts and characters to CSV format.

## Usage

This is a workhorse script designed to be called with arguments from other scripts or the command line.
```bash
python GW2-extractor.py [OPTIONS]
```

Running without arguments displays this README.

## Options

- `--api-keys` - API key(s) or path to API keys file (default: `api_keys.txt`)
- `--output PATH` - Output CSV filename (default: `GW2_data_output.csv`)
- `--item-ids` - Item ID(s) or path to item IDs file
- `--get-unfiltered` - Get ALL items, ignoring item-ids filter
- `--get-shared` - Include shared inventory
- `--get-materials` - Include materials storage
- `--get-bank` - Include bank storage
- `--get-wallet` - Include wallet currencies
- `--verbose` - Enable verbose output

## Input Formats

**Direct values:**
```bash
--item-ids 70093
--item-ids 70093 18729 12345
--api-keys YOUR-API-KEY-HERE
--api-keys KEY1 KEY2 KEY3
```

**From files:**
- **API keys file**: One GW2 API key per line
- **Item IDs file**: One item ID per line

## Examples

Search for Shiny Baubles (70093) across all characters:
```bash
python GW2-extractor.py --item-ids 70093
```

Full inventory dump:
```bash
python GW2-extractor.py --get-unfiltered --get-shared --get-materials --get-bank --get-wallet --output full_inventory.csv
```

Multiple specific items:
```bash
python GW2-extractor.py --item-ids 70093 18729 12345 --output specific_items.csv
```

Using direct API key:
```bash
python GW2-extractor.py --api-keys YOUR-KEY-HERE --item-ids 70093 --output baubles.csv
```

Character inventories with verbose output:
```bash
python GW2-extractor.py --get-unfiltered --verbose --output characters.csv
```

## Output

CSV with columns: Account Name, Character Name, Amount, Item ID, Item Name, Value, Description, Source

**Value** is what one of the item is worth, in gold. 1 gold is exactly 10000 copper, so the four
decimals read off as silver and copper: `0.3000` is 30 silver, `2.0887` is 2 gold 8 silver 87 copper.
Multiply by `Amount` for what a stack is worth.

**Source** says where that number came from, and is only there to explain a surprising Value:

- `TP` - lowest current sell listing on the trading post, with the 15% trading post fee already
  taken off, so it is what you would actually pocket.
- `Vendor` - the item cannot be listed on the trading post (or this copy is bound), but a merchant
  will buy it. No fee applies, so the number is raw.
- `-` - no value: the item can be neither sold on the trading post nor vendored. Wallet currencies
  are always `-`, since they are not items and have no price.
