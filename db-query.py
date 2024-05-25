import os
from dotenv import load_dotenv
import weaviate
from weaviate.exceptions import WeaviateBaseError

# Load environment variables
load_dotenv()

# Initialize Weaviate client
client = weaviate.Client(
    url=os.getenv("WCS_URL"),
    auth_client_secret=weaviate.auth.AuthApiKey(os.getenv("WCS_API_KEY")),
    additional_headers={
        "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")
    }
)

# Function to retrieve schema and get a list of all classes with their properties
def get_classes_with_properties(client):
    try:
        schema = client.schema.get()
        classes = {cls['class']: [prop['name'] for prop in cls['properties']] for cls in schema['classes']}
        return classes
    except WeaviateBaseError as e:
        print(f"An error occurred while retrieving the schema: {e}")
        return {}

# Function to query and print all data points for the Agents class using `with_where`
def query_agents_class(client):
    try:
        response = client.query.get("Agents", ["agentID", "createdAt", "inContextPrompt", "network", "_additional { id }"]).do()
        return response
    except WeaviateBaseError as e:
        print(f"An error occurred while querying class 'Agents': {e}")
        return {}

# Function to query and print all data points for a given class
def query_all_datapoints_for_class(client, class_name, properties):
    properties_query = ' '.join(properties)
    
    query = f"""
    {{
        Get {{
            {class_name} {{
                {properties_query}
                _additional {{
                    id
                }}
            }}
        }}
    }}
    """
    try:
        result = client.query.raw(query)
        return result
    except WeaviateBaseError as e:
        print(f"An error occurred while querying class '{class_name}': {e}")
        return {}

# Main function to query and print data points for all classes
def main():
    classes = get_classes_with_properties(client)
    print("Classes and their properties in the schema:", classes)
    
    for class_name, properties in classes.items():
        print(f"\nDatapoints for class '{class_name}':")
        if class_name == "Agents":
            datapoints = query_agents_class(client)
        else:
            datapoints = query_all_datapoints_for_class(client, class_name, properties)
        
        # Ensure 'data' key exists in the response
        if 'data' in datapoints and 'Get' in datapoints['data']:
            print(datapoints)
        else:
            print(f"No data found for class '{class_name}'")

if __name__ == "__main__":
    main()
