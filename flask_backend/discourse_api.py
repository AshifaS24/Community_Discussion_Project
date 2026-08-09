import requests
from bs4 import BeautifulSoup


DISCOURSE_URL = "https://kcommunity.discourse.group"


def clean_html(html_content):

    soup = BeautifulSoup(html_content, "html.parser")

    return soup.get_text(" ", strip=True)


def get_latest_topics():

    url = f"{DISCOURSE_URL}/latest.json"

    response = requests.get(url, timeout=30)

    response.raise_for_status()

    data = response.json()

    topics = data["topic_list"]["topics"]

    return topics


# Backward-compatible alias (your existing /discourse_topics route uses this name)
def get_topics():

    url = f"{DISCOURSE_URL}/latest.json"

    response = requests.get(url, timeout=30)

    response.raise_for_status()

    return response.json()


def get_topic_discussion(topic_id):

    url = f"{DISCOURSE_URL}/t/{topic_id}.json"

    response = requests.get(url, timeout=30)

    response.raise_for_status()

    data = response.json()

    title = data["title"]
    created_at = data["created_at"]
    slug = data.get("slug", "")
    views = data.get("views", 0)
    posts_count = data.get("posts_count", 0)

    posts = data["post_stream"]["posts"]

    comments = []

    for post in posts:

        cleaned_text = clean_html(post["cooked"])

        comments.append({
            "username": post["username"],
            "text": cleaned_text,
            "date": post["created_at"],
            "is_op": post.get("post_number") == 1
        })

    return {
        "id": topic_id,
        "title": title,
        "created_at": created_at,
        "url": f"{DISCOURSE_URL}/t/{slug}/{topic_id}",
        "views": views,
        "replies": max(posts_count - 1, 0),
        "comments": comments
    }


if __name__ == "__main__":

    topics = get_latest_topics()

    print("\nTOTAL TOPICS FETCHED:", len(topics))

    for topic in topics:

        print("\n" + "=" * 70)

        print("TOPIC ID:", topic["id"])
        print("TOPIC NAME:", topic["title"])
        print("CREATED DATE:", topic["created_at"])

        discussion = get_topic_discussion(topic["id"])

        print("\nDISCUSSION CONTENT:\n")

        for comment in discussion["comments"]:

            print("USER:", comment["username"])
            print("COMMENT:", comment["text"])
            print("-" * 50)