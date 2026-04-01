import time
import json
from typing import Callable

from kafka import KafkaConsumer

from .config import get_kafka_config


class KafkaBatchConsumer:
    """
    Generic batched Kafka consumer.

    Polls messages from a topic and delivers them to a user-supplied
    callback in batches (by size or timeout, whichever triggers first).
    Offsets are committed only after the callback returns successfully.

    Usage:
        def handle_batch(messages: list[dict]) -> None:
            for msg in messages:
                print(msg)

        consumer = KafkaBatchConsumer(topic="orders", batch_size=10)
        consumer.consume(process_fn=handle_batch)   # blocks until Ctrl+C
    """

    def __init__(
        self,
        topic: str,
        group_id: str = None,
        bootstrap_servers: str = None,
        batch_size: int = None,
        batch_timeout_s: int = None,
        value_deserializer: Callable = None,
        auto_offset_reset: str = "earliest",
    ):
        config = get_kafka_config(
            bootstrap_servers=bootstrap_servers,
            consumer_group_id=group_id,
            batch_size=batch_size,
            batch_timeout_s=batch_timeout_s,
        )

        self._topic = topic
        self._batch_size = config["batch_size"]
        self._batch_timeout_s = config["batch_timeout_s"]

        if value_deserializer is None:
            value_deserializer = lambda v: json.loads(v.decode("utf-8"))

        self._consumer = KafkaConsumer(
            topic,
            bootstrap_servers=[config["bootstrap_servers"]],
            group_id=config["consumer_group_id"],
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=False,
            value_deserializer=value_deserializer,
        )
        print(
            f"KafkaBatchConsumer connected | topic={topic} "
            f"group={config['consumer_group_id']} "
            f"batch_size={self._batch_size} "
            f"timeout={self._batch_timeout_s}s"
        )

    def consume(self, process_fn: Callable[[list[dict]], None]) -> None:
        """
        Main consumption loop — blocks until KeyboardInterrupt.

        Accumulates polled messages into a batch. Flushes the batch to
        `process_fn` when either:
          - the batch reaches `batch_size`, or
          - `batch_timeout_s` seconds have elapsed since the last flush
            (and the batch is non-empty).

        Offsets are committed after `process_fn` returns. If `process_fn`
        raises, offsets are NOT committed — messages will be redelivered
        on the next startup.

        Args:
            process_fn: callback receiving list[dict] (deserialized values).
        """
        batch: list = []
        last_flush_time = time.time()

        try:
            while True:
                poll_result = self._consumer.poll(timeout_ms=1000)

                if poll_result:
                    for _, messages in poll_result.items():
                        batch.extend(msg.value for msg in messages)

                elapsed = time.time() - last_flush_time
                ready_by_size = len(batch) >= self._batch_size
                ready_by_time = elapsed >= self._batch_timeout_s and len(batch) > 0

                if ready_by_size or ready_by_time:
                    reason = "size" if ready_by_size else "timeout"
                    print(f"Flushing batch ({reason}): {len(batch)} messages")

                    process_fn(batch)

                    self._consumer.commit()
                    batch = []
                    last_flush_time = time.time()

        except KeyboardInterrupt:
            print("\nShutting down consumer...")
        finally:
            self.close()

    def close(self) -> None:
        """Close the underlying KafkaConsumer."""
        self._consumer.close()
        print("Consumer closed.")
