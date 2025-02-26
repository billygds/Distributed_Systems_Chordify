import hashlib
import socket
import threading
import json

class ChordNode:
    def __init__(self, ip, port, bootstrap_ip=None, bootstrap_port=None):
        self.ip = ip
        self.port = port
        self.node_id = self.generate_id(ip, port)
        self.data_store = {}  # DHT key-value store
        self.predecessor = None
        self.successor = (ip, port)  # Αρχικά δείχνει τον εαυτό του

        # Αν υπάρχει bootstrap node, συνδέσου στο δίκτυο
        if bootstrap_ip and bootstrap_port:
            self.join_network(bootstrap_ip, bootstrap_port)

        # Εκκίνηση server για επικοινωνία με άλλους κόμβους
        threading.Thread(target=self.start_server, daemon=True).start()

    def generate_id(self, ip, port):
        """ Δημιουργεί μοναδικό ID με SHA-1(ip:port) """
        node_str = f"{ip}:{port}".encode()
        return int(hashlib.sha1(node_str).hexdigest(), 16) % (2**160)

    def start_server(self):
        """ Ξεκινάει έναν TCP server για επικοινωνία με άλλους κόμβους """
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.ip, self.port))
        server.listen(5)
        print(f"[NODE {self.node_id}] Listening on {self.ip}:{self.port}...")

        while True:
            conn, addr = server.accept()
            threading.Thread(target=self.handle_request, args=(conn,)).start()

    def handle_request(self, conn):
        """ Διαχειρίζεται εισερχόμενα αιτήματα από άλλους κόμβους """
        data = conn.recv(1024).decode()
        if data:
            request = json.loads(data)
            response = self.process_request(request)
            conn.send(json.dumps(response).encode())
        conn.close()

    def process_request(self, request):
        """ Διαχειρίζεται τα αιτήματα insert, query, delete """
        command = request.get("command")
        key = request.get("key")
        value = request.get("value")

        if command == "insert":
            return self.insert(key, value)
        elif command == "query":
            return self.query(key)
        elif command == "delete":
            return self.delete(key)
        return {"status": "error", "message": "Invalid command"}

    def insert(self, key, value):
        """ Αποθηκεύει ένα τραγούδι στο DHT """
        hashed_key = int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**160)
        self.data_store[hashed_key] = value
        return {"status": "success", "message": f"Inserted {key} -> {value}"}

    def query(self, key):
        """ Αναζητά ένα τραγούδι στο DHT """
        hashed_key = int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**160)
        if hashed_key in self.data_store:
            return {"status": "success", "value": self.data_store[hashed_key]}
        return {"status": "error", "message": "Key not found"}

    def delete(self, key):
        """ Διαγράφει ένα τραγούδι από το DHT """
        hashed_key = int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**160)
        if hashed_key in self.data_store:
            del self.data_store[hashed_key]
            return {"status": "success", "message": f"Deleted {key}"}
        return {"status": "error", "message": "Key not found"}

    def join_network(self, bootstrap_ip, bootstrap_port):
        """ Ενώνει τον κόμβο στο Chord δίκτυο """
        print(f"[NODE {self.node_id}] Joining network via {bootstrap_ip}:{bootstrap_port}")
        self.successor = (bootstrap_ip, bootstrap_port)  # Προσωρινά ορίζουμε ως successor τον bootstrap

# Εκκίνηση κόμβου
if __name__ == "__main__":
    node = ChordNode("127.0.0.1", 5000)
