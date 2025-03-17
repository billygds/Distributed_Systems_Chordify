
#--------Usage in Ubuntu---------
#chmod +x queryExperiment.sh - Once
#dos2unix insertExperiment.sh - Once
#bash queryExperiment.sh

# Configuration
IP="127.0.0.1"
BASE_PORT=5000
NODE_COUNT=10
QUERY_PATH="./data/queries"
EXPERIMENTS=(1 3 5) # k values
CONSISTENCIES=("linearizability" "eventual")

# Function to start nodes
start_nodes() {
    echo "Starting bootstrap node..." | tee -a queryLog_0.txt
    bash -c "python3 node.py $IP $BASE_PORT $1 | tee queryLog_0.txt &" &
    sleep 2
    
    for ((i=1; i<$NODE_COUNT; i++)); do
        port=$((BASE_PORT + i))
        echo "Starting node $i on port $port..." | tee -a queryLog_${i}.txt
        bash -c "python3 node.py $IP $port $IP $BASE_PORT | tee queryLog_${i}.txt &" &
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

# Function to execute queries
execute_queries() {
    local k=$1
    local consistency=$2
    
    echo "Running queries with k=$k and consistency=$consistency" | tee -a queryResults.csv
    start_time=$(date +%s.%N)
    
    for ((i=0; i<$NODE_COUNT; i++)); do
        port=$((BASE_PORT + i))
        file="$QUERY_PATH/query_0${i}.txt"
        echo "Executing queries from $file on node $i (port $port)..." | tee -a queryLog_${i}.txt

        while read -r line; do
            echo "Querying key: '$line'" | tee -a queryLog_${i}.txt
            python3 Chord_Client.py query "$line" | tee -a queryLog_${i}.txt
        done < "$file" &
    done
    
    wait
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)
    echo "Read throughput for k=$k, consistency=$consistency: $duration seconds" | tee -a queryResults.csv
    echo "$k,$consistency,$duration" >> queryResults.csv
}

# Main execution
rm -f queryResults.csv
rm -f queryLog_*.txt
echo "k,consistency,time" > queryResults.csv

for k in "${EXPERIMENTS[@]}"; do
    for consistency in "${CONSISTENCIES[@]}"; do
        start_nodes "$k"
        sleep 5
        execute_queries "$k" "$consistency"
        echo "Experiment with k=$k and consistency=$consistency completed." | tee -a queryResults.csv
        pkill -f node.py
        sleep 5
    done
done

echo "All experiments completed. Results saved in queryResults.csv." | tee -a queryResults.csv
