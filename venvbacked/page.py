''' Create webpage for medical search '''

import requests
from pprint import pprint
import os
import pyodbc
import re
#import bootstrap_py
from flask import Flask, redirect, url_for, render_template, request

icdnames = []
rxnames = []
icds = []
rxns = []

app = Flask(__name__)

@app.route("/", methods=["POST","GET"])
def home():
    if request.method == "POST":
        doc = request.form["nm"]
        get_data(doc)

    return render_template("index.html", icdnames=icdnames, rxnames=rxnames, icds=icds, rxns=rxns, lenicd=len(icdnames), lenrx=len(rxnames))

'''@app.route("/<name>")
def user(name):
    return ("Hello " + name)'''

def get_data(doc):
    subscription_key = "31e4531244d648ceb00aecb7ea7e67d6"
    endpoint = "https://analyzetexts.cognitiveservices.azure.com"
    keyphrase_url = endpoint + "/text/analytics/v2.1/keyphrases"

    documents = {"documents": [{"id":"1","language":"en","text":str(doc)}]}

    # identify names entity
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}
    response = requests.post(keyphrase_url, headers=headers, json=documents)
    key_phrases = response.json()
    ents = [article['keyPhrases'] for article in key_phrases['documents']]
    ents = ents[0]

    if str(ents) == "[[]]":
        return 1
    else:
        for name in ents:
            name = name.lower()
            # if already in list, skip it
            exists = False
            for x in (rxnames+icdnames):
                if (str(x) == name):
                    exists = True
                    print(name + " already in list")
                    break
            if not exists:
                get_icd(name)
                get_rxnorm(name)

def get_icd(name):
    # get ICD data from SQL database
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

    while row and not found:
        if (name == row[1]):
            # code found --> insert into array
            icdnames.insert(0,name)
            icds.insert(0,row[2])
            found = True
        row = cursor.fetchone()

def get_rxnorm(name):
    # get RxNorm data from API
    baseurl = "https://rxnav.nlm.nih.gov/REST/rxcui?name="
    uagent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.82 Safari/537.36"
    url = baseurl + name

    try:
        # web request to get code
        response = requests.request('GET', url)
        rx = re.search(r'(rxnormId>)([0-9]*)(</rx)', response.text)

        if not rx:
            pass
        else:
            # code found --> insert into array
            rxnames.insert(0,name)
            rxns.insert(0,rx.group(2))

    except ValueError as e:
        print("Error: " + str(e))
    except AttributeError as e:
        print("Error: " + str(e))

if __name__ == "__main__":
    app.run()
