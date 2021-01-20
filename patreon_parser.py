from cloudscraper import CloudScraper
import os
import pickle
from dotenv import load_dotenv

load_dotenv()

class ParseSession():
    session: CloudScraper
    url: str
    
    def __init__(self, session: CloudScraper):
        self.session = session
    
    def parse_patreon_url(self, url: str):    
        self._load_cookies()
        self.url = url
        
        if(self._need_cookies()):
            self._refresh_cookies()

        req = self.session.get(self.url)

        print(req)
        
        # Next up--turn content into list of URLs to download
        # And a list of tags for the page too
        
        return {"req_content":req.content}


    def _need_cookies(self):
        # Put our headers here because it should be the first req of the session
        
        
        return self.session.get('https://www.patreon.com/user').url == 'https://www.patreon.com/login'


    def _refresh_cookies(self):
        data = '{"data":{"type":"user","attributes":{"email":"%s","password":"%s"},"relationships":{}}}' % (os.getenv('PATREON_EMAIL'),os.getenv('PATREON_PWD'))

        self.session.post('https://www.patreon.com/api/login?include=campaign%2Cuser_location&json-api-version=1.0', data=data)
        with open('cookies', 'wb') as f:
            pickle.dump(self.session.cookies, f)
        
    def _load_cookies(self):
        try:
            with open('cookies', 'rb') as f:
                self.session.cookies.update(pickle.load(f))
        except FileNotFoundError:
            return
