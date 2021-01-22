import requests
import zipfile
import re
import rfc6266
import cgi
import os
from cloudscraper import CloudScraper
from dotenv import load_dotenv
from pathvalidate import sanitize_filename

load_dotenv()
directory = sanitize_filename(os.getenv('DIR'))


class DownloadHandler():
    session: CloudScraper
    url: str
    download_location: str
    final_location: str
    filename: str
    post_dir: str
    
    author = "Unknown Author"
    post = "Unknown Post"

    def __init__(self, session: CloudScraper):
        self.session = session
        if not os.path.exists(directory):
            os.makedirs(directory)

    def download_url(self, url):
        self.url = url

        domain = url.split(".")[1]
        
        if domain == "dropbox":
            self.format_dropbox()
        
        self.general_process()
        

    def format_dropbox(self):
        self.url = self.url.split("?")[0] + "?dl=1"

    def general_process(self):
        r = self.session.head(self.url, allow_redirects=True)

        # This is very specific but w/e
        full_filename = sanitize_filename(cgi.parse_header(
            r.headers.get('Content-Disposition'))[1]['filename'])
        self.filename, ext = os.path.splitext(full_filename)
        
        self.post_dir = os.path.join(directory, sanitize_filename(self.author), sanitize_filename(self.post))

        self.download_location = os.path.join(self.post_dir, full_filename)

        if not os.path.exists(self.post_dir):
            os.makedirs(self.post_dir)
        
        if not os.path.isfile(self.download_location):
            r = self.session.get(self.url, allow_redirects=True)

            open(self.download_location, 'wb').write(r.content)

        if ext == '.zip':
            self.handle_zip()
            self.final_location = post_dir
        else:
            self.final_location = self.download_location

        print("Downloaded " + str(self.filename))

    def handle_zip(self):
        with zipfile.ZipFile(self.download_location, 'r') as zip_ref:
            zip_ref.extractall(self.post_dir)
        os.remove(self.download_location)