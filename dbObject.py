import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import weaviate
from weaviate.exceptions import WeaviateBaseError

class dbObject:
    def __init__(self):
        load_dotenv()
        self.client = weaviate.Client(
            url=os.getenv("WCS_URL"),
            auth_client_secret=weaviate.auth.AuthApiKey(os.getenv("WCS_API_KEY")),
            additional_headers={
                "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")
            }
        )
        self._ensure_base_classes_exist()

####################### SCHEMA ############################
    def _ensure_base_classes_exist(self):
        network_class = {
            "class": "Networks",
            "properties": [
                {"name": "networkID", "dataType": ["string"]},
                {"name": "name", "dataType": ["string"]},
                {"name": "description", "dataType": ["text"]}
            ]
        }

        agent_class = {
            "class": "Agents",
            "properties": [
                {"name": "agentID", "dataType": ["string"]},
                {"name": "network", "dataType": ["Network"]},
                {"name": "createdAt", "dataType": ["date"]},
                {"name": "inContextPrompt", "dataType": ["text"]}
            ]
        }

        try:
            self.client.schema.create({"classes": [network_class, agent_class]})
            print("Base classes created successfully.")
        except WeaviateBaseError as e:
            if "already exists" not in str(e):  # ignore "already exists" errors
                print(f"An error occurred: {e}")

################################ NETWORKS ################################
    def create_network(self, network_id, name, description):
        network_object = {
            "networkID": network_id,
            "name": name,
            "description": description
        }
        try:
            self.client.data_object.create(network_object, "Networks")
            print(f"Network '{name}' added successfully.")
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")

################################ AGENTS ################################
    def create_agent(self, network_id):
        agent_id = self._get_next_agent_id()
        if agent_id is None:
            print("Failed to create agent due to ID generation failure.")
            return

        agent_id_str = str(agent_id)
        agent_object = {
            "agentID": agent_id_str,
            "network": {
                "beacon": f"weaviate://localhost/Network/{network_id}"
            },
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "inContextPrompt": f"You are an Gen Z texter. You can use abbreviations and common slang. You can ask questions, provide answers, or just chat. You should not say anything offensive, toxic, ignorant, or malicious."
        }
        try:
            self.client.data_object.create(agent_object, "Agents")
            print(f"Agent '{agent_id}' added successfully.")

            self._create_agent_class(agent_id_str)
            return agent_id_str
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")
            return f"An error occurred: {e}"
        
    # create agent brain
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

    def _get_next_agent_id(self):
        try:
            query = """
            {
                Aggregate {
                    Agents {
                        meta {
                            count
                        }
                    }
                }
            }
            """
            response = self.client.query.raw(query)
            count = response["data"]["Aggregate"]["Agents"][0]["meta"]["count"]
            return count + 1
        except WeaviateBaseError as e:
            print(f"An error occurred while getting next agent ID: {e}")
            return None

    def add_agent_data(self, agent_id, data_content, toxicity_flag=False):
        agent_data_class = f"AgentData_{agent_id}"
        agent_data_object = {
            "dataContent": data_content,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "toxicityFlag": toxicity_flag
        }
        try:
            self.client.data_object.create(agent_data_object, agent_data_class)
            print(f"Data for agent '{agent_id}' added successfully.")
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")

    def get_agent_memory(self, agent_id, query_string=None):
        agent_data_class = f"AgentData_{agent_id}"
        try:
            if query_string:
                response = self.client.query.get(agent_data_class, ["dataContent", "toxicityFlag"]) \
                    .with_bm25(query=query_string) \
                    .do()
            else:
                response = self.client.query.get(agent_data_class, ["dataContent", "toxicityFlag"]).do()
            return response
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")
            return None


    def update_in_context_prompt(self, agent_id, new_prompt):
        try:
            if new_prompt is None:
                raise ValueError("New prompt is None, cannot update in-context prompt.")

            # Assert the new prompt is UTF-8 encoded
            self._assert_utf8(new_prompt)

            # First, retrieve the UUID of the agent using the agentID
            response = self.client.query.get("Agents", ["_additional { id }"]) \
                .with_where({
                    "path": ["agentID"],
                    "operator": "Equal",
                    "valueString": agent_id
                }) \
                .do()
            
            if not response['data']['Get']['Agents']:
                print(f"No agent found with agentID '{agent_id}'")
                return
            
            uuid = response['data']['Get']['Agents'][0]['_additional']['id']
            
            # Update the in-context prompt using the UUID
            self.client.data_object.update({
                "inContextPrompt": new_prompt
            }, class_name="Agents", uuid=uuid)
            print(f"In-context prompt for agent '{agent_id}' updated successfully.")
        except ValueError as e:
            print(f"Validation error: {e}")
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")

    def _assert_utf8(self, text):
        try:
            text.encode('utf-8')
        except UnicodeEncodeError:
            raise ValueError("Text is not valid UTF-8")

    def get_in_context_prompt(self, agent_id):
        try:
            response = self.client.query.get("Agents", ["inContextPrompt"]) \
                .with_where({
                    "path": ["agentID"],
                    "operator": "Equal",
                    "valueString": agent_id
                }) \
                .do()
            
            # Debugging output to inspect the response structure
            # print(f"Response: {response}")

            if 'data' in response and 'Get' in response['data'] and 'Agents' in response['data']['Get']:
                agents = response['data']['Get']['Agents']
                if len(agents) > 0:
                    return agents[0]['inContextPrompt']
                else:
                    print("No agents found with the provided agentID.")
                    return None
            else:
                print("Unexpected response structure.")
                return None
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")
            return None

