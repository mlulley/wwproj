''' Create webpage for medical search '''

import requests
from pprint import pprint
import os, uuid
import pyodbc
import re
import json
from flask import Flask, redirect, url_for, render_template, request
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from bs4 import BeautifulSoup
import azure.cosmos.documents as documents
import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.exceptions as exceptions
from azure.cosmos.partition_key import PartitionKey
import datetime
import config

import pandas as pd
import time

# Global Variables
icdnames = []
rxnames = []
icds = []
rxns = []
files = []
filetracker = [] # keep track of the indeces of file clusters
'''HOST = config.settings['host']
MASTER_KEY = config.settings['master_key']
DATABASE_ID = config.settings['database_id']
CONTAINER_ID = config.settings['container_id']'''


app = Flask(__name__)

@app.route("/", methods=["POST","GET"])
def home():
    if request.method == "POST":
        doc = request.form["nm"]
        #search_index(doc)
        get_data(doc)

    print(files)

    return render_template("index.html", icdnames=icdnames, rxnames=rxnames, icds=icds, rxns=rxns, lenicd=len(icdnames), lenrx=len(rxnames), files=files)

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
                #get_icd(name)
                #get_rxnorm(name)
                search_index(name)

def get_icd(names):
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
        for name in names:
            exists = False
            name = str(name).lower()
            if (name == row[1]):
                for x in icdnames:
                    if (name == str(x)):
                        exists = True
                if not exists:
                    # code found --> insert into array
                    icdnames.insert(0,name)
                    icds.insert(0,row[2])
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

def pubmed_files(name):
    # Connect to my storage
    connect_str = "DefaultEndpointsProtocol=https;AccountName=mywwstorage;AccountKey=HlIn8m0AfR/YINbuL51aB9riMY+ghksRPVlHhf5600mUrlHBKz1zbL14c5ycXX94Ja1oXcasguZ6J4Fr8uYUoQ==;EndpointSuffix=core.windows.net"

    # Create the BlobServiceClient object which will be used to create a container client
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    # Create a unique name for the container
    container_name = name  # + str(uuid.uuid4())
    # Create the container
    container_client = blob_service_client.create_container(container_name)

    # Create a file in local data directory to upload and download
    local_path = "./data"
    local_file_name = '' #str(name + str(uuid.uuid4()) + ".txt")
    upload_file_path = '' # os.path.join(local_path, local_file_name)

    # Get links to articles
    url = 'https://pubmed.ncbi.nlm.nih.gov/'
    response = requests.get(url + '?term=' + name + '&sort=date')
    soup = BeautifulSoup(response.text, "html.parser")

    for line in soup.findAll('a'):
        link = str(line.get('href'))
        l = re.search(r'/([0-9]+/)', link)

        if not l:
            #print("no link")
            pass
        else:
            l = l.group(1) # url extension

            local_file_name = str(name + str(uuid.uuid4()) + ".txt")
            upload_file_path = os.path.join(local_path, local_file_name)

            # Add link to the file
            file = open(upload_file_path, 'w')
            file.write(url+l)
            file.close()

            # Create a blob client using the local file name as the name for the blob
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=local_file_name)
            #print("\nUploading to Azure Storage as blob:\n\t" + local_file_name)
            # Upload the created file
            with open(upload_file_path, "rb") as data:
                blob_client.upload_blob(data)

    search_index(name)

