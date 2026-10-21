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
- `--item-ids` - Item ID(s) or path to item IDs file. Limits every section of the report - characters,
  bank, materials and shared inventory alike - to those items.
- `--get-unfiltered` - Get ALL items, ignoring item-ids filter
- `--get-shared` - Include shared inventory
- `--get-materials` - Include materials storage
- `--get-bank` - Include bank storage
- `--get-wallet` - Include wallet currencies. **Ignored when `--item-ids` is given** - a wallet row
  carries a *currency* id in the `Item ID` column, and the two namespaces overlap (4 is both Gem and
  Assassin Transform Weapon), so an item filter cannot be applied to it. A filtered report leaves the
  wallet out and prints a note rather than appending every currency in the game.
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
- **API keys file**: One GW2 API key per line. Blank lines are skipped, and anything after a `#`
  or a `,` on a line is ignored - so `YOUR-KEY-HERE,jazz` works and the `,jazz` is treated as a note
  rather than sent as part of the key.
- **Item IDs file**: One item ID per line. Read tolerantly, because this is the file edited
  by hand: a UTF-8 BOM (what Notepad writes) is stripped, blank lines and `#` comments are
  skipped, duplicates are dropped so a pasted id cannot double its rows, and a line that is
  not a number is reported and skipped rather than killing the run.

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

CSV with columns: Account Name, Character Name, Amount, Item ID, Item Name, Value, Source, Description

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

## Tests

The whole suite runs offline against a fake API client - no key, no network, nothing written
outside a temp directory:

```bash
python run_tests.py                        # or: python -m unittest discover -s tests -t .
python -m unittest tests.test_build_rows    # one module
```

| File | What it pins |
|---|---|
| `tests/harness.py` | the shared rig: loads the script, the fixtures, and the fake client |
| `tests/test_build_rows.py` | filtering per section, wallet handling, the value rungs, binding, row order |
| `tests/test_item_ids.py` | `item_ids.txt` parsing - BOM, comments, blanks, duplicates, junk lines |
| `tests/test_baubles_only.py` | end to end: mom's exact flag set returns only the item asked for |
| `tests/record_fixtures.py` | re-records the public API fixtures |

Fixtures are split on purpose. The three public endpoints (`items`, `commerce/prices`,
`currencies`) are **recorded** from the live API into `tests/fixtures/`, so the fake client
cannot silently disagree with reality about response shape - re-run `record_fixtures.py` after
an API change and read the diff. Everything authenticated (account, characters, bank,
materials, shared inventory, wallet) is **hand-written** in `harness.py`, because a recording
of those would put real account names, character names and inventory into the repo.

What the tests cannot catch: API shape drift, rate limiting, and the 404-on-an-all-untradable
price chunk. Those only show up on a live run.

### Testable seam

`build_rows()` is pure - fetched data in, spreadsheet rows out, no API calls and no file IO.
Everything that decides what lands in the CSV lives there, which is why the filtering can be
tested without a key. `main()` is the fetch-and-write shell around it.
