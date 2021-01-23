import re
import mail_handler
from patreon_parser import ParseSession
from download_handler import DownloadHandler
from post_manager import PostManager
import requests
import datetime
from cloudscraper import CloudScraper
from dotenv import load_dotenv
import os


load_dotenv()


def main():
    # By default grab 1 week of emails
    date_1wk = 'SENTSINCE ' + (datetime.date.today() - datetime.timedelta(7)).strftime("%d-%b-%Y")
    custom_datestring = 'SENTON 17-Jan-2021'
    mails = mail_handler.get_emails(custom_datestring)
    
    post_manager_file = os.path.join(os.getenv("DIR"), os.getenv("POST_TRACKER_FILE"))
    
    manager = PostManager(post_manager_file)
    
    mail_details = []
    post_urls = set()
    
    for mail in mails:
        mail_obj = mail_handler.process_email(mail)
        mail_details.append(mail_obj)
        
        link_regex = r"https:\/\/www\.patreon\.com\/posts.*?(?=[\?\"\<\'])"
        
        url_list = re.findall(link_regex, mail_obj["Text"])
        
        post_urls.update(set(url_list))
        
    post_data = []
    
    
    
    session = CloudScraper()
    parse_session = ParseSession(session)
    
    for url in post_urls:
        data = parse_session.parse_patreon_url(url)
        data["url"] = url
        
        if manager.should_update(data["id"], data["date"]):        
            post_data.append(data)
        
    for post in post_data:
        print_data(post)
        for url in post["links"]:
            downloader = DownloadHandler(session)
            downloader.author = post["author"]
            downloader.post = post["title"]
            downloader.download_url(url)
        
        manager.register_post(post["id"], post["date"])
        
    

def print_data(post):
    print(post["title"] + " by " + post["author"])
    print("Tags: " + ", ".join(post["tags"]))
    print("Posted on: " + post["date"])
    print("URL: " + post["url"])
    if(post["links"]):
        print("Files: ")
        for url in post["links"]:
            print("\t" + url)
    

if __name__ == "__main__":
    main()
