from serpapi import GoogleSearch
import json
data = ""
with open('keywords.txt','r') as fp:
    data = fp.readlines()


data = [datum.replace("\n","") for datum in data]



master_dictionary = {}
counter = 1
for keyword in data:
    print(f'{counter}: {keyword} ')
    counter = counter + 1
    params = {
    "engine": "google_play",
    "q": keyword,
    "api_key": "[INSERT API KEY]"
    }


    search = GoogleSearch(params)
    results = search.get_dict()
    organic_results = results["organic_results"]

    item_list = organic_results[0]['items']

    for item in item_list:

        if item['link'] not in master_dictionary:
            master_dictionary[item['link']]  = item
        else:
            continue

with open('output.txt', 'w') as file:
    json.dump(master_dictionary, file)
    print("Data written to output")