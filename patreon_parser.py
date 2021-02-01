import os
import pickle
import re
import requests
import json
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from cloudscraper import CloudScraper
from urllib.parse import urlparse
import time
import validators

load_dotenv()


class ParseSession():
    session: CloudScraper
    url: str
    permitted_creators: list
    soup: BeautifulSoup

    def __init__(self, session: CloudScraper):
        self.session = session
        self._load_cookies()
        self.permitted_creators = os.getenv(
            'CREATORS').replace(" ", "").split(",")

        if(self._need_cookies()):
            self._refresh_cookies()

    def parse_patreon_url(self, url: str):
                
        self.url = url

        is_redir = True

        while is_redir:
            # Let's just double check we actually got a URL
            if not validators.url(self.url):
                print("URL is malformed: " + self.url)
                return
            
            req = self.session.head(self.url)

            if not req.ok:
                return

            is_redir = req.is_redirect

            if is_redir:
                self.url = req.next.url

        # For older mailgun URLs where we don't know where we'll end up,
        # validate we end at patreon
        post_regex = r"patreon\.com\/posts"
        if not re.search(string=self.url, pattern=post_regex):
            return

        try:
            req = self.session.get(self.url)
        except requests.exceptions.ConnectionError:
            return

        # Double check all is well at our final destination
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

        if len(campaign_obj) != 1:
            raise Exception("Invalid Campaign Object--not a valid post")

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

        self.soup = BeautifulSoup(
            campaign_obj.post.data.attributes.content, "html5lib")
        all_links = self.get_attachments(campaign_obj)

        for link in self.soup.findAll('a', attrs={'href': re.compile("^https?://")}):
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
            "dungeondraft": 0,
            "adventure": 0
        }

        for tag in data["tags"]:
            self.weight_type(types, tag)

        self.weight_type(types, data["title"])

        self.weight_type(types, self.soup.text, .2, True)

        return max(types, key=types.get)

    def weight_type(self, types, text, mod=1, count=False):
        formatted = text.lower()

        c = 1

        if "token" in formatted:
            if count:
                c = formatted.count("token")
            types["token"] += 1*mod*c
        if "map" in formatted or "encounter" in formatted:
            if count:
                # I don't think we want to count encounters here... eh...... let's try it
                c = formatted.count("map") + formatted.count("encounter")
            types["map"] += 1*mod*c
        if "asset" in formatted or "empty room" in formatted:
            if count:
                # Putting "Empty Rooms" under assets since they really aren't full maps
                c = formatted.count("asset") + formatted.count("empty room")
            types["asset"] += 1*mod*c
        if "dungeon draft" in formatted or "dungeondraft" in formatted:
            if count:
                c = formatted.count("dungeondraft") + \
                                    formatted.count("dungeon draft")
            types["dungeondraft"] += 5*mod*c
        if "adventure" in formatted or "module" in formatted:
            if count:
                c = formatted.count("adventure") + formatted.count("module")
            # We're accidentally picking up on adventurer...
            if "adventurer" in formatted:
                if count:
                    c -= .5*formatted.count("adventurer")
                else:
                    # If we aren't counting I can't think of a good way to handle this
                    return

            # If it's an adventure it probably references maps
            types["adventure"] += .3*mod*c
            types["map"] -= .1*mod*c

    def get_attachments(self, campaign_obj):
        attachments = []

        arr = campaign_obj.post.included
        for i in range(len(arr)):
            if hasattr(arr[i], 'type') and arr[i].type == 'attachment':
                attachments.append(arr[i].attributes.url)

        return attachments

    def _need_cookies(self):
        # Do some looping in case Patreon doesn't like us anymore
        count = 0
        while count <= 10:
            count += 1
            try:
                return self.session.get('https://www.patreon.com/user').url == 'https://www.patreon.com/login'
            except ConnectionError:
                print("Failed to check for login, sleeping for %s seconds" % str((count + 1) * 10))
                time.sleep((count + 1) * 10)

        raise ConnectionError("Failed to connect to Patreon")

    def _refresh_cookies(self):
        data='{"data":{"type":"user","attributes":{"email":"%s","password":"%s"},"relationships":{}}}' % (
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
    pos=0
    while True:
        match=text.find('{', pos)
        if match == -1:
            break
        try:
            result, index=decoder.raw_decode(text[match:])
            yield result
            pos=match + index
        except ValueError:
            pos=match + 1

# Setting up dict->obj conversion


class obj:
    def __init__(self, dict1):
        self.__dict__.update(dict1)


def dict2obj(dict1):
    return json.loads(json.dumps(dict1), object_hook=obj)
