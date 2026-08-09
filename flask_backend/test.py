from discourse_api import get_topics

data = get_topics()

print(data.keys())

topics = data["topic_list"]["topics"]

print("\nLatest Topics:\n")

for topic in topics[:5]:
    print(topic["title"])