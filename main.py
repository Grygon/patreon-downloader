import re
import mail_handler
import patreon_parser
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
    
    
    session = patreon_parser.ParseSession(CloudScraper())
    
    for url in post_urls:
        data = session.parse_patreon_url(url)
        data["url"] = url
        
        post_data.append(data)
        
    for post in post_data:
        print(post["url"] + "\n")
        for url in post["links"]:
            print("\t" + url + "\n")


if __name__ == "__main__":
    main()
