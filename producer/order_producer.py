# Keep creating events in short events until the script is cut off 
import time

# Related configs
KAFKA_TOPIC_NAME = "orders"
ORDER_GENERATION_TIMEOUT = 10

def create_event():
    pass

def push_to_kafka_topic(topic_name, event): 
    pass

if __name__ == "__main__":
    count = 0
    
    
    # ensure that topic is created / exists

    while(1): 
        event = create_event() 
        push_to_kafka_topic(KAFKA_TOPIC_NAME, event)
        time.sleep(ORDER_GENERATION_TIMEOUT)
        count += 1
    print(count, "events have been pushed to Kafka topic")
    