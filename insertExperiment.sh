#--------Usage---------
#chmod +x insertExperiment.sh
#dos2unix insertExperiment.sh
#bash insertExperiment.sh

# Configuration
IP="127.0.0.1"
BASE_PORT=5000
NODE_COUNT=10
INSERT_PATH="./data/insert"
EXPERIMENTS=(1 3 5) # k values
CONSISTENCIES=("linearizability" "eventual")
LOG_DIR="./logs/insert_logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to start nodes
start_nodes() {
    local k=$1
    local consistency=$2
    
    echo "Starting bootstrap node with k=$k and consistency=$consistency..." | tee -a "$LOG_DIR/insertLog_0.txt"
    bash -c "python3 node.py $IP $BASE_PORT $k $consistency | tee $LOG_DIR/insertLog_0.txt &" &
    sleep 2
    
    for ((i=1; i<$NODE_COUNT; i++)); do
        port=$((BASE_PORT + i))
        echo "Starting node $i on port $port..." | tee -a "$LOG_DIR/insertLog_${i}.txt"
        bash -c "python3 node.py $IP $port $IP $BASE_PORT | tee $LOG_DIR/insertLog_${i}.txt &" &
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

# Function to execute inserts
execute_inserts() {
    local k=$1
    local consistency=$2
    
    echo "Running inserts with k=$k and consistency=$consistency" | tee -a "$LOG_DIR/insertResults.csv"
    start_time=$(date +%s.%N)
    
    for ((i=0; i<$NODE_COUNT; i++)); do
        port=$((BASE_PORT + i))
        file="$INSERT_PATH/insert_0${i}_part.txt"
        echo "Inserting data from $file to node $i on port $port..." | tee -a "$LOG_DIR/insertLog_${i}.txt"

        while read -r line; do
            echo "Inserting key: '$line'" | tee -a "$LOG_DIR/insertLog_${i}.txt"
            python3 Chord_Client.py insert "$line" --port $port | tee -a "$LOG_DIR/insertLog_${i}.txt"
        done < "$file" &
    done
    
    wait
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)
    echo "Write throughput for k=$k and consistency=$consistency: $duration seconds" | tee -a "$LOG_DIR/insertResults.csv"
    echo "$k,$consistency,$duration" >> "$LOG_DIR/insertResults.csv"
}

# Main execution
rm -f "$LOG_DIR/insertResults.csv"
rm -f "$LOG_DIR/insertLog_*.txt"
echo "k,consistency,time" > "$LOG_DIR/insertResults.csv"

for k in "${EXPERIMENTS[@]}"; do
    for consistency in "${CONSISTENCIES[@]}"; do
        start_nodes "$k" "$consistency"
        sleep 5
        execute_inserts "$k" "$consistency"
        echo "Experiment with k=$k and consistency=$consistency completed." | tee -a "$LOG_DIR/insertResults.csv"
        sleep 5
        pkill -f node.py
    done
done

echo "All experiments completed. Nodes have been shut down."
