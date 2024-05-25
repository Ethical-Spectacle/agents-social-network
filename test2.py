from dbObject import dbObject  # Ensure you import the dbObject class from the correct module
import time

def run_tests():
    db = dbObject()

    # Create a network
    network_id = "grapevine-test"
    # db.create_network(network_id, "Grapevine Test Network", "A network for testing the Grapevine chatbot.")

    agent_id1 = "1"
    agent_id2 = "2"

    # # Create agents
    # agent_id1 = db.create_agent(network_id)
    # agent_id2 = db.create_agent(network_id)

    # # Wait for the data to be properly indexed
    # time.sleep(5)

    # # Add data to agents
    # db.add_agent_data(agent_id1, "micheal, a software engineer, is working on a new project with agents, and is looking for people to join his team.")
    # db.add_agent_data(agent_id1, "maximus, is a tall guy who plays basketball at ASU.")
    # db.add_agent_data(agent_id2, "Hello, this is a test message.")
    # db.add_agent_data(agent_id2, "Another test message with different content.")

    # # Wait for the data to be properly indexed
    # time.sleep(5)

    # Query agent memory
    print(f"Querying memory for agent '{agent_id1}'...")
    memory1 = db.get_agent_memory(agent_id1)
    print(f"Memory for agent '{agent_id1}': {memory1}")

    print(f"Querying memory for agent '{agent_id2}'...")
    memory2 = db.get_agent_memory(agent_id2)
    print(f"Memory for agent '{agent_id2}': {memory2}")

    print(f"Querying memory for agent '{agent_id1}' with query string 'software engineer'...")
    memory1_query = db.get_agent_memory(agent_id1, "software engineer")
    print(f"Memory for agent '{agent_id1}' with query string: {memory1_query}")

    print(f"Querying memory for agent '{agent_id2}' with query string 'test message'...")
    memory2_query = db.get_agent_memory(agent_id2, "test message")
    print(f"Memory for agent '{agent_id2}' with query string: {memory2_query}")

if __name__ == "__main__":
    run_tests()
