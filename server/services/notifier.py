import os
import secrets
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOPIC_FILE = os.path.join(BASE_DIR, 'data', 'ntfy_topic.txt')


def get_topic():
    """Private ntfy topic.

    ntfy.sh topics are public: anyone who knows the name can read them.
    So the topic is a long random string, generated once and stored in
    data/ntfy_topic.txt (git-ignored). NTFY_TOPIC env var overrides it.
    """
    env_topic = os.environ.get('NTFY_TOPIC')
    if env_topic:
        return env_topic
    if os.path.exists(TOPIC_FILE):
        with open(TOPIC_FILE) as f:
            topic = f.read().strip()
        if topic:
            return topic
    topic = 'radar_' + secrets.token_urlsafe(18)
    os.makedirs(os.path.dirname(TOPIC_FILE), exist_ok=True)
    with open(TOPIC_FILE, 'w') as f:
        f.write(topic)
    return topic


def send_push(title: str, message: str, priority: str = "default", tags: list = None, click_url: str = None):
    """
    Send push notification to phone via ntfy.

    Priority levels:
      - 'min' / 'low'
      - 'default'
      - 'high' / 'urgent' (rings loud, vibrates)
    """
    headers = {
        "Title": title.encode('utf-8'),
        "Priority": str(priority),
    }

    if tags:
        headers["Tags"] = ",".join(tags)

    if click_url:
        headers["Click"] = click_url

    try:
        response = requests.post(
            f"https://ntfy.sh/{get_topic()}",
            data=message.encode('utf-8'),
            headers=headers,
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send notification: {e}")
        return False


# The radar calls notify(); keep it as an alias of send_push.
notify = send_push


if __name__ == "__main__":
    print(f"Testing push notification to ntfy topic: {get_topic()}")
    success = send_push(
        title="Radar Online",
        message="Push notifications are working!",
        priority="high",
        tags=["rocket"]
    )
    print("Sent!" if success else "Failed!")
