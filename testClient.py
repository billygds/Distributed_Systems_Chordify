import socket
import json
import sys
import signal
import os

def send_request(ip, port, command, key=None, value=None):
    """Στέλνει request στον server"""
    request = {"command": command}
    if key:
        request["key"] = key
    if value:
        request["value"] = value
    
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((ip, port))
        client.send(json.dumps(request).encode())
        response = client.recv(1024).decode()
        client.close()
        return json.loads(response)
    except Exception as e:
        return {"status": "error", "message": str(e)}

def signal_handler(sig, frame):
    print("\n[CLIENT] Received Ctrl+C. Exiting...")
    sys.exit(0)

# Capture Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python testClient.py <command> [<key>] [<value>]")
        print("Commands: insert <key> <value>, query <key>, delete <key>, shutdown, depart")
        sys.exit(1)

    ip = "127.0.0.1"
    port = 5000
    command = sys.argv[1]
    key = sys.argv[2] if len(sys.argv) > 2 else None
    value = sys.argv[3] if len(sys.argv) > 3 else None

    if command == "depart":
        if len(sys.argv) < 3:
            print("Usage: python testClient.py depart <node_id>")
            sys.exit(1)

        node_id = sys.argv[2]
        response = send_request(ip, port, "depart", value=node_id)


    if "status" in response and response["status"] == "success":
        print(response)
    else:
        print({"status": "error", "message": "Invalid response from server", "response": response})
