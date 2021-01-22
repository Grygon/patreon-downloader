from cloudscraper import CloudScraper
import os
import pickle
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import json


load_dotenv()


class ParseSession():
    session: CloudScraper
    url: str

    def __init__(self, session: CloudScraper):
        self.session = session
        self._load_cookies()

        if(self._need_cookies()):
            self._refresh_cookies()

    def parse_patreon_url(self, url: str):
        self.url = url

        req = self.session.get(self.url)
        soup = BeautifulSoup(req.text, "html5lib")
        all_links = []

        for link in soup.findAll('a', attrs={'href': re.compile("^https?://")}):
            all_links.append(link.get('href'))

        filters = [r".*patreon\.com\/file\?h\=.*", r".*dropbox\.com"]
        filtered_urls = []

        for f in filters:
            filtered_urls += [l for l in all_links if re.match(f, l)]
            
        # Now we filter down to only links we can access
        filtered_urls = [x for x in filtered_urls if self.session.head(x).ok]

        # Next up--turn content into list of URLs to download
        # And a list of tags for the page too

        # Find our data from the provided Object in our page
        objects = []
        for result in extract_json_objects(soup.text):
            objects.append(result)

        # Filter out blanks because there are quite a few of them
        objects = [i for i in objects if i != {}]

        # Now find our "campaign" object which contains all the data we care about
        campaign_obj = [i for i in filter(lambda x: 'campaign' in x, objects)]

        if len(campaign_obj) > 1:
            raise Exception("Too many campaign objects")
        campaign_obj = dict2obj(campaign_obj[0])

        title = campaign_obj.post.data.attributes.title

        unclean_tags = campaign_obj.post.data.relationships.user_defined_tags.data

        tags = [x.id.split(";")[1] for x in unclean_tags]
        
        date = campaign_obj.post.data.attributes.created_at.split("T")[0]
        
        arr = campaign_obj.post.included 
        for i in range(len(arr)):
            if hasattr(arr[i].attributes,'full_name'):
                author = arr[i].attributes.full_name
                break

        return {"links": filtered_urls, "title": title, "tags": tags, "object": campaign_obj, 'author': author, 'date': date}

    def _need_cookies(self):
        # Put our headers here because it should be the first req of the session

        return self.session.get('https://www.patreon.com/user').url == 'https://www.patreon.com/login'

    def _refresh_cookies(self):
        data = '{"data":{"type":"user","attributes":{"email":"%s","password":"%s"},"relationships":{}}}' % (
            os.getenv('PATREON_EMAIL'), os.getenv('PATREON_PWD'))

        self.session.post(
            'https://www.patreon.com/api/login?include=campaign%2Cuser_location&json-api-version=1.0', data=data)
        with open('cookies', 'wb') as f:
            pickle.dump(self.session.cookies, f)

    def _load_cookies(self):
        try:
            with open('cookies', 'rb') as f:
                self.session.cookies.update(pickle.load(f))
        except FileNotFoundError:
            return


def extract_json_objects(text, decoder=json.JSONDecoder()):
    """Find JSON objects in text, and yield the decoded JSON data

    Does not attempt to look for JSON arrays, text, or other JSON types outside
    of a parent JSON object.

    """
    pos = 0
    while True:
        match = text.find('{', pos)
        if match == -1:
            break
        try:
            result, index = decoder.raw_decode(text[match:])
            yield result
            pos = match + index
        except ValueError:
            pos = match + 1

# Setting up dict->obj conversion


class obj:
    def __init__(self, dict1):
        self.__dict__.update(dict1)


def dict2obj(dict1):
    return json.loads(json.dumps(dict1), object_hook=obj)
