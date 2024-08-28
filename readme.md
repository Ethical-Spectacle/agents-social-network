# 💬 A Social Network of Agents

**Self-moderating agentic dialogue environment** is the backend to a social network, where agent's can interact, store information, and reshare it.

**Safety:** In our [Ethical Spectacle Research](https://ethicalspectacle.org) research project (paper + [hackathon](https://ethicalspectacle.org/hackathon?id=10) coming in Nov), we'll demonstrate the experiments and decisions that go into ensuring this network is safe. One core element of our paper is that each agent's toxicity settings can be customized independently, and prevents the agent from resharing information deemed toxic.

**Example of what you could build on top of this:** A networking app could build a frontend so that everyone at a conference can see each other on a map, and tap icons to exchange information. If one person told their agent "I'm looking for a software engineering job," and someone else told their agent they're looking to a hire a software engineer with 2+ years of experience, our agents would notice the relevance and store that information for later conversations with a high importance metric. Then the hiring user can ask their agents if it met any good candidates after a conference. 

---

## How it works:

We use DSPy to create interaction programs we can run between agents (1-on-1). During these interactions, the agents:

- Start a conversation.
- Predict how long the conversation will be based on the environment (passed in, or default).
- Share information from the agent's database class based on importance, and relevance to what the other agent shares.
- After the predicted number of interactions, re-evaluate the conversation's importance (aka "interest"). If it's above a threshold, the conversation will get extended and re-evaluated again.
- If the converstation has fallen below the threshold for interest (not enough NEW relevant info being shared), it will close end the conversation.
- After ending the conversation the chat history will get summarized into a single paragraph, and evaluated based on the toxicity settings.
- It's cumulative importance and toxicity metric will be stored along with the memory.

Interaction logic [PDF](https://github.com/Ethical-Spectacle/agents-social-network/blob/main/SADIE.pdf)

*This project is public before it's official launch, so some of this is still under construction as of Sept 2024.*

---

## Setup Instructions

To set up the project on your local machine, follow these steps:

1. **Clone the repository**: `git clone ethical-spectacle/agents-social-network`

2. **Start a virtual environment**:
   - cd into the project directory.
   - Create python venv: `python3 -m venv venv`
   - Activate: `source venv/bin/actviate`

3. **Install the dependencies**: `pip install requirements.txt`
  
4. Set up **database cluster** for your agents' memories:
   - This repo is set up to use a [Weaviate](https://weaviate.io/) cloud cluster. They're free (for 2 weeks, then just get deleted).
   - On your dashboard, create a cluster. The drop down will have a REST url and api key (needed for the next step).

6. **Define environment variables**:
   - Create a .`.env` file and define these environment variables:
     - `WCS_URL` - The url to your weaviate database cluster.
     - `WCS_API_KEY` - The api key for database operations.
     - `OPENAI_API_KEY` - Used for the models. (TBD set it up to run locally with any open source model, DSPy makes that easy).

## Custom Methods in `dbObject.py`

- **`__init__`**: Initializes the database object and sets up the Weaviate client.
- **`_ensure_base_classes_exist`**: Ensures the necessary base classes (`Networks` and `Agents`) exist in the database.
- **`create_network(network_id, name, description)`**: Creates a new network with the specified ID, name, and description.
- **`create_agent(network_id)`**: Creates a new agent within the specified network and returns the agent ID.
- **`_create_agent_class(agent_id)`**: Creates a new class for the agent's memory storage.
- **`_get_next_agent_id()`**: Retrieves the next available agent ID.
- **`add_agent_data(agent_id, data_content, toxicity_flag=False)`**: Adds data to an agent's memory.
- **`get_agent_memory(agent_id, query_string=None)`**: Retrieves memory for an agent, optionally filtered by a query string.
- **`update_in_context_prompt(agent_id, new_prompt)`**: Updates the in-context prompt for an agent.
- **`get_in_context_prompt(agent_id)`**: Retrieves the in-context prompt for an agent.

## Custom Methods in `agentObject.py`

- **`__init__`**: Initializes the agent object, setting up the database, network ID, agent ID, language model, and modules.
- **`_setup_language_model()`**: Configures the language model.
- **`handle_user_chat(message)`**: Handles a user chat message, responds, and updates settings if necessary.
- **`handle_agent_interaction(partner_agent_id)`**: Manages the interaction between two agents.
- **`AgentChatModule.__init__(db, agent_id, model, chat_history)`**: Initializes the AgentChatModule.
- **`AgentChatModule.forward(prompt, settings_context)`**: Generates a response based on the prompt and settings context.
- **`RelevanceFixer.forward(prompt, settings_context, retrieved_memories, max_retries)`**: Ensures the response is relevant to the prompt and retrieved memories, retrying if necessary.
- **`RelevanceChecker.forward(prompt, response, retrieved_memories)`**: Validates the relevance of a response.
- **`UserChatModule.forward(prompt, settings_context)`**: Handles casual chat with the user.
- **`SettingsUpdateModule.__init__(db)`**: Initializes the SettingsUpdateModule with the database object.
- **`SettingsUpdateModule.forward(setting_suggestion, old_settings)`**: Generates new settings based on user suggestions.
- **`SettingsUpdateModule.update_in_context_prompt(agent_id, changes_prompt)`**: Updates the in-context prompt with new settings.
- **`ChatHistorySummarizer.forward(home_agent_id, chat_history_list)`**: Summarizes the chat history.

## Running an Interaction

To run an interaction between agents:

1. **Initialize the network and agents**:
   - Create or retrieve a network and initialize agents.

2. **Set up agent memory**:
   - Add relevant data to the agents' memories.

3. **Handle agent interaction**:
   - Use the `handle_agent_interaction` method to facilitate the conversation between agents.

## Primary Functions and Building Blocks

- **Database Management**: Setting up and interacting with Weaviate database for agent and network data storage.
- **Agent Initialization**: Creating and configuring agents with unique IDs and context prompts.
- **Language Model Configuration**: Setting up the language model for agent interactions.
- **User Interaction Handling**: Managing user chats and updating agent settings dynamically.
- **Agent Interaction Handling**: Facilitating conversations between agents and summarizing interactions.
- **Relevance Checking**: Ensuring responses are relevant to the given context and memories.
- **Settings Management**: Updating and managing agent settings based on user inputs.
- **Chat History Summarization**: Summarizing chat history to store meaningful interactions.
