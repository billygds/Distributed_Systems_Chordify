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
    elif command == "insert":
        response = response = send_request(ip, port, command, key)
    elif command == "help":
        """Εκτυπώνει βοήθεια με τις διαθέσιμες εντολές"""
        help_text = """
        Chordify Client - Available Commands:

        insert <key>        - Εισάγει ένα νέο (key, value) ζεύγος στον DHT.
        delete <key>           - Διαγράφει το (key, value) ζεύγος με κλειδί <key>.
        query <key>            - Αναζητά την τιμή του <key>. Αν <key> είναι '*', επιστρέφει όλα τα αποθηκευμένα δεδομένα.
        join <ip> <port> ( <bootstra_ip> <bootstrap port> )     -Δημιουργεί ενα Chord Ring με τις δωσμένες πληροφορίες ή εισχωρεί έναν κόμβο
                                                                 σε Chord Ring αν δωθεί η ip και port του bootstrap
        depart <node_id>       - Ο κόμβος με αναγνωριστικό <node_id> αποχωρεί από το δίκτυο.
        overlay               - Εμφανίζει την τρέχουσα τοπολογία του Chord δακτυλίου.
        help                  - Εμφανίζει αυτό το μήνυμα βοήθειας.

        Παράδειγμα χρήσης:
        python Chord_Client.py insert "song"
        python Chord_Client.py query "song"
        python Chord_Client.py delete "song"
        python Chord_Client.py join 127.0.0.1 5000 - Starts Chord Ring
        python Chord_Client.py join 127.0.0.1 5001 127.0.0.1 5000 - Adds node to existing chord ring
        python Chord_Client.py depart "5604500"
        python Chord_Client.py overlay
        python Chord_Client.py help
        """
        print(help_text)
        sys.exit(0)
    else:
        response = send_request(ip, port, command, key, value)

    if "status" in response and response["status"] == "success":
        print(json.dumps(response,indent=4))
    else:
        print({"status": "error", "message": "Invalid response from server", "response": response})
