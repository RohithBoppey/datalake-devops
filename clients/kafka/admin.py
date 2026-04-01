from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

from .config import get_kafka_config


class KafkaAdmin:
    """
    Thin wrapper around KafkaAdminClient for topic management.

    Usage:
        admin = KafkaAdmin()
        admin.create_topic("orders", num_partitions=3)
        print(admin.list_topics())
        admin.close()
    """

    def __init__(self, bootstrap_servers: str = None):
        config = get_kafka_config(bootstrap_servers=bootstrap_servers)
        self._admin = KafkaAdminClient(
            bootstrap_servers=config["bootstrap_servers"],
        )

    def create_topic(
        self,
        topic_name: str,
        num_partitions: int = 1,
        replication_factor: int = 1,
    ) -> None:
        """Create a topic. No-ops if it already exists."""
        topic = NewTopic(
            name=topic_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
        )
        try:
            self._admin.create_topics([topic])
            print(f"Topic '{topic_name}' created "
                  f"(partitions={num_partitions}, rf={replication_factor}).")
        except TopicAlreadyExistsError:
            print(f"Topic '{topic_name}' already exists, skipping.")

    def list_topics(self) -> list[str]:
        """Return a list of all topic names on the broker."""
        return list(self._admin.list_topics())

    def topic_exists(self, topic_name: str) -> bool:
        """Check whether a topic exists."""
        return topic_name in self.list_topics()

    def delete_topic(self, topic_name: str) -> None:
        """Delete a topic by name."""
        self._admin.delete_topics([topic_name])
        print(f"Topic '{topic_name}' deleted.")

    def close(self) -> None:
        """Close the admin client connection."""
        self._admin.close()
