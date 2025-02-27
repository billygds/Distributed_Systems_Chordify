import hashlib
import socket
import threading
import json
import traceback
import time
import os
import sys
import signal

from numpy import conj

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

        # Εκκίνηση server
        server_thread = threading.Thread(target=self.start_server)
        server_thread.start()
        #server_thread.join() #Το κύριο νήμα δεν τερματίζει αν δεν τελειώσει ο σερβερ

        # Διαχείρηση Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler) # Capture Ctrl+C

        print("[NODE] Server running. Press Ctrl+C to shut down.")
        while True:
            time.sleep(1)  # Κρατάει το πρόγραμμα ανοιχτό χωρίς να μπλοκάρει το Ctrl+C
    
    def signal_handler(self, sig, frame):
        print("\n[NODE] Received Ctrl+C. Shutting down...")
        os._exit(0)
        

    def generate_id(self, ip, port):
        """ Δημιουργεί μοναδικό ID με SHA-1(ip:port) """
        node_str = f"{ip}:{port}".encode()
        return int(hashlib.sha1(node_str).hexdigest(), 16) % (2**160)

    def start_server(self):
        """ Ξεκινάει έναν TCP server για επικοινωνία με άλλους κόμβους """
        try:
            print(f"[DEBUG] Trying to start server on {self.ip}:{self.port}")  # Debugging
            print("[DEBUG] Creating socket...")
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            print("[DEBUG] Setting socket options...")
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            print(f"[DEBUG] Binding server to {self.ip}:{self.port}...")
            server.bind((self.ip, self.port))

            print("[DEBUG] Server is now listening...")
            server.listen(5)
            print(f"[NODE {self.node_id}] Listening on {self.ip}:{self.port}...")  # Αν εμφανιστεί, ο server τρέχει

            while True:
                conn, addr = server.accept()
                print(f"[NODE {self.node_id}] Connection from {addr}")  # Δείχνει αν υπάρχει εισερχόμενη σύνδεση
                threading.Thread(target=self.handle_request, args=(conn,)).start()
        except Exception as e:
            print(f"[ERROR] Server failed to start: {e}")
            traceback.print_exc()
        finally:
            server.close() #Σωστό κλείσιμο του socket


    def handle_request(self, conn):
        """ Διαχειρίζεται εισερχόμενα αιτήματα από άλλους κόμβους """
        try:
            data = conn.recv(1024).decode()
            if data:
                request = json.loads(data)
                response = self.process_request(request)
                conn.send(json.dumps(response).encode())
        except Exception as e:
            print(f"[ERROR] Request handling failed: {e}")
        finally:
            conn.close()

    def process_request(self, request):
        """ Διαχειρίζεται τα αιτήματα insert, query, delete, shutdown """
        command = request.get("command")
        key = request.get("key")
        value = request.get("value")

        if command == "insert":
            return self.insert(key, value)
        elif command == "query":
            return self.query(key)
        elif command == "delete":
            return self.delete(key)
        #elif command == "shutdown":
        #    return self.shutdown(conn)  # Περνάμε τη σύνδεση
        return {"status": "error", "message": f"Invalid command received: {command}"}

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

    #def shutdown(self, conn):
        """Τερματίζει τον server σωστά χωρίς να κλείνει απότομα τις συνδέσεις"""
        print("[NODE] Shutting down...")

        response = {"status": "success", "message": "Server shutting down"}
        
        try:
            conn.send(json.dumps(response).encode())  # Στέλνει απάντηση πριν το exit
            time.sleep(1)  # Δίνει χρόνο στον client να λάβει την απάντηση
        except Exception as e:
            print(f"[ERROR] Could not send shutdown response: {e}")

        os._exit(0)  # Τερματίζει το πρόγραμμα

    def join_network(self, bootstrap_ip, bootstrap_port):
        """ Ενώνει τον κόμβο στο Chord δίκτυο """
        print(f"[NODE {self.node_id}] Joining network via {bootstrap_ip}:{bootstrap_port}")
        self.successor = (bootstrap_ip, bootstrap_port)  # Προσωρινά ορίζουμε ως successor τον bootstrap

# Εκκίνηση κόμβου
if __name__ == "__main__":
    node = ChordNode("127.0.0.1", 5000)
