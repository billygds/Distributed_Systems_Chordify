#--------Usage---------
#chmod +x queryExperiment.sh
#dos2unix queryExperiment.sh
#bash queryExperiment.sh

# Configuration
IP="127.0.0.1"
BASE_PORT=5000
NODE_COUNT=10
QUERY_PATH="./data/queries"
EXPERIMENTS=(1 3 5) # k values
CONSISTENCIES=("linearizability" "eventual")
LOG_DIR="./logs/query_logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to start nodes
start_nodes() {
    local k=$1
    local consistency=$2
    
    echo "Starting bootstrap node with k=$k and consistency=$consistency..." | tee -a "$LOG_DIR/queryLog_0.txt"
    bash -c "python3 node.py $IP $BASE_PORT $k $consistency | tee $LOG_DIR/queryLog_0.txt &" &
    sleep 2
    
    for ((i=1; i<$NODE_COUNT; i++)); do
        port=$((BASE_PORT + i))
        echo "Starting node $i on port $port..." | tee -a "$LOG_DIR/queryLog_${i}.txt"
        bash -c "python3 node.py $IP $port $IP $BASE_PORT | tee $LOG_DIR/queryLog_${i}.txt &" &
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

# Function to execute queries on existing nodes
execute_queries() {
    local k=$1
    local consistency=$2
    
    echo "Running queries with k=$k and consistency=$consistency" | tee -a "$LOG_DIR/queryResults.csv"
    start_time=$(date +%s.%N)
    
    for ((i=0; i<$NODE_COUNT; i++)); do
        port=$((BASE_PORT + i))
        file="$QUERY_PATH/query_0${i}.txt"
        echo "Executing queries from $file on node $i (port $port)..." | tee -a "$LOG_DIR/queryLog_${i}.txt"

        while read -r line; do
            echo "Querying key: '$line'" | tee -a "$LOG_DIR/queryLog_${i}.txt"
            python3 Chord_Client.py query "$line" --port $port | tee -a "$LOG_DIR/queryLog_${i}.txt"
        done < "$file" &
    done
    
    wait
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)
    echo "Read throughput for k=$k and consistency=$consistency: $duration seconds" | tee -a "$LOG_DIR/queryResults.csv"
    echo "$k,$consistency,$duration" >> "$LOG_DIR/queryResults.csv"
}

# Main execution
rm -f "$LOG_DIR/queryResults.csv"
rm -f "$LOG_DIR/queryLog_*.txt"
echo "k,consistency,time" > "$LOG_DIR/queryResults.csv"

for k in "${EXPERIMENTS[@]}"; do
    for consistency in "${CONSISTENCIES[@]}"; do
        start_nodes "$k" "$consistency"
        sleep 5
        execute_queries "$k" "$consistency"
        echo "Experiment with k=$k and consistency=$consistency completed." | tee -a "$LOG_DIR/queryResults.csv"
        sleep 5
        pkill -f node.py
    done
done

echo "All experiments completed. Nodes have been shut down."
