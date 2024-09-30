import pandas as pd
from gw2api import GuildWars2Client

with open('api_keys.txt', 'r') as opened_api_file:
    api_keys = [line.strip() for line in opened_api_file.readlines()]
    
print(api_keys)
sys.exit()

item_ids = [70093, 24517]

result = []
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
            
            result.append([jj, vv, ww, nn, ooo])

df = pd.DataFrame(result, columns=['Account Name', 'Character Name', 'Count', 'Item Name', 'Item ID'])

print(df)
