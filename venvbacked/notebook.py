from bs4 import BeautifulSoup
import requests
import re

url = 'https://pubmed.ncbi.nlm.nih.gov/'

# Get links to articles
response = requests.get(url + '?term=insomnia&sort=date')
soup = BeautifulSoup(response.text, "html.parser")

for line in soup.findAll('a'):
    link = str(line.get('href'))
    l = re.search(r'/([0-9]+/)', link)

    try:
        l = l.group(1) # url extension
        r = requests.get(url + l)
        soup = BeautifulSoup(r.text, "html.parser")

        # get the abstract
        for x in soup.main.find_all('p'):
            pass #print(x.get_text())

        # get the author
        for x in soup.main.header.find_all('span'):
            found = re.search(r'full-name">(.+)(</span>){2}$', str(x))

            if not found:
                pass
            else:
                print(found.group(1))
    except:
        print("no link")
        pass


#download_url = 'http://web.mta.info/developers/'+ link
#time.sleep(1)


