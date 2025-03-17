#!/bin/bash

#--------Usage---------
#chmod +x requestExperiment.sh
#./requestExperiment.sh

# Configuration
IP="127.0.0.1"
BASE_PORT=5000
NODE_COUNT=10
REQUEST_PATH="./data/requests"
k=3  # Fixed k value
CONSISTENCIES=("linearizability" "eventual")
LOG_DIR="./logs/request_logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to start nodes
start_nodes() {
    echo "Starting bootstrap node..." | tee -a "$LOG_DIR/requestLog_0.txt"
    bash -c "python3 node.py $IP $BASE_PORT $k | tee $LOG_DIR/requestLog_0.txt &" &
    sleep 2
    
    for ((i=1; i<$NODE_COUNT; i++)); do
        port=$((BASE_PORT + i))
        echo "Starting node $i on port $port..." | tee -a "$LOG_DIR/requestLog_${i}.txt"
        bash -c "python3 node.py $IP $port $IP $BASE_PORT | tee $LOG_DIR/requestLog_${i}.txt &" &
        sleep 2
    done
    
    # Wait for all nodes to be fully initialized
    echo "Waiting for all nodes to be fully initialized..."
    for ((i=0; i<$NODE_COUNT; i++)); do
        port=$((BASE_PORT + i))
        while ! nc -z 127.0.0.1 $port; do sleep 1; done
        echo "Node on port $port is now active."
    done
}

# Function to execute requests on correct nodes
execute_requests() {
    local consistency=$1
    
    echo "Running requests with k=$k and consistency=$consistency" | tee -a "$LOG_DIR/requestResults.csv"
    start_time=$(date +%s.%N)
    
    for ((i=0; i<$NODE_COUNT; i++)); do
        port=$((BASE_PORT + i))
        file="$REQUEST_PATH/requests_0${i}.txt"
        echo "Executing requests from $file on node $i (port $port)..." | tee -a "$LOG_DIR/requestLog_${i}.txt"

        while IFS= read -r line; do
            request_type=$(echo "$line" | awk '{print $1}')
            args=$(echo "$line" | cut -d' ' -f2-)
            
            if [ "$request_type" == "insert" ]; then
                echo "Inserting: $args on node $i (port $port)" | tee -a "$LOG_DIR/requestLog_${i}.txt"
                python3 Chord_Client.py insert "$args" --port $port | tee -a "$LOG_DIR/requestLog_${i}.txt"
            elif [ "$request_type" == "query" ]; then
                echo "Querying: $args on node $i (port $port)" | tee -a "$LOG_DIR/requestLog_${i}.txt"
                python3 Chord_Client.py query "$args" --port $port | tee -a "$LOG_DIR/requestLog_${i}.txt"
            fi
        done < "$file" &
    done
    
    wait
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)
    echo "Request execution time for k=$k, consistency=$consistency: $duration seconds" | tee -a "$LOG_DIR/requestResults.csv"
    echo "$k,$consistency,$duration" >> "$LOG_DIR/requestResults.csv"
}

# Main execution
rm -f "$LOG_DIR/requestResults.csv"
rm -f "$LOG_DIR/requestLog_*.txt"
echo "k,consistency,time" > "$LOG_DIR/requestResults.csv"

for consistency in "${CONSISTENCIES[@]}"; do
    start_nodes
    sleep 5
    execute_requests "$consistency"
    echo "Experiment with k=$k and consistency=$consistency completed." | tee -a "$LOG_DIR/requestResults.csv"
    sleep 5
done

echo "Request phase completed. Nodes are still running for further queries."
