import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import weaviate
from weaviate.exceptions import WeaviateBaseError

# to be honest, there is a lot of functionality for RAG and weaviate interactions in DSPy
# got frustrated with some things that got broken it weaviate v4, so we're building custom methods for a lot of the same things

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

    # schemas for the classes database init
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

    # make a new network (not really implemented yet, but agents should be confined to their own network)
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


    # create a new agent
    def create_agent(self, network_id):
        agent_id = self._get_next_agent_id()
        if agent_id is None:
            print("Failed to create agent due to ID generation failure.")
            return

        agent_id_str = str(agent_id)

        # agent's class entry schema 
        # (each agent gets an entry in the Agents class), the inContextPrompt can be updated and is prepended to every prompt the llm sees.
        agent_object = {
            "agentID": agent_id_str,
            "network": {
                "beacon": f"weaviate://localhost/Network/{network_id}"
            },
            "createdAt": datetime.now(timezone.utc).isoformat(),
            # we should spend a lot of time figuring out the defaults we want people to start with (but they can update this by just asking their chat to update it)
            "inContextPrompt": f"You are a Gen Z texter. You can use abbreviations and common slang. You can ask questions, provide answers, or just chat. You should not say anything offensive, toxic, ignorant, or malicious."
        }
        try:
            self.client.data_object.create(agent_object, "Agents")
            print(f"Agent '{agent_id}' added successfully.")

            # create the new class (new memory for each agent)
            self._create_agent_class(agent_id_str)
            return agent_id_str
        
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")
            return f"An error occurred: {e}"
        
    # schema for each agent's memory class
    def _create_agent_class(self, agent_id):
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
            # execure creating class in weaviate
            self.client.schema.create_class(agent_data_class)
            print(f"Class for agent '{agent_id}' created successfully.")

        except WeaviateBaseError as e:
            print(f"An error occurred while creating class for agent '{agent_id}': {e}")

    # every agent should have a unique id, auto incrementing rn like this and it's so stupid
    # agent ID's are unique even outside of their network.
    def _get_next_agent_id(self):
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
            return count + 1 # returns the next avail
        
        except WeaviateBaseError as e:
            print(f"An error occurred while getting next agent ID: {e}")
            return None

    # add data to an agent's memory 
    def add_agent_data(self, agent_id, data_content, toxicity_flag=False):
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

    # memory retrevial
    def get_agent_memory(self, agent_id, query_string=None): # in the agents obj I want to add a step to create a query string worded for RAG w bm25 (vector distance ranking)
        agent_data_class = f"AgentData_{agent_id}"
        try:
            if query_string:
                # query based on dataContent relevancy to the query string
                # this is the way we should query weaviate whenever we can (using their SDK methonds rather than writing our own graphql)
                response = self.client.query.get(agent_data_class, ["dataContent", "toxicityFlag"]) \
                    .with_bm25(query=query_string) \
                    .with_additional("score") \
                    .with_limit(10) \
                    .do()
            else:
                # janky solution, not really sure about how this default should work. Maybe most recent returns? fringe case anyways only matters if the input prompt gets messed up
                response = self.client.query.get(agent_data_class, ["dataContent", "toxicityFlag"]).do()

            # print(f"Response: {response}")
            
            # parse memories and only keep one's over our relevancy threshold
            filtered_response = []
            if 'data' in response and 'Get' in response['data'] and agent_data_class in response['data']['Get']:
                for item in response['data']['Get'][agent_data_class]:
                    if query_string:
                        if '_additional' in item and 'score' in item['_additional']:
                            score = float(item['_additional']['score'])
                            if score > 0.01: # set threshold here (0.01 is just for testing, i'm thinking we'll use like 0.5 or 0.6)
                                # add another if check here for the toxicity flag (however we decide to interpret that)
                                filtered_response.append(item)
                    else:
                        filtered_response.append(item)
            else:
                print(f"No data found for agent '{agent_id}'.")

            return filtered_response

        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")
            return None

    # update the in-context prompt for an agent ("settings")
    def update_in_context_prompt(self, agent_id, new_prompt):
        # this function is bloated, can cut back
        try:
            if new_prompt is None:
                raise ValueError("New prompt is None, cannot update in-context prompt.")

            self._assert_utf8(new_prompt) # we're getting utf-8 errors when we recall it sometimes

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

        except ValueError as e:
            print(f"Validation error: {e}")

        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")

    # I don't even this this is working
    def _assert_utf8(self, text):
        try: text.encode('utf-8')
        except UnicodeEncodeError: raise ValueError("Text is not valid UTF-8")


    # get the in-context prompt for an agent
    def get_in_context_prompt(self, agent_id):
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
