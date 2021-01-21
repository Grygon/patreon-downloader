from cloudscraper import CloudScraper
import os
import pickle
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()


class ParseSession():
    session: CloudScraper
    url: str
    
    def __init__(self, session: requests.session):
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

        # Next up--turn content into list of URLs to download
        # And a list of tags for the page too
        
        return {"req_content": req.content, "links": filtered_urls}


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
