import requests
import json

NTFY_TOPIC = "Brain_x1"  # Custom private topic
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

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
        "Priority": priority,
    }
    
    if tags:
        headers["Tags"] = ",".join(tags)
        
    if click_url:
        headers["Click"] = click_url
        
    try:
        response = requests.post(
            NTFY_URL,
            data=message.encode('utf-8'),
            headers=headers,
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        print(f"⚠️ Failed to send notification: {e}")
        return False

if __name__ == "__main__":
    print("Testing push notification to ntfy...")
    success = send_push(
        title="🧠 PocketBrain Online",
        message="Your Mobistar C2 push notification system is working!",
        priority="high",
        tags=["rocket", "brain"]
    )
    print("Sent!" if success else "Failed!")
