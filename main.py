import re
import mail_handler
from patreon_parser import ParseSession
from download_handler import DownloadHandler
import requests
from cloudscraper import CloudScraper


def main():
    mails = mail_handler.get_emails('SENTON 11-Jan-2021')
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
        
        post_data.append(data)
        
    for post in post_data:
        print_data(post)
        for url in post["links"]:
            downloader = DownloadHandler(session)
            downloader.download_url(url)
        
    

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
