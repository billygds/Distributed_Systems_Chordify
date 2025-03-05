import hashlib
import threading
import time


class Chord:
    def __init__(self, node):
        """
        Initializes the Chord DHT for a given node.
        - The `node` parameter is a reference to the ChordNode instance from node.py.
        """
        stabilize_thread = threading.Thread(target=self.stabilize, daemon=True)
        stabilize_thread.start()
        self.node = node  # Link Chord functionality to the node instance
        self.data_store = {}  # Stores key-value pairs

    def hash_key(self, key):
        """ Generates a consistent hash for the key using SHA-1. """
        return int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**160)

    def store_data(self, key, value):
        """ Stores a key-value pair in the correct node. """
        hashed_key = self.hash_key(key)

        if self.is_responsible(hashed_key):
            self.data_store[hashed_key] = value
            return {"status": "success", "message": f"Stored {key} -> {value}"}
        else:
            # Forward request to the correct node
            successor = self.node.successor
            response = self.node.send_request(successor["ip"], successor["port"], {
                "command": "insert",
                "key": key,
                "value": value
            })
            return response

    def lookup_data(self, key):
        """ Finds and returns the value for a given key in the DHT. """
        hashed_key = self.hash_key(key)

        if self.is_responsible(hashed_key):
            if hashed_key in self.data_store:
                return {"status": "success", "value": self.data_store[hashed_key]}
            return {"status": "error", "message": "Key not found"}
        else:
            # Forward request to the correct node
            successor = self.node.successor
            response = self.node.send_request(successor["ip"], successor["port"], {
                "command": "query",
                "key": key
            })
            return response

    def delete_data(self, key):
        """ Deletes a key-value pair from the DHT. """
        hashed_key = self.hash_key(key)

        if self.is_responsible(hashed_key):
            if hashed_key in self.data_store:
                del self.data_store[hashed_key]
                return {"status": "success", "message": f"Deleted {key}"}
            return {"status": "error", "message": "Key not found"}
        else:
            # Forward request to the correct node
            successor = self.node.successor
            response = self.node.send_request(successor["ip"], successor["port"], {
                "command": "delete",
                "key": key
            })
            return response

    def is_responsible(self, key_hash):
        """ Checks if this node is responsible for a given key. """
        return self.node.predecessor is None or (self.node.predecessor["node_id"] < key_hash <= self.node.node_id)
    
    def stabilize(self):
        """ Periodically checks and updates successor information """
        while True:
            try:
                if self.node.successor:
                    check_request = {"command": "get_predecessor"}
                    response = self.node.send_request(self.node.successor["ip"], self.node.successor["port"], check_request)

                    if response["status"] == "success" and response["predecessor"]:
                        pred_id = response["predecessor"]["node_id"]
                        if self.node.node_id < pred_id < self.node.successor["node_id"]:
                            print(f"[STABILIZE] Updating successor from {self.node.successor['node_id']} to {pred_id}")
                            self.node.successor = response["predecessor"]

                    # Notify the successor about this node
                    notify_request = {
                        "command": "notify",
                        "node_id": self.node.node_id,
                        "ip": self.node.ip,
                        "port": self.node.port
                    }
                    self.node.send_request(self.node.successor["ip"], self.node.successor["port"], notify_request)

            except Exception as e:
                print(f"[ERROR] Stabilization failed: {e}")

            time.sleep(5)  # Run stabilization every 5 seconds
