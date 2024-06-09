import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import weaviate
from weaviate.exceptions import WeaviateBaseError

# This class is the main interface to the Weaviate database. It handles all interactions with the database.
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

        assert self.client.is_ready()  # check if client is ready

        self._ensure_base_classes_exist()

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

         # if the database hasn't been setup it will create those classes
        try:
            existing_classes = self.client.schema.get()['classes']
            existing_class_names = [cls['class'] for cls in existing_classes]

            if "Networks" not in existing_class_names:
                self.client.schema.create_class(network_class)
                print("Networks class created successfully.")
            else:
                print("Networks class already exists.")

            if "Agents" not in existing_class_names:
                self.client.schema.create_class(agent_class)
                print("Agents class created successfully.")
            else:
                print("Agents class already exists.")

        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")

    # *** Network methods ***
    # ? Do we need to autogenerate unique network IDs?
    def create_network(self, network_id, name, description):
        """
        Create a network in the database. 
        """
        network = {
            "networkID": network_id,
            "name": name,
            "description": description
        }

        try:
            self.client.data_object.create(network, "Networks")
            print(f"Network {network_id} created successfully.")
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")

    def get_network(self, network_name) -> str:
        """
        Get a network from the database by name. Returns the network ID.
        """
        try:
            response = self.client.query.get("Networks", ["networkID", "name", "description"]) \
                .with_where({
                    "path": ["name"],
                    "operator": "Equal",
                    "valueString": network_name
                }) \
                .do()
            
            if 'data' in response and 'Get' in response['data'] and 'Networks' in response['data']['Get']:
                networks = response['data']['Get']['Networks']
                if len(networks) > 0:
                    return networks[0].get("networkID")
                else:
                    print("No networks found with the provided agentID.")
                    return None
                
            else:
                print("Unexpected response structure.")
                return None
            
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")
            return None
        
        
    # *** Agent methods ***
    # create an agent
    def create_agent(self, network_name) -> str:
        """
        Create an agent within a network given the network name. Returns the agent ID.
        """
        agent_id = self._get_next_agent_id()
        print(f"Creating agent with ID: {agent_id}")
        network_id = self.get_network(network_name)

        agent_object = {
            "agentID": str(agent_id),
            "network": {
                "beacon": f"weaviate://localhost/Network/{network_id}"
            },
            "createdAt": datetime.now(timezone.utc).isoformat(),
            # This is basically the prompt that the agent will use to generate responses. This can be edited by the user later on. 
            "inContextPrompt": f"You are a Gen Z texter. You can use abbreviations and common slang. You can ask questions, provide answers, or just chat. You should not say anything offensive, toxic, ignorant, or malicious."
        }

        try:
            # create the agent
            self.client.data_object.create(agent_object, "Agents")

            # create memory class for the agent
            self._create_agent_class(str(agent_id))

            print(f"Agent '{agent_id}' created successfully.")
            return str(agent_id)
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")
            return None
    
    # add data to an agent
    def add_agent_data(self, agent_id: str, data_content, toxicity_flag=False):
        """
        Add data to an agent in the database. This is the information that the agent will store.
        """
        agent_data_class = f"AgentData_{agent_id}"
        agent_data_object = {
            "dataContent": data_content,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "toxicityFlag": toxicity_flag
        }
        print(f"Inserting data into {agent_data_class}: {agent_data_object}")

        try:
            self.client.data_object.create(agent_data_object, agent_data_class)
            print(f"Data for agent '{agent_id}' added successfully.")
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")
        
    # memory retrieval for the agent
    def get_agent_memory(self, agent_id, query_string=None): 
        agent_data_class = f"AgentData_{agent_id}"
        try:
            if query_string:
                # query based on dataContent relevancy to the query string
                response = self.client.query.get(agent_data_class, ["dataContent", "toxicityFlag"]) \
                    .with_bm25(query=query_string) \
                    .with_additional("score") \
                    .with_limit(10) \
                    .do()
            else:
                # returns all memories for the agent if no query string is provided
                response = self.client.query.get(agent_data_class, ["dataContent", "toxicityFlag"]).do()

            # * parse memories and only keep one's over our relevancy threshold
            filtered_response = []
            if 'data' in response and 'Get' in response['data'] and agent_data_class in response['data']['Get']:
                for item in response['data']['Get'][agent_data_class]:
                    if query_string:
                        if '_additional' in item and 'score' in item['_additional']:
                            score = float(item['_additional']['score'])
                            if score > 0.01: # TODO: set threshold here (0.01 is just for testing, i'm thinking we'll use like 0.5 or 0.6)
                                # TODO: add another if check here for the toxicity flag (however we decide to interpret that)
                                filtered_response.append(item)
                    else:
                        filtered_response.append(item)
            else:
                print(f"No data found for agent '{agent_id}'.")
            return filtered_response

        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")
            return None
    
    # get the in-context prompt for an agent
    def get_in_context_prompt(self, agent_id: str):
        try:

            response = self.client.query.get("Agents", ["inContextPrompt"]) \
                .with_where({
                    "path": ["agentID"],
                    "operator": "Equal",
                    "valueString": agent_id
                }) \
                .do()
            
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

    # update the in-context prompt for an agent
    def update_in_context_prompt(self, agent_id: str, new_prompt):
        try:
            if new_prompt is None:
                raise ValueError("New prompt is None, cannot update in-context prompt.")

            # get uuid of agent to update
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
            
            # update the in-context prompt
            self.client.data_object.update({
                "inContextPrompt": new_prompt
            }, class_name="Agents", uuid=uuid)

            print(f"In-context prompt for agent '{agent_id}' updated successfully.")
            # return the in-context prompt
            return new_prompt

        except ValueError as e:
            print(f"Validation error: {e}")

        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")


    # *** Private methods *** 
    def _create_agent_class(self, agent_id):
        """
        Create a class (memory) for an agent in the database. 
        """
        agent_data_class = {
            "class": f"AgentData_{agent_id}",
            "properties": [
                {"name": "dataContent", "dataType": ["text"]},
                {"name": "createdAt", "dataType": ["date"]},
                {"name": "toxicityFlag", "dataType": ["boolean"]}
            ],
            "vectorizer": "text2vec-openai",
            "moduleConfig": {
                "text2vec-openai": {
                    "vectorizeClassName": True,
                    "vectorizeProperties": ["dataContent"]
                }
            }
        }
        try:
            # execute creating class in weaviate
            self.client.schema.create_class(agent_data_class)
            print(f"Class (memory) for agent '{agent_id}' created successfully.")

        except WeaviateBaseError as e:
            print(f"An error occurred while creating class for agent '{agent_id}': {e}")
        
    def _get_next_agent_id(self):
        """
        Get the next available agent ID."""
        try:
            # graphql query to get the count of agents
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
            return count + 1 # returns the next available agentID
        
        except WeaviateBaseError as e:
            print(f"An error occurred while getting next agent ID: {e}")
            return None