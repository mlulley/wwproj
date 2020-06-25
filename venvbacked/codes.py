''' WinWire Medical Mining Project '''
''' Megan Lulley '''

import requests
# pprint is used to format the JSON response
from pprint import pprint
import os
import re
import pyodbc

def get_rx_data(names):
    baseurl = "https://rxnav.nlm.nih.gov/REST/rxcui?name="
    uagent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.82 Safari/537.36"

    for name in names:
        url = baseurl + name

        try:
            response = requests.request('GET',url)
            code = re.search(r'(rxnormId>)([0-9]*)(</rx)', response.text)

            if not code:
                pass
            else:
                print(name + " " + code.group(2))
        except ValueError as e:
            print("Error: " + str(e))
        except AttributeError as e:
            print("Error: " + str(e))

def get_icd_data(names):
    found = False
    server = 'mysqlserver217.database.windows.net'
    database = 'mySampleDatabase'
    username = 'azureadmin'
    password = 'Rareair23'
    driver = '{ODBC Driver 17 for SQL Server}'
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+ password)
    cursor = cnxn.cursor()
    cursor.execute("SELECT TOP (100) * FROM [dbo].[CodesICD]")
    row = cursor.fetchone()

    for name in names:
        while row and not found:
            if (name == row[1]):
                print (str(row[2]) + " " + str(row[1]))
                found = True
            row = cursor.fetchone()
        found = False

def main():
    subscription_key = "633550d5f833422e8db562d491a3c0e8"
    endpoint = "https://analyzetext.cognitiveservices.azure.com"
    keyphrase_url = endpoint + "/text/analytics/v2.1/keyphrases"

    documents = {"documents": [
        {"id": "1", "language": "en",
        "text": "I am experiencing insomnia"},
        {"id": "2", "language": "en",
        "text": "Covid-10"},
        {"id": "3", "language": "en",
        "text": "She has pneumonia"},
        {"id": "4", "language": "en",
        "text": "Fluorine"},
        {"id": "5", "language": "en",
        "text": "Warfarin"}
    ]}

    headers = {"Ocp-Apim-Subscription-Key": subscription_key}
    response = requests.post(keyphrase_url, headers=headers, json=documents)
    key_phrases = response.json()
    #pprint(key_phrases)

    # extract all the key phrases and convert to compatible/readable format
    names = [article['keyPhrases'] for article in key_phrases['documents']]
    names = [str(name)[3:len(name)-3].lower() for name in names]
    print(names)

    print(' ')
    get_icd_data(names)
    print(' ')
    get_rx_data(names)

# Main Execution
if __name__ == '__main__':
    main()



'''
create UI webpage with input textbox (documents block)
get codes from here using button
display in table format for readability
    one for icd-10, one for rxNorm   
    one call to local, one call to API

then... more into ML for near neighbor detection
'''
