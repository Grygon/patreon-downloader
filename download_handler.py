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
directory = os.getenv('DIR')


class DownloadHandler():
    session: CloudScraper
    url: str
    download_location: str
    final_location: str
    filename: str

    def __init__(self, session: CloudScraper):
        self.session = session
        if not os.path.exists(directory):
            os.makedirs(directory)

    def download_url(self, url):
        self.url = url

        r = self.session.head(url, allow_redirects=True)

        # This is very specific but w/e
        full_filename = sanitize_filename(cgi.parse_header(
            r.headers.get('Content-Disposition'))[1]['filename'])
        self.filename, ext = os.path.splitext(full_filename)

        self.download_location = os.path.join(directory, full_filename)

        if not os.path.isfile(self.download_location):
            r = self.session.get(url, allow_redirects=True)

            open(self.download_location, 'wb').write(r.content)

        if ext == '.zip':
            self.handle_zip()
        else:
            self.final_location = self.download_location

        print("Downloaded " + str(self.final_location))

    def handle_zip(self):
        self.final_location = os.path.splitext(self.download_location)[0]

        with zipfile.ZipFile(self.download_location, 'r') as zip_ref:
            zip_ref.extractall(self.final_location)
