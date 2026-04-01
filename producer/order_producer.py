# Keep creating events in short intervals until the script is cut off
import sys
import os
import time
import json

from kafka import KafkaProducer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from clients.kafka import KafkaAdmin
from clients.kafka.config import get_kafka_config
from order_generator import generate_order

# Related configs
KAFKA_TOPIC_NAME = os.environ.get("KAFKA_TOPIC", "orders")
ORDER_GENERATION_TIMEOUT = int(os.environ.get("PRODUCER_INTERVAL_SECONDS", "5"))
MAX_ORDER_IDS = 200

# Track a cycling counter so repeated runs continue cycling through IDs
_order_counter = 0


def create_event() -> dict:
    """Generate a single order event, cycling through 200 order IDs."""
    global _order_counter
    _order_counter += 1
    order_num = (_order_counter % MAX_ORDER_IDS) + 1
    return generate_order(order_num)


def push_to_kafka_topic(producer: KafkaProducer, topic_name: str, event: dict) -> None:
    """Send a single event to the Kafka topic, keyed by order_id."""
    key = event["order_id"].encode("utf-8")
    producer.send(topic_name, key=key, value=event)
    producer.flush()
    print(f"  Sent: {event}")


if __name__ == "__main__":
    config = get_kafka_config()
    bootstrap = config["bootstrap_servers"]

    # Ensure topic exists
    admin = KafkaAdmin(bootstrap_servers=bootstrap)
    admin.create_topic(KAFKA_TOPIC_NAME, num_partitions=3)
    admin.close()

    # Create a KafkaProducer with JSON serialization
    producer = KafkaProducer(
        bootstrap_servers=[bootstrap],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    print(f"Producer started | topic={KAFKA_TOPIC_NAME} interval={ORDER_GENERATION_TIMEOUT}s")

    count = 0
    try:
        while True:
            event = create_event()
            push_to_kafka_topic(producer, KAFKA_TOPIC_NAME, event)
            count += 1
            time.sleep(ORDER_GENERATION_TIMEOUT)
    except KeyboardInterrupt:
        print(f"\nStopped. {count} events pushed to '{KAFKA_TOPIC_NAME}'.")
    finally:
        producer.close()
