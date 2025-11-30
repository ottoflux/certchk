import requests
import sys
import json
import os

# CHANGE THIS URL to your actual Cloud URL after deployment
# For local testing, use: http://localhost:8080/check
API_URL = "https://certchk.vercel.app/check"

API_TOKEN = os.getenv("API_TOKEN", "123")

def main():
    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} <server_name_or_filename>')
        sys.exit(1)

    input_arg = sys.argv[1]
    servers = []

    # Try to read as file, fallback to single domain arg
    try:
        with open(input_arg, "r") as file:
            servers = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        servers = [input_arg]

    print(f"Checking {len(servers)} domains against API ({API_URL})...")

    try:
        # Send POST request to API
        headers = {
                    "Authorization": f"Bearer {API_TOKEN}",
                    "Content-Type": "application/json"
                }
        payload = {"domains": servers}
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            results = response.json()

            # Print pretty results
            print(f"{'DOMAIN':<30} | {'STATUS':<10} | {'DAYS LEFT':<10} | {'EXPIRY'}")
            print("-" * 75)

            for res in results:
                if res['status'] == 'ok':
                    days = res['days_left']
                    # Color code output if running in a terminal that supports it
                    status_color = ""
                    if days < 7: status_color = "CRITICAL: "
                    elif days < 30: status_color = "WARNING:  "

                    print(f"{res['server']:<30} | {res['status']:<10} | {days:<10} | {res['expiry_date']}")
                    if status_color:
                        print(f"  >>> {status_color}Expiring soon!")
                else:
                    print(f"{res['server']:<30} | {res['status']:<10} | {'-':<10} | {res['error_message']}")
        elif response.status_code == 401:
                     print("Error: Unauthorized. Please check your API_TOKEN.")
        elif response.status_code == 403:
                print("Error: Forbidden. Token accepted but permission denied.")
        else:
            print(f"API Error {response.status_code}: {response.text}")

    except requests.exceptions.ConnectionError:
        print("Could not connect to API. Is it running?")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
