'''
Script to import RSS Feeds, then create a summary of the article 
from the feed and email that summary
'''
import os
import smtplib
from email.message import EmailMessage
import datetime
import feedparser
import requests
from bs4 import BeautifulSoup
import openai
from dotenv import load_dotenv
import pytz


def main():
    """
    Main function to read RSS feeds, summarize articles, and send emails
    with summaries.
    """

    # Open AI API key
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        print("Please set OPENAI_API_KEY in your .env file.")
        return
    
    rss_feed_url, rss_feed_summary_length = load_feeds_info()
    if rss_feed_url is None or rss_feed_summary_length is None:
        return

    feed = read_rss_feed(rss_feed_url)
    summary_length = get_summary_length(rss_feed_summary_length)

    for entry in feed:
        title = entry.title
        link = entry.link
        published = entry.published

        # Fetch the full article content
        response = requests.get(link, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        article_content = soup.get_text()

        # Generate summary using OpenAI ChatCompletion API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes articles.",
                },
                {
                    "role": "user",
                    "content": f"Summarize the following article:\n\n{article_content}",
                },
            ],
            max_tokens=summary_length,
            temperature=0.7,
        )

        generated_summary = response.choices[0].message.content.strip()
        # Add each summary to a complete_summary list
        if "complete_summary" not in locals():
            complete_summary = []
        complete_summary.append(
            {
                "title": title,
                "published": published,
                "link": link,
                "summary": generated_summary,
            }
        )

    # Send email with the summary
    send_email(complete_summary)


def send_email(complete_summary):
    '''
    Load email configuration from environment variables
    '''
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_sender = os.getenv("SENDER_EMAIL")
    recipient_email = os.getenv("RECIPIENT_EMAIL")

    if not all(
        [smtp_server, smtp_port, smtp_user, smtp_password, recipient_email, smtp_sender]
    ):
        print(
            "Please set SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_SENDER, SMTP_PASSWORD, and RECIPIENT_EMAIL in your .env file."
        )
        return

    body = ""
    for item in complete_summary:
        body += (
            f"<h2>{item['title']}</h2>\n"
            f"<h3>Published on: {item['published']}</h3>\n"
            f"<h3>Summary:</h3>\n{item['summary']}<p>&nbsp;</p>\n"
            f"<a href=\"{item['link']}\">Read more</a><p>&nbsp;</p>\n\n"
            f"=========================================================\n"
        )

    # Create the email content
    subject = f"Summary of Tweaker RSS Feed Articles"

    # Compose the email message
    msg = EmailMessage()
    msg.set_content(body, subtype="html")
    msg["Subject"] = subject
    msg["From"] = smtp_sender
    msg["To"] = recipient_email

    # Send the email
    with smtplib.SMTP_SSL(smtp_server, int(smtp_port)) as server:
        # server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        # server.sendmail(smtp_user, recipient_email, message)


def load_feeds_info():
    '''
    Load RSS feed URL and summary length from environment variables
    '''
    load_dotenv()
    rss_feed_url = os.getenv("RSS_FEED_URL")
    rss_feed_summary_length = os.getenv("RSS_FEED_SUMMARY_LENGTH")

    if not rss_feed_url or not rss_feed_summary_length:
        print("Please set RSS_FEED_URL and RSS_FEED_SUMMARY_LENGTH in your .env file.")
        return None, None

    return rss_feed_url, rss_feed_summary_length


def read_rss_feed(url):
    '''
    Read the RSS feed from the given URL and filter entries published yesterday (Amsterdam time).
    '''
    feed = feedparser.parse(url)
    amsterdam_tz = pytz.timezone("Europe/Amsterdam")
    now_ams = datetime.datetime.now(amsterdam_tz)
    yesterday_ams = (now_ams - datetime.timedelta(days=1)).date()

    filtered_entries = []
    for entry in feed.entries:
        # Try to parse the published date
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published_dt_utc = datetime.datetime(*entry.published_parsed[:6], tzinfo=pytz.utc)
            published_dt_ams = published_dt_utc.astimezone(amsterdam_tz)
            published_date_ams = published_dt_ams.date()
            if published_date_ams == yesterday_ams and entry.tags[0].term != 'Software':
                filtered_entries.append(entry)
    feed.entries = filtered_entries
    return feed.entries

def get_summary_length(rss_feed_summary_length)
    '''
    Determine summary length based on user input
    '''
    if rss_feed_summary_length == "Short":
        return 500
    elif rss_feed_summary_length == "Medium":
        return 1000
    elif rss_feed_summary_length == "Long":
        return 1500
    else:
        print(
            "Invalid summary length. Please set RSS_FEED_SUMMARY_LENGTH to Short, Medium, or Long in your .env file."
        )
        return 1000
        
if __name__ == "__main__":
    main()
