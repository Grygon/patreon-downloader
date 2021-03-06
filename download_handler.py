import zipfile
import re
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
    post_type: str

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
        self.url = re.sub(r'\?dl\=0', '?dl=1', self.url)

    def general_process(self):
        r = self.session.head(self.url, allow_redirects=True)

        if not r.ok:
            return False

        # This is very specific but w/e. IF it fails, we aren't downloading a file
        try:
            full_filename = sanitize_filename(cgi.parse_header(
                r.headers.get('Content-Disposition'))[1]['filename'])
        except KeyError:
            return False
        self.filename, ext = os.path.splitext(full_filename)

        self.post_dir = os.path.join(directory, sanitize_filename(type_to_dir(
            self.post_type)), sanitize_filename(self.author), sanitize_filename(self.post))

        self.download_location = os.path.join(self.post_dir, full_filename)

        if not os.path.exists(self.post_dir):
            os.makedirs(self.post_dir)

        if not os.path.isfile(self.download_location):
            self.download_file(self.url, self.download_location)

        if ext == '.zip':
            try:
                self.handle_zip()
            except zipfile.BadZipFile:
                print("ZIP was malformed, attempting re-download...")
                self.download_file(self.url, self.download_location)
                self.handle_zip()
                
            self.final_location = self.post_dir
        else:
            self.final_location = self.download_location

        print("Downloaded " + str(self.filename))

        return True

    def handle_zip(self):
        with zipfile.ZipFile(self.download_location, 'r') as zip_ref:
            zip_ref.extractall(self.post_dir)
        os.remove(self.download_location)
            
    def download_file(self, url, save_path, chunk_size=128):
        r = self.session.get(url, stream=True, allow_redirects=True)
        with open(save_path, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=chunk_size):
                fd.write(chunk)

def type_to_dir(t):
    d = {
        "token": "Tokens",
        "map": "Maps",
        "asset": "Assets",
        "dungeondraft": "DungeonDraft"
    }

    if t in d:
        return d[t]
    else:
        return "Unsorted"
