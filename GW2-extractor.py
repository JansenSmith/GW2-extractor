import pandas as pd
from gw2api import GuildWars2Client

with open('api_keys.txt', 'r') as opened_api_file:
    api_keys = [line.strip() for line in opened_api_file.readlines()]

item_ids = [70093, 24517]

result = []
verbosity = True  # Set to False if you don't want the "Adding element"

for aaa in api_keys:
    gg = GuildWars2Client(api_key=aaa)
    
    jj = gg.account.get()['name']
    
    cc = gg.characters.get()
    for vv in cc:
        ss = gg.charactersinventory.get(vv)
        
        for ooo in item_ids:
            qq = [d['count'] for bag in ss['bags'] if bag for d in bag.get('inventory',[]) if isinstance(d, dict) and d['id'] == ooo]
            
            ww = sum(qq)
            
            nn = gg.items.get(id=ooo)['name']
            
            if verbosity:
                print("Adding element:", [jj, vv, ww, nn, ooo])
            result.append([jj, vv, ww, nn, ooo])

df = pd.DataFrame(result, columns=['Account Name', 'Character Name', 'Amount', 'Item Name', 'Item ID'])

filename = 'GW2_data_output.csv' 
df.to_csv(filename, index=False)
print("Saved to:", filename)
