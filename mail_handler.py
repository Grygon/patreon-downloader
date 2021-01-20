import pandas as pd
import datetime
import os
import glob
import email
import imaplib
from dotenv import load_dotenv
from html.parser import HTMLParser
from bs4 import BeautifulSoup

load_dotenv()

cwd = os.getcwd()
EMAIL_UN = os.getenv('APP_EMAIL')
EMAIL_PW = os.getenv('APP_PWD')


def get_emails(search):
    un = EMAIL_UN
    pw = EMAIL_PW
    url = 'imap.gmail.com'
    detach_dir = '.'  # directory where to save attachments (default: current)
    # connecting to the gmail imap server
    m = imaplib.IMAP4_SSL(url)
    m.login(un, pw)
    m.select('Patreon')

    resp, items = m.search(None, search)
    # you could filter using the IMAP rules here (check http://www.example-code.com/csharp/imap-search-critera.asp)

    items = items[0].split()  # getting the mails id

    mails = []

    for emailid in items:
        # fetching the mail, "`(RFC822)`" means "get the whole stuff", but you can ask for headers only, etc
        resp, data = m.fetch(emailid, "(RFC822)")
        # parsing the mail content to get a mail object
        mail = email.message_from_bytes(data[0][1])

        mails.append(mail)

    return mails


def process_email(mail):
    subj = email.header.decode_header(mail["Subject"])[0][0]
    if type(subj) is not str:
        subj = subj.decode('utf-8')

    text = ""
    if mail.is_multipart():
        # iterate over email parts
        for part in mail.walk():
            # extract content type of email
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            try:
                # get the email body
                body = part.get_payload(decode=True).decode()
            except:
                pass
            if content_type == "text/plain" and "attachment" not in content_disposition:
                # print text/plain emails and skip attachments
                text += body
    else:
        # extract content type of email
        content_type = mail.get_content_type()
        # get the email body
        body = mail.get_payload(decode=True).decode()
        if content_type == "text/plain":
            # print only text email parts
            text += body

    res = {
        'From': email.utils.parseaddr(mail['From'])[1],
        'From name': email.utils.parseaddr(mail['From'])[0],
        'To': mail['To'],
        'Subject': subj,
        'Text': text,
        'File': None
    }
    print("["+res["From"]+"] :" + res["Subject"])

    return res

if __name__ == "__main__":
    pass