def search_index(name):
    # Setup
    namefile = []
    datasource_name = "mywwstorage"
    skillset_name = "medical-search"
    index_name = "medical-tutorial"
    #indexer_name = "medtutorial-indexer"
    endpoint = "https://wwmedsearch.search.windows.net"
    datasourceConnectionString = "DefaultEndpointsProtocol=https;AccountName=mywwstorage;AccountKey=HlIn8m0AfR/YINbuL51aB9riMY+ghksRPVlHhf5600mUrlHBKz1zbL14c5ycXX94Ja1oXcasguZ6J4Fr8uYUoQ==;EndpointSuffix=core.windows.net"
    headers = {'Content-Type': 'application/json',
               'api-key': '6A719CA26E0D445DFAFDB0220E13B9B4'}
    params = {
        'api-version': '2019-05-06'
    }

    # Create a data source
    datasource_payload = {
        "name": datasource_name,
        "description": "Demo files to demonstrate cognitive search capabilities.",
        "type": "azureblob",
        "credentials": {
            "connectionString": datasourceConnectionString
        },
        "container": {
            "name": name
        }
    }
    r = requests.put(endpoint + "/datasources/" + datasource_name,data=json.dumps(datasource_payload), headers=headers, params=params)
    #print(r.status_code)

    # Create a skillset
    skillset_payload = {
        "name": skillset_name,
        "description":
            "Extract entities, detect language and extract key-phrases",
        "skills":
            [
                {
                    "@odata.type": "#Microsoft.Skills.Text.EntityRecognitionSkill",
                    "categories": ["Organization"],
                    "defaultLanguageCode": "en",
                    "inputs": [
                        {
                            "name": "text", "source": "/document/content"
                        }
                    ],
                    "outputs": [
                        {
                            "name": "organizations", "targetName": "organizations"
                        }
                    ]
                },
                {
                    "@odata.type": "#Microsoft.Skills.Text.LanguageDetectionSkill",
                    "inputs": [
                        {
                            "name": "text", "source": "/document/content"
                        }
                    ],
                    "outputs": [
                        {
                            "name": "languageCode",
                            "targetName": "languageCode"
                        }
                    ]
                },
                {
                    "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
                    "textSplitMode": "pages",
                    "maximumPageLength": 4000,
                    "inputs": [
                        {
                            "name": "text",
                            "source": "/document/content"
                        },
                        {
                            "name": "languageCode",
                            "source": "/document/languageCode"
                        }
                    ],
                    "outputs": [
                        {
                            "name": "textItems",
                            "targetName": "pages"
                        }
                    ]
                },
                {
                    "@odata.type": "#Microsoft.Skills.Text.KeyPhraseExtractionSkill",
                    "context": "/document/pages/*",
                    "inputs": [
                        {
                            "name": "text", "source": "/document/pages/*"
                        },
                        {
                            "name": "languageCode", "source": "/document/languageCode"
                        }
                    ],
                    "outputs": [
                        {
                            "name": "keyPhrases",
                            "targetName": "keyPhrases"
                        }
                    ]
                }
            ]
    }
    r = requests.put(endpoint + "/skillsets/" + skillset_name, data=json.dumps(skillset_payload), headers=headers,params=params)
    #print(r.status_code)

    # Create an index
    index_payload = {
        "name": index_name,
        "fields": [
            {
                "name": "id",
                "type": "Edm.String",
                "key": "true",
                "searchable": "true",
                "filterable": "false",
                "facetable": "false",
                "sortable": "true"
            },
            {
                "name": "content",
                "type": "Edm.String",
                "sortable": "false",
                "searchable": "true",
                "filterable": "false",
                "facetable": "false"
            },
            {
                "name": "languageCode",
                "type": "Edm.String",
                "searchable": "true",
                "filterable": "false",
                "facetable": "false"
            },
            {
                "name": "keyPhrases",
                "type": "Collection(Edm.String)",
                "searchable": "true",
                "filterable": "false",
                "facetable": "false"
            },
            {
                "name": "organizations",
                "type": "Collection(Edm.String)",
                "searchable": "true",
                "sortable": "false",
                "filterable": "false",
                "facetable": "false"
            }
        ]
    }
    r = requests.get(endpoint + "/indexes/" + index_name + "/docs?api-version=2019-05-06&search=" + name, headers=headers)
    #print(r.status_code)

    '''# Create an indexer
    indexer_payload = {
        "name": indexer_name,
        "dataSourceName": datasource_name,
        "targetIndexName": index_name,
        "skillsetName": skillset_name,
        "fieldMappings": [
            {
                "sourceFieldName": "metadata_storage_path",
                "targetFieldName": "id",
                "mappingFunction":
                    {"name": "base64Encode"}
            },
            {
                "sourceFieldName": "content",
                "targetFieldName": "content"
            }
        ],
        "outputFieldMappings":
            [
                {
                    "sourceFieldName": "/document/organizations",
                    "targetFieldName": "organizations"
                },
                {
                    "sourceFieldName": "/document/pages/*/keyPhrases/*",
                    "targetFieldName": "keyPhrases"
                },
                {
                    "sourceFieldName": "/document/languageCode",
                    "targetFieldName": "languageCode"
                }
            ],
        "parameters":
            {
                "maxFailedItems": -1,
                "maxFailedItemsPerBatch": -1,
                "configuration":
                    {
                        "dataToExtract": "contentAndMetadata",
                        "imageAction": "generateNormalizedImages"
                    }
            }
    }
    r = requests.get(endpoint + "/indexers/" + indexer_name,data=json.dumps(indexer_payload), headers=headers)
    print(r.status_code)

    # Get indexer status
    r = requests.get(endpoint + "/indexers/" + indexer_name + "/status", headers=headers, params=params)
    pprint(json.dumps(r.json(), indent=1))'''

    # Query service for an index definition
    r = requests.get(endpoint + "/indexes/" + index_name,headers=headers, params=params)
    #pprint(json.dumps(r.json(), indent=1))

    # Query the index to return the content and keyphrases
    r1 = requests.get(endpoint + "/indexes/" + index_name + "/docs?&search=*&$select=content", headers=headers, params=params)
    r2 = requests.get(endpoint + "/indexes/" + index_name + "/docs?&search=*&$select=keyphrases", headers=headers, params=params)
    content = [article['content'] for article in r1.json()['value']]
    phrases = [article['keyphrases'] for article in r2.json()['value']]

    # files and key phrases will be at the same index of their respective array
    for x in content:
        namefile.append(x)
    for x in phrases:
        get_icd(x)

    files.append(namefile)
    filetracker.append(name)

    #pprint(json.dumps(r.json(), indent=1))

if __name__ == "__main__":
    #get_icd(["insomnia","Megan"])
    #search_index("insomnia")
    #pubmed_files("insomnia")
    app.run()


'''  goes at bottom of pubmed_files()
# List the blobs in the container
print("\nListing blobs...")
blob_list = container_client.list_blobs()
for blob in blob_list:
    print("\t" + blob.name)

# Download the blob to a local file
# Add 'DOWNLOAD' before the .txt extension so you can see both files in the data directory
download_file_path = os.path.join(local_path, str.replace(local_file_name, '.txt', 'DOWNLOAD.txt'))
print("\nDownloading blob to \n\t" + download_file_path)
with open(download_file_path, "wb") as download_file:
    download_file.write(blob_client.download_blob().readall())
'''
