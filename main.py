import re
import mail_handler

def main():
    mails = mail_handler.get_emails('SENTSINCE 01-Dec-2020')
    mail_details = []
    post_urls = {''}
    
    for mail in mails:
        mail_obj = mail_handler.process_email(mail)
        mail_details.append(mail_obj)
        
        regex = r"https:\/\/www\.patreon\.com\/posts.*?(?=[\?\"\<])"
        
        url_list = re.findall(regex,mail_obj["Text"])
        
        post_urls.update(set(url_list))
        
    print("\n".join(post_urls))

if __name__ == "__main__":
    main()