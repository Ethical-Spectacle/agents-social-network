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
            "inContextPrompt": f"You are a Gen Z texter. You can use abbreviations and common slang. You can ask questions, provide answers, or just chat. You should not say anything offensive, toxic, ignorant, or malicious."
        }
        try:
            self.client.data_object.create(agent_object, "Agents")
            print(f"Agent '{agent_id}' added successfully.")

            self._create_agent_class(agent_id_str)
            return agent_id_str
        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")
            return f"An error occurred: {e}"
        
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
            self.client.schema.create_class(agent_data_class)
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
        print(f"Inserting data into {agent_data_class}: {agent_data_object}")  # Log the data being inserted
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
                    .with_additional("score") \
                    .with_limit(10) \
                    .do()
            else:
                response = self.client.query.get(agent_data_class, ["dataContent", "toxicityFlag"]).do()

            # print(f"Response: {response}")
            
            filtered_response = []
            if 'data' in response and 'Get' in response['data'] and agent_data_class in response['data']['Get']:
                for item in response['data']['Get'][agent_data_class]:
                    if query_string:
                        if '_additional' in item and 'score' in item['_additional']:
                            score = float(item['_additional']['score'])
                            if score > 0.01:
                                filtered_response.append(item)
                    else:
                        filtered_response.append(item)
            else:
                print(f"No data found for agent '{agent_id}'.")

            return filtered_response

        except WeaviateBaseError as e:
            print(f"An error occurred: {e}")
            return None

    def update_in_context_prompt(self, agent_id, new_prompt):
        try:
            if new_prompt is None:
                raise ValueError("New prompt is None, cannot update in-context prompt.")

            self._assert_utf8(new_prompt)

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
