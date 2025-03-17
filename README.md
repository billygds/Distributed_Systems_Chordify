# Distributed_Systems_Chordify

Πρωτα τρεχουμε αυτό:

python node.py 127.0.0.1 5000

Υστερα:

Chordify Client - Available Commands:

        insert <key>        - Εισάγει ένα νέο (key, value) ζεύγος στον DHT.
        delete <key>           - Διαγράφει το (key, value) ζεύγος με κλειδί <key>.
        query <key>            - Αναζητά την τιμή του <key>. Αν <key> είναι '*', επιστρέφει όλα τα αποθηκευμένα δεδομένα.
        join <ip> <port> ( <replication factor> ) ( <bootstrap_ip> <bootstrap port> )     -Δημιουργεί ενα Chord Ring με τις δωσμένες πληροφορίες ή εισχωρεί έναν κόμβο
                                                                                        σε Chord Ring αν δωθεί η ip και port του bootstrap
        depart <node_id>       - Ο κόμβος με αναγνωριστικό <node_id> αποχωρεί από το δίκτυο.
        overlay               - Εμφανίζει την τρέχουσα τοπολογία του Chord δακτυλίου.
        help                  - Εμφανίζει αυτό το μήνυμα βοήθειας.

        Παράδειγμα χρήσης:
        python Chord_Client.py insert "song"
        python Chord_Client.py query "song"
        python Chord_Client.py delete "song"
        python Chord_Client.py join 127.0.0.1 5000 3 - Starts Chord Ring with replication factor 3
        python Chord_Client.py join 127.0.0.1 5001 127.0.0.1 5000 - Adds node to existing chord ring
        python Chord_Client.py depart "5604500"
        python Chord_Client.py overlay
        python Chord_Client.py help
