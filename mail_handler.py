import datetime
import os
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from imap_tools import MailBox, AND

load_dotenv()

cwd = os.getcwd()
EMAIL_UN = os.getenv('APP_EMAIL')
EMAIL_PW = os.getenv('APP_PWD')


def get_emails(days_back_max, days_back_range):
    date_max = datetime.date.today() - datetime.timedelta(days_back_max)
    date_min = datetime.date.today() - datetime.timedelta(days_back_max - days_back_range)

    with MailBox('imap.gmail.com').login(EMAIL_UN, EMAIL_PW) as mailbox:
        mails = [m for m in mailbox.fetch(
            AND(from_="bingo@patreon.com", sent_date_lt=date_min, sent_date_gte=date_max))]

    return mails


def process_email(mail):

    # We don't need the receipt
    if re.match(pattern=r"(Your Patreon receipt is here!|Congrats, you\'re now a patron of|Here\'s your confirmation for)", string=mail.subject):
        return

    res = {
        'From': mail.from_,
        'From name': mail.from_values["name"],
        'To': mail.to,
        'Subject': mail.subject,
        'Text': mail.text,
        'HTML': mail.html,
        'File': None
    }
    print("["+res["From"]+"] :" + res["Subject"])

    return res


def get_post_urls(mail):
    try:
        # Ideally we find the singular URL from our View on Patreon button
        soup = BeautifulSoup(mail["HTML"], "html.parser")
        URL = soup.find(string=re.compile(
            r"(View\sall\s\d*\simages\son\sPatreon|(View|Listen)\son\sPatreon|Vote\snow|Watch\snow)")).find_parent("a")['href']
        return [URL]
    except AttributeError:
        # Drop here if that button can't be found
        # Now we just grab what we can
        # This isn't ideal, since we pick up on all URLs, including potentially email settings etc for the mailgun links
        all_links = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        specific_links = r"(patreon\.com\/posts|email\.mailgun\.patreon\.com\/c\/)"

        all_url_list = re.findall(all_links, mail["HTML"])

        url_list = [l[0] for l in all_url_list if re.search(
            string=l[0], pattern=specific_links)]

        return url_list


if __name__ == "__main__":
    pass
