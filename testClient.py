import socket
import json
import sys

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python testClient.py <command> <key> [<value>]")
        print("Commands: insert <key> <value>, query <key>, delete <key>, shutdown")
        sys.exit(1)

    ip = "127.0.0.1"
    port = 5000
    command = sys.argv[1]
    key = sys.argv[2] if len(sys.argv) > 2 else None
    value = sys.argv[3] if len(sys.argv) > 3 else None

    response = send_request(ip, port, command, key, value)
    print(response)


# Οδηγίες Χρήσης ;)

# python testClient.py insert song.mp3 192.168.1.2
# python testClient.py query song.mp3
# python testClient.py delete song.mp3
# python testClient.py shutdown
