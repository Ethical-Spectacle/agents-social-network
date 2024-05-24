import os
from datetime import datetime
from dotenv import load_dotenv
import weaviate
from weaviate.exceptions import WeaviateBaseError

class WeaviateDB:
    def __init__(self,):
        load_dotenv()
        self.client = weaviate.Client(
            url=os.getenv("WCS_URL"),
            auth_client_secret=weaviate.auth.AuthApiKey(os.getenv("WCS_API_KEY")),
            additional_headers={
                "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")
            }
        )
        self._ensure_base_classes_exist()

    # schema (makes it if cluster gets reset)
    def _ensure_base_classes_exist(self):
        network_class = {
            "class": "Network",
            "properties": [
                {"name": "networkID", "dataType": ["string"]},
                {"name": "name", "dataType": ["string"]},
                {"name": "description", "dataType": ["text"]}
            ]
        }

        agent_class = {
            "class": "Agent",
            "properties": [
                {"name": "agentID", "dataType": ["string"]},
                {"name": "name", "dataType": ["string"]},
                {"name": "network", "dataType": ["Network"]},
                {"name": "createdAt", "dataType": ["date"]}
            ]
        }

        # agent data schema is in create_agent method

        try:
            self.client.schema.create({"classes": [network_class, agent_class]})
            print("Base classes created successfully.")
        except WeaviateBaseError as e:
            if "already exists" not in str(e):  # ignore "already exists" errors
                print(f"An error occurred: {e}")


    # create new network
    def create_network(self, network_id, name, description):
        network_object = {
            "networkID": network_id,
            "name": name,
            "description": description
        }
        try:
            self.client.data_object.create(network_object, "Network")
            print(f"Network '{name}' added successfully.")
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")


    # create new agent
    def create_agent(self, agent_id, name, network_id):
        agent_object = {
            "agentID": agent_id,
            "name": name,
            "network": {
                "beacon": f"weaviate://localhost/Network/{network_id}"
            },
            "createdAt": datetime.utcnow().isoformat() + "Z"
        }
        try:
            self.client.data_object.create(agent_object, "Agent")
            print(f"Agent '{name}' added successfully.")
            self._create_agent_class(agent_id)
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")


    # new agent class, only called by create_agent
    def _create_agent_class(self, agent_id):

        agent_data_class = {
            "class": f"AgentData_{agent_id}",
            "properties": [
                {"name": "dataContent", "dataType": ["text"]},
                {"name": "createdAt", "dataType": ["date"]},
                {"name": "toxicityFlag", "dataType": ["boolean"]}
            ]
        }

        try:
            self.client.schema.create({"classes": [agent_data_class]})
            print(f"Class for agent '{agent_id}' created successfully.")
        except WeaviateBaseError as e:
            print(f"An error occurred while creating class for agent '{agent_id}': {e}")


    # store thought (insert to class)
    def add_agent_data(self, agent_id, data_content, toxicity_flag=False):
        agent_data_class = f"AgentData_{agent_id}"
        agent_data_object = {
            "dataContent": data_content,
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "toxicityFlag": toxicity_flag
        }
        try:
            self.client.data_object.create(agent_data_object, agent_data_class)
            print(f"Data for agent '{agent_id}' added successfully.")
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")


    # think back (query class)
    def get_agent_data(self, agent_id):
        agent_data_class = f"AgentData_{agent_id}"
        try:
            response = self.client.query.get(agent_data_class, ["dataContent", "toxicityFlag"]).do()
            return response
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")
            return None


# Example 

# db = WeaviateDB(weaviate_url, api_key)

# db.create_network("network1", "Network 1", "This is the first network")

# db.create_agent("agent1", "Agent 1", "network1")
# db.create_agent("agent2", "Agent 2", "network1")

# db.add_agent_data("agent1", "This is the first piece of data for Agent 1", toxicity_flag=True)

# agent_data = db.get_agent_data("agent1")
# print(agent_data)
