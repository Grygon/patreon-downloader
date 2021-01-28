import os
import pickle
import re
import requests
import json
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from cloudscraper import CloudScraper

load_dotenv()


class ParseSession():
    session: CloudScraper
    url: str
    permitted_creators: list

    def __init__(self, session: CloudScraper):
        self.session = session
        self._load_cookies()
        self.permitted_creators = os.getenv(
            'CREATORS').replace(" ", "").split(",")

        if(self._need_cookies()):
            self._refresh_cookies()

    def parse_patreon_url(self, url: str):
        self.url = url

        req = self.session.get(self.url)
        
        if not req.ok:
            return

        # Find our data from the provided Object in our page
        objects = []
        for result in extract_json_objects(req.text):
            objects.append(result)

        # Filter out blanks because there are quite a few of them
        objects = [i for i in objects if i != {}]

        # Now find our "campaign" object which contains all the data we care about
        campaign_obj = [i for i in filter(lambda x: 'campaign' in x, objects)]

        if len(campaign_obj) > 1:
            raise Exception("Too many campaign objects")
            
        campaign_obj = dict2obj(campaign_obj[0])

        arr = campaign_obj.post.included
        for i in range(len(arr)):
            if hasattr(arr[i].attributes, 'full_name'):
                author = arr[i].attributes.full_name
                author_short = arr[i].attributes.url.split("/")[-1]
                break

        # Check if they're a permitted creator, then check that we can view the post
        if (len(self.permitted_creators) and (author_short not in self.permitted_creators)) \
            or not campaign_obj.post.data.attributes.current_user_can_view:
            return {"author_short": author_short}

        if campaign_obj.post.data.attributes.post_type == 'poll':
            return {"type": 'poll',
                    "author_short": author_short}
            

        soup = BeautifulSoup(
            campaign_obj.post.data.attributes.content, "html5lib")
        all_links = self.get_attachments(campaign_obj)
        
        for link in soup.findAll('a', attrs={'href': re.compile("^https?://")}):
            all_links.append(link.get('href'))

        filters = \
            [r".*patreon\.com\/file\?h\=.*",
             r".*dropboxusercontent\.com",
             r".*dropbox\.com"]
        filtered_urls = []

        for f in filters:
            filtered_urls += [l for l in all_links if re.match(f, l)]

        # Now we filter down to only links we can access
        filtered_urls = [x for x in filtered_urls if self.session.head(x).ok]

        # Next up--turn content into list of URLs to download
        # And a list of tags for the page too

        title = campaign_obj.post.data.attributes.title

        post_id = campaign_obj.post.data.id

        unclean_tags = campaign_obj.post.data.relationships.user_defined_tags.data

        tags = [x.id.split(";")[1] for x in unclean_tags]

        posted_date = campaign_obj.post.data.attributes.created_at.split("T")[
            0]
        edited_date = campaign_obj.post.data.attributes.edited_at.split("T")[0]

        data = {"links": filtered_urls,
                "title": title,
                "tags": tags,
                'author': author,
                'author_short': author_short,
                'posted_date': posted_date,
                'date': edited_date,
                'id': post_id}

        data["type"] = self.determine_type(data)

        return data

    def determine_type(self, data):
        types = {
            "": 0.9,
            "token": 0,
            "map": 0,
            "asset": 0,
            "dungeondraft": 0
        }

        for tag in data["tags"]:
            if "token" in tag:
                types["token"] += 1
            if "map" in tag or "encounter" in tag:
                types["map"] += 1
            if "asset" in tag:
                types["asset"] += 1
            if "dungeon draft" in tag or "dungeondraft" in tag:
                types["asset"] += 5

        return max(types)

    def get_attachments(self, campaign_obj):
        attachments = []
        
        arr = campaign_obj.post.included
        for i in range(len(arr)):
            if hasattr(arr[i], 'type') and arr[i].type == 'attachment':
                attachments.append(arr[i].attributes.url)
                
        return attachments

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
