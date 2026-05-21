"""REST API usage example."""
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"


def main():
    """Run REST API demonstration."""
    print("=" * 60)
    print("Asubarnipal - REST API Demo")
    print("=" * 60)

    # Health check
    print("\n[1] Health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("  [Error] API server not running. Start with: python -m api.main")
        return

    # Get wiki stats
    print("\n[2] Wiki statistics...")
    response = requests.get(f"{BASE_URL}/stats")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")

    # Get agent status
    print("\n[3] Agent status...")
    response = requests.get(f"{BASE_URL}/status")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")

    # List RSS feeds
    print("\n[4] RSS feeds...")
    response = requests.get(f"{BASE_URL}/feeds")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")

    # Get command history
    print("\n[5] Command history...")
    response = requests.get(f"{BASE_URL}/history")
    print(f"  Status: {response.status_code}")
    data = response.json()
    if isinstance(data, list):
        print(f"  Total commands: {len(data)}")
        for cmd in data[:5]:
            print(f"    - {cmd}")
    else:
        print(f"  Response: {data}")

    # Get logs
    print("\n[6] Recent logs...")
    response = requests.get(f"{BASE_URL}/logs")
    print(f"  Status: {response.status_code}")
    data = response.json()
    if isinstance(data, list):
        print(f"  Total logs: {len(data)}")
        for log in data[:3]:
            print(f"    - {log}")
    else:
        print(f"  Response: {data}")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("\nFor full API documentation, visit: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
