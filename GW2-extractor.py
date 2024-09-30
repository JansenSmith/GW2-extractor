import pandas as pd
from gw2api import GuildWars2Client

def get_value(wallet, id):
    for item in wallet:
        if item['id'] == id:
            return item['value']
    return 0

with open('api_keys.txt', 'r') as opened_api_file:
    api_keys = [line.strip() for line in opened_api_file.readlines()]

item_ids = [70093, 24517]

result = []
verbosity = True  # Set to False if you don't want the "Adding element"

for aaa in api_keys:
	gg = GuildWars2Client(api_key=aaa)

	jj = gg.account.get()['name']
	
	vv = jj + '.wallet'
	wallet = gg.accountwallet.get()
	for currency in gg.currencies.get():
		ccc = gg.currencies.get(id=currency)
		ww = get_value(wallet,currency)
		nn = ccc['name']
		dd = ccc['description']
		if nn:
			if verbosity:
			    print("Adding element:", [jj, vv, ww, nn])
			result.append([jj, vv, ww, nn])

df = pd.DataFrame(result, columns=['Account Name', 'Character Name', 'Amount', 'Item Name'])

filename = 'GW2_data_output.csv' 
df.to_csv(filename, index=False)
print("Saved to:", filename)
