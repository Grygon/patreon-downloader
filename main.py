import datetime
import time
import os
import mail_handler
from requests import exceptions, Session
from patreon_parser import ParseSession, CaptchaError
from download_handler import DownloadHandler
from post_manager import PostManager
from cloudscraper import CloudScraper, create_scraper
from dotenv import load_dotenv
from pathvalidate import sanitize_filename


load_dotenv()

post_manager_file = os.path.join(
    os.getenv("DIR"), os.getenv("POST_TRACKER_FILE"))

error_manager_file = os.path.join(
    os.getenv("DIR"), os.getenv("ERROR_TRACKER_FILE"))


class ScrapeSession():

    def __init__(self):
        self.manager = PostManager(post_manager_file)
        self.error_manager = PostManager(error_manager_file)
        self.scraper = create_scraper()  
        self.parse_session: ParseSession
        


    def main(self, days_back_max=7, days_back_range=8):
        if os.getenv("PROXY_URL"):
            proxy_str = ('socks5://%s:%s@%s:%s' % (os.getenv("PROXY_USER"),os.getenv("PROXY_PASS"),os.getenv("PROXY_URL"),os.getenv("PROXY_PORT")))
            self.scraper.proxies.update({'http':proxy_str,'https':proxy_str})

        post_urls = self.handle_mail(days_back_max, days_back_range)
        
        self.parse_session = ParseSession(self.scraper)

        post_data = self.handle_posts(post_urls)

        self.handle_download(post_data)


    def handle_mail(self, days_back_max, days_back_range):
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


    def handle_posts(self, post_urls):

        post_data = []

        all_creators = set()

        for url in post_urls:
            count = 0
            done = False
            while count <= 10:
                count += 1
                try:
                    data = self.parse_session.parse_patreon_url(url)

                    if data is None:
                        done = True
                        break

                    all_creators.add(data["author_short"])

                    # It'll only have an ID if we did proper processing
                    if "id" not in data:
                        done = True
                        break

                    data["url"] = url

                    if self.manager.should_update(data["id"], data["date"]):
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


    def handle_download(self, post_data):
        for post in post_data:
            try:
                print_data(post)
                
                downloader = None
                
                for i in range(len(post["links"])):
                    downloader = DownloadHandler(session)
                    downloader.author = post["author"]
                    downloader.post = post["title"]
                    downloader.post_type = post["type"]
                    if downloader.download_url(post["links"][i]):
                        post["links"][i] = [post["links"][i], downloader.post_dir]
                    else:
                        post["links"][i] = [post["links"][i], "Failed"]

                if not (downloader is None):
                    create_shortcut({
                        'url': post['url'], 
                        'folder': downloader.post_dir,
                        'post': sanitize_filename(post['title'])
                        })

                self.manager.register_post(post["id"], post)
                self.manager.save_data()
            except Exception as e:
                self.error_manager.register_post(post["id"], post)
                self.error_manager.save_data()
                print(e)
                print("Post processing failed! Continuing to process posts...")
                print("Post: " + post["title"])
                print("Dump: " + str(post))


    def print_data(self, post):
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
                
    def create_shortcut(self, data):    
        content = ('''
        <html>
        <head>
        <meta http-equiv="refresh" content="0; url=%s" />
        </head>
        <body>
        </body>
        </html>
        ''' % data['url'])
        
        with open(os.path.join(data['folder'], data["post"] + '.html'), 'w') as f:
            f.write(content)


if __name__ == "__main__":
    
    captcha_retry_count = 0

    while True:
        try:
            session = ScrapeSession()
            session.main(1,30)
            break

        except CaptchaError as e:
            if captcha_retry_count >= int(os.getenv("CAPTCHA_RETRY_COUNT")):
                raise e
                break
            captcha_retry_count = captcha_retry_count + 1
            sleep_time = captcha_retry_count * 5

            print("Hit a CAPTCHA, sleeping for %s seconds and retrying" % sleep_time)
            time.sleep(sleep_time)

    # For processing backlog
    #for i in range(48)[::-1]:
    #    d = (i + 1) * 30
    #    print(str(i + 1) + " months back, through: " + (datetime.date.today() -
    #                                                    datetime.timedelta(d)).strftime("%d-%b-%Y") + "--------------------------------")
    #    main(d, 30)
