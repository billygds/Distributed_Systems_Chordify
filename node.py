import hashlib
import socket
import threading
import json
import traceback
import time
import os
import sys
import signal
import random
import string

#Random string generator for value
def random_string_value(length=12):
    """Generate a random string of letters and digits with a max length of 12."""
    length = min(length, 12)  # Ensure max length is 12
    characters = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return ''.join(random.choices(characters, k=length))

class ChordNode:
    def __init__(self, ip, port, bootstrap_ip=None, bootstrap_port=None):
        self.ip = ip
        self.port = port
        self.node_id = self.generate_id(ip, port)
        self.data_store = {}  # DHT key-value store
        self.predecessor = None

        if bootstrap_ip and bootstrap_port:
            # This is a new node joining an existing network
            print(f"[NODE {self.node_id}] Attempting to join network via {bootstrap_ip}:{bootstrap_port}")
            self.join(bootstrap_ip, bootstrap_port)
        else:
            # This is the bootstrap node
            self.successor = {"node_id": self.node_id, "ip": self.ip, "port": self.port}
            print(f"[BOOTSTRAP NODE] Initialized with self-successor: {self.successor}")

        # Start the server
        server_thread = threading.Thread(target=self.start_server)
        server_thread.start()

        # Capture Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)

        print(f"[NODE {self.node_id}] Server running at {self.ip}:{self.port}. Press Ctrl+C to shut down.")
        while True:
            time.sleep(1)  # Keep the program alive

    
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
            server.close() #Κλείσιμο του socket


    def join(self, bootstrap_ip, bootstrap_port):
        """ Εισάγει τον κόμβο στον δακτύλιο Chord μέσω του bootstrap node """
        print(f"[NODE {self.node_id}] Attempting to join network via {bootstrap_ip}:{bootstrap_port}")

        try:
            # Συνδέεται στον bootstrap node για να βρει τους γειτονες του
            request = {"command": "find_neighbours", "node_id": self.node_id}
            print(f"[DEBUG] Sending request to bootstrap node: {request}")

            neighbours_response = self.send_request(bootstrap_ip, bootstrap_port, request)

            print(f"[DEBUG] Response from bootstrap: {neighbours_response}")

            if neighbours_response["status"] == "success":
                print(neighbours_response)
                self.successor = neighbours_response["successor"]
                print(f"[NODE {self.node_id}] Successor found: {self.successor}")

                # Ενημερώνουμε τον successor για το νέο predecessor
                update_predecessor_request = {
                    "command": "update_predecessor",
                    "node_id": self.node_id,
                    "ip": self.ip,
                    "port": self.port
                }
                print(f"[DEBUG] Sending update_predecessor request: {update_predecessor_request}")
                self.send_request(self.successor["ip"], self.successor["port"], update_predecessor_request)

                self.predecessor = neighbours_response["predecessor"]
                # Ενημερώνουμε τον predecessor μας (που είναι ο bootstrap) ότι έχει νέο successor
                update_successor_request = {
                    "command": "update_successor",
                    "node_id": self.node_id,
                    "ip": self.ip,
                    "port": self.port
                }
                print(f"[DEBUG] Sending update_successor request to predecessor: {update_successor_request}")
                update_response = self.send_request(self.predecessor['ip'], self.predecessor['port'], update_successor_request)
                print(f"[NODE {self.node_id}] Update successor response: {update_response}")


            else:
                print(f"[ERROR] Could not find successor: {neighbours_response['message']}")

        except Exception as e:
            print(f"[ERROR] Failed to join network: {e}")


    def find_neighbours(self, node_id):
        """Finds the correct successor for a joining node."""
        print(f"[DEBUG] find_successor() called for node_id: {node_id}")

        # If the current node is its own successor, return itself (Bootstrap case)
        if self.successor["node_id"] == self.node_id:
            print(f"[DEBUG] Returning bootstrap node as successor: {self.successor}")
            return {"status": "success", "successor": self.successor, "predecessor": self.successor}

        # If this node is the correct successor
        if self.node_id < node_id <= self.successor["node_id"]:
            print(f"[DEBUG] Returning successor: {self.successor}")
            return {"status": "success", "successor": self.successor, "predecessor": {'node_id':self.node_id,'ip':self.ip,'port':self.port}}

        # Handle wrap-around case: if this node has the highest ID, its successor is the smallest node
        if self.node_id > self.successor["node_id"]:
            if node_id > self.node_id or node_id <= self.successor["node_id"]:
                print(f"[DEBUG] Returning smallest node as successor: {self.successor}")
                return {"status": "success", "successor": self.successor, "predecessor": {'node_id':self.node_id,'ip':self.ip,'port':self.port}}

        # If this node is not the correct successor, forward the request
        print(f"[DEBUG] Forwarding find_successor request to {self.successor}")
        forward_request = {"command": "find_neighbours", "node_id": node_id}
        return self.send_request(self.successor["ip"], self.successor["port"], forward_request)


    def update_successor(self, node_id, ip, port):
        """ Ενημερώνει τον successor του κόμβου """
        self.successor = {"node_id": node_id, "ip": ip, "port": port}
        print(f"[NODE {self.node_id}] Successor updated: {self.successor}")
        return {"status": "success", "message": "Successor updated"}


    def update_predecessor(self, node_id, ip, port):
        """ Ορίζει τον νέο predecessor """
        self.predecessor = {"node_id": node_id, "ip": ip, "port": port}
        print(f"[NODE {self.node_id}] Predecessor updated: {self.predecessor}")
        return {"status": "success", "message": "Predecessor updated"}


    def send_request(self, ip, port, request):
        """ Στέλνει request σε άλλον κόμβο """
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((ip, port))
            client.send(json.dumps(request).encode())
            response = client.recv(1024).decode()
            client.close()
            return json.loads(response)
        except Exception as e:
            return {"status": "error", "message": str(e)}




    def handle_request(self, conn):
        """ Διαχειρίζεται εισερχόμενα αιτήματα από άλλους κόμβους """
        try:
            data = conn.recv(1024).decode()
            if data:
                request = json.loads(data)
                print(f"[DEBUG] Received request: {request}")  # Προσθέτουμε debugging
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
        node_id = request.get("node_id")

        if command == "insert":
            return self.insert(key, random_string_value())
        elif command == "query":
            if key !='*':
                return self.query(key)
            else:
                return self.query_all({})
        elif command == "query_all":
            return self.query_all(value)
        elif command == "delete":
            return self.delete(key)
        elif command == "depart":
            node_id = request.get("node_id") or request.get("value")  # Διαβάζουμε από value αν λείπει το node_id
            if node_id is None:
                return {"status": "error", "message": "Missing node_id in depart request"}   
            print(f"[DEBUG] Processing depart request for node {node_id}")
            return self.depart(node_id)
        elif command == "receive_data":
            return self.receive_data(request["data_store"])
        elif command == "find_successor":
            return self.find_successor(node_id)  # Call find_successor with node_id
        elif command == "find_predecessor":
            return self.find_predecessor(node_id)  # Call find_predecessor with node_id
        elif command == "find_neighbours":
            return self.find_neighbours(node_id)  # Call find_predecessor with node_id
        elif command == "update_successor":
            return self.update_successor(request["node_id"], request["ip"], request["port"])
        elif command == "update_predecessor":
            return self.update_predecessor(request["node_id"], request["ip"], request["port"])
        #elif command == "shutdown":
        #    return self.shutdown(conn)  # Περνάμε τη σύνδεση
        return {"status": "error", "message": f"Invalid command received: {command}"}

    def insert(self, key, value):
        """ Αποθηκεύει ένα τραγούδι στο DHT.Ακολουθεί δρομολόγηση Chord Ring """
        print('Starting Insert')
        hashed_key = int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**160)

        #If this is the case,we are on the correct node
        #Either this node is the first with ID >= key,or this is the one with the smallest ID
        if (self.predecessor['node_id'] < hashed_key and self.node_id >= hashed_key) or self.predecessor['node_id'] > self.node_id:
            if hashed_key in self.data_store:
                self.data_store[hashed_key] = self.data_store[hashed_key] + value
            else:
                self.data_store[hashed_key] = value
            return {"status": "success", "message": f"Inserted {key} -> {self.data_store[hashed_key]}"}
        
        #This is not the correct node,forward to predecessor
        elif self.predecessor['node_id'] >= hashed_key:
            print('Forwarding to predecessor:')
            print(self.predecessor)
            print('Hashed key:' + str(hashed_key))
            return self.send_request(self.predecessor['ip'],self.predecessor['port'],{
                'command': 'insert',
                'key': key,
                'value': value
            })
        
        #Forward to successor
        else:
            print('Forwarding to successor:')
            print(self.successor)
            print('Hashed key:' + str(hashed_key))
            return self.send_request(self.successor['ip'],self.successor['port'],{
                'command': 'insert',
                'key': key,
                'value': value
            })


    def query(self, key):
        """ Αναζητά ένα τραγούδι στο DHT """
        #If this is the case,we are on the correct node
        #Either this node is the first with ID >= key,or this is the one with the smallest ID
        if key != "*" :
            hashed_key = int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**160)
            if (self.predecessor['node_id'] < hashed_key and self.node_id >= hashed_key) or self.predecessor['node_id'] > self.node_id:
                    hashed_key = int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**160)
                    if hashed_key in self.data_store:
                        return {"status": "success", "value": self.data_store[hashed_key]}
                    return {"status": "error", "message": "Key not found"}
                
            #This is not the correct node,forward to predecessor
            elif self.predecessor['node_id'] >= hashed_key:
                print('Forwarding to predecessor:')
                print(self.predecessor)
                print('Hashed key:' + str(hashed_key))
                return self.send_request(self.predecessor['ip'],self.predecessor['port'],{
                    'command': 'query',
                    'key': key,
                })
            
            #Forward to successor
            else:
                print('Forwarding to successor:')
                print(self.successor)
                print('Hashed key:' + str(hashed_key))
                return self.send_request(self.successor['ip'],self.successor['port'],{
                    'command': 'query',
                    'key': key,
                })
        #else:
        #    return {"status":"success","value":list(self.data_store.values())}

    def query_all(self,nodes_info):
        """ Τυπώνει ολα τα δεδομενα των κομβων """
        #If this is the case,we are on the correct node
        #Either this node is the first with ID >= key,or this is the one with the smallest ID
        nodes_info[self.node_id] = list(self.data_store.values())

        if str(self.successor['node_id']) in nodes_info and nodes_info:
            print(f"[NODE {self.node_id}] Completed node info collection.")
            return {"status":"success","nodes_info":nodes_info}\
            
        print(f"[NODE {self.node_id}] Forwarding node info request to {self.successor}")
        return self.send_request(self.successor["ip"], self.successor["port"], {
            "command":"query_all",
            "value": nodes_info
        })
        #else:
        #    return {"status":"success","value":list(self.data_store.values())}

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

    def depart(self, node_id):
        """ Αποχώρηση συγκεκριμένου κόμβου από το Chord δίκτυο """
        node_id = int(node_id)
        if self.node_id == node_id:
            # Ο κόμβος που πρέπει να αποχωρήσει εκτελεί το depart
            print(f"[NODE {self.node_id}] Departing from network...")

            if self.successor and self.predecessor:
                # Ενημέρωση του predecessor να δείχνει στον successor
                notify_predecessor_request = {
                    "command": "update_successor",
                    "node_id": self.successor["node_id"],
                    "ip": self.successor["ip"],
                    "port": self.successor["port"]
                }
                self.send_request(self.predecessor["ip"], self.predecessor["port"], notify_predecessor_request)

                # Ενημέρωση του successor να δείχνει στον predecessor
                notify_successor_request = {
                    "command": "update_predecessor",
                    "node_id": self.predecessor["node_id"],
                    "ip": self.predecessor["ip"],
                    "port": self.predecessor["port"]
                }
                self.send_request(self.successor["ip"], self.successor["port"], notify_successor_request)

                # Μεταφορά των δεδομένων στον successor
                transfer_data_request = {
                    "command": "receive_data",
                    "data_store": self.data_store
                }
                self.send_request(self.successor["ip"], self.successor["port"], transfer_data_request)

            print(f"[NODE {self.node_id}] Successfully departed.")

            # Επιστρέφουμε απάντηση στο process_request() ΠΡΙΝ τερματίσουμε
            response = {"status": "success", "message": "Node successfully departed"}
            print(f"[DEBUG] Sending response before exiting: {response}")

            # Περιμένουμε λίγο για να προλάβει να σταλεί η απάντηση
            time.sleep(1)

            os._exit(0)  # Τερματισμός του κόμβου

        else:
            # Αν δεν είναι ο κόμβος που αποχωρεί, προωθεί το request στον successor
            print(f"[NODE {self.node_id}] Forwarding depart request for node {node_id} to successor {self.successor}")
            forward_request = {"command": "depart", "node_id": node_id}
            return self.send_request(self.successor["ip"], self.successor["port"], forward_request)

    
    def receive_data(self, data_store):
        """ Λαμβάνει τα δεδομένα του αποχωρούντος κόμβου """
        self.data_store.update(data_store)
        print(f"[NODE {self.node_id}] Received data from departing node.")
        return {"status": "success", "message": "Data received"}


# Εκκίνηση κόμβου
# Node startup logic
if __name__ == "__main__":
    if len(sys.argv) == 3:
        # This is the bootstrap node
        ip = sys.argv[1]
        port = int(sys.argv[2])
        node = ChordNode(ip, port)
    
    elif len(sys.argv) == 5:
        # This is a new node joining an existing network
        ip = sys.argv[1]
        port = int(sys.argv[2])
        bootstrap_ip = sys.argv[3]
        bootstrap_port = int(sys.argv[4])
        node = ChordNode(ip, port, bootstrap_ip, bootstrap_port)

    else:
        print("Usage:")
        print("  Bootstrap node: python node.py <ip> <port>")
        print("  Joining node:  python node.py <ip> <port> <bootstrap_ip> <bootstrap_port>")
        sys.exit(1)

