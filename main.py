import datetime
import time
import os
import mail_handler
from requests import exceptions
from patreon_parser import ParseSession
from download_handler import DownloadHandler
from post_manager import PostManager
from cloudscraper import CloudScraper
from dotenv import load_dotenv


load_dotenv()

post_manager_file = os.path.join(
    os.getenv("DIR"), os.getenv("POST_TRACKER_FILE"))

manager = PostManager(post_manager_file)
session = CloudScraper()
parse_session = ParseSession(session)


def main(days_back_max=7, days_back_range=7):

    post_urls = handle_mail(days_back_max, days_back_range)

    post_data = handle_posts(post_urls)

    handle_download(post_data)


def handle_mail(days_back_max, days_back_range):
    # By default grab 1 week of emails
    mails = mail_handler.get_emails(days_back_max, days_back_range)

    mail_details = []
    post_urls = set()

    url_list = []

    for mail in mails:
        mail_obj = mail_handler.process_email(mail)
        if not mail_obj:
            continue
        mail_details.append(mail_obj)

        url_list += mail_handler.get_post_urls(mail_obj)

        post_urls.update(set(url_list))

    return post_urls


def handle_posts(post_urls):

    post_data = []

    all_creators = set()

    for url in post_urls:
        count = 0
        done = False
        while count <= 10:
            count += 1
            try:
                data = parse_session.parse_patreon_url(url)

                if data is None:
                    done = True
                    break

                all_creators.add(data["author_short"])

                # It'll only have an ID if we did proper processing
                if "id" not in data:
                    done = True
                    break

                data["url"] = url

                if manager.should_update(data["id"], data["date"]):
                    post_data.append(data)
                else:
                    print("Skipping, already processed post " + data["title"])

                done = True
                break
            except exceptions.ConnectionError:
                print("Failed to connect to Patreon while parsing URL: " + url)
                print("Sleeping for %s seconds" % str((count + 1) * 10))
                time.sleep((count + 1) * 10)
                continue
            print("If you're here something went wrong")

        # Idk a better way to do this...
        if done:
            continue

        raise ConnectionError("Failed to connect to Patreon")

    permitted_creators = os.getenv('CREATORS').replace(" ", "").split(",")

    print("\nAll creator IDs found: " + ", ".join(all_creators))
    print("Not downloading these creators: " +
          ",".join([c for c in all_creators if c not in permitted_creators]))
    print("")
    
    return post_data


def handle_download(post_data):
    for post in post_data:
        print_data(post)
        for i in range(len(post["links"])):
            downloader = DownloadHandler(session)
            downloader.author = post["author"]
            downloader.post = post["title"]
            downloader.post_type = post["type"]
            if downloader.download_url(post["links"][i]):
                post["links"][i] = [post["links"][i], downloader.post_dir]
            else:
                post["links"][i] = [post["links"][i], "Failed"]

        manager.register_post(post["id"], post)
        manager.save_data()


def print_data(post):
    print("- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -")
    print(post["title"] + " by " + post["author"])
    print("Tags: " + ", ".join(post["tags"]))
    print("Posted on: " + post["date"])
    print("URL: " + post["url"])
    print("Type: " + post["type"])
    if(post["links"]):
        print("Files: ")
        for url in post["links"]:
            print("\t" + url)


if __name__ == "__main__":
    for i in range(48)[::-1]:
        d = (i + 1) * 30
        print(str(i + 1) + " months back, through: " + (datetime.date.today() -
                                                        datetime.timedelta(d)).strftime("%d-%b-%Y") + "--------------------------------")
        main(d, 30)
    # main(2,1)
