import os
from agentObject import Agent
from dbObject import dbObject

# create or get a network
db = dbObject()
network_id = "grapevine-test"
db.create_network(network_id, "Grapevine Test", "Internal test network")

# # create two agents
home_agent_id = db.create_agent(network_id)
away_agent_id = db.create_agent(network_id)
home_agent_id = "1"
away_agent_id = "2"

db.add_agent_data(home_agent_id, "micheal, a software engineer, is working on a new project with agents, and is looking for people to join his team.")
db.add_agent_data(home_agent_id, "maximus, is a tall guy who plays basketball at ASU.")

db.add_agent_data(away_agent_id, "jane, a data scientist in Phoenix, just graduated and is looking for a job.")
db.add_agent_data(away_agent_id, "mark, a man who loves to travel, is planning a trip to Europe.")

# init the agents
home_agent = Agent(network_id=network_id, agent_id=home_agent_id)
away_agent = Agent(network_id=network_id, agent_id=away_agent_id)

# func to run the test interaction
def run_test_interaction():
    print("Starting agent interaction test...\n")

    # interaction method
    home_agent.handle_agent_interaction(partner_agent_id=away_agent_id)

    print("\nAgent interaction test completed.")

# run
if __name__ == "__main__":
    run_test_interaction()
