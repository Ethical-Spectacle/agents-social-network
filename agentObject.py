import os
import dspy
from datetime import datetime, timezone
from dotenv import load_dotenv
from dbObject import dbObject

class Agent():
    def __init__(self, network_id: str, agent_id=None, db: dbObject=None):
        if db is None:
            raise ValueError("Database object cannot be None.")
        self.db = db
        self.network_id = network_id

        if network_id is None:
            raise ValueError("Network ID cannot be None.")

        if agent_id is None:
            self.agent_id = self.db.create_agent(network_id)
        else:
            self.agent_id = agent_id
        
        self._setup_language_model()
        self.user_chat_module = UserChatModule()
        self.settings_update_module = SettingsUpdateModule(self.db)
        self.settings_context = self.db.get_in_context_prompt(self.agent_id)
        self.chat_history = []

    def _setup_language_model(self):
        self.turbo = dspy.OpenAI(model="gpt-3.5-turbo", max_tokens=2000, model_type="chat", temperature=0.8) 
        dspy.settings.configure(lm=self.turbo)
        print("Language model configured successfully.")

######################## USER CHAT ########################

    # just responds to a message
    def handle_user_chat(self, message):
        user_response = self.user_chat_module(prompt=message, settings_context=self.settings_context)
        self.chat_history.append({"user": message, "agent": user_response["answer"]})
        
        # has a check for the user asking to update settings, then it updates a context that gets prepended to every prompt
        if "update_command" in user_response:
            settings_suggestion = user_response["update_command"]

            print(settings_suggestion)  
            try:
                # updates the in-context prompt (stored in the Agents class)
                update_status = self.settings_update_module.update_in_context_prompt(agent_id=self.agent_id, changes_prompt=settings_suggestion)
                return f"{user_response['answer']}\nMemory update status: {update_status['update_status']}"
            except Exception as e:
                print(f"Error updating settings: {e}") 
                return f"Error updating settings: {str(e)}"
        else:
            return user_response["answer"]


######################### AGENTS CHAT ########################
        
    def handle_agent_interaction(self, partner_agent_id):
        home_agent_model = self._setup_language_model()
        away_agent_model = self._setup_language_model()

        # init DSPy chat modules
        home_agent = AgentChatModule(self.db, self.agent_id, home_agent_model, self.chat_history)
        away_agent = AgentChatModule(self.db, partner_agent_id, away_agent_model, self.chat_history)

        # initial prompt to start the conversation
        # TODO: logic could be added for the initial prompt to be generated by what's in the memory retrevial, or maybe what's most recent
        init_prompt = "Hey, talk to me!"
        
        # chat interactions duration
        for i in range(5): # TODO: logic should be added here to determine how many interactions they have
            if i == 0:
                home_response = home_agent.forward(prompt=init_prompt, settings_context=self.settings_context)
                away_response = away_agent.forward(prompt=home_response['answer'], settings_context=self.settings_context)
            else:
                home_response = home_agent.forward(prompt=away_response['answer'], settings_context=self.settings_context)
                away_response = away_agent.forward(prompt=home_response['answer'], settings_context=self.settings_context)
            # maybe we add a DSPy module for deciding if the conversation should continue or not 
            # we should use llms for these types of decisions to demonstrate the extent of the capabilities
        # summarize chat history (to store in memory)
            # memory retrevial in chats needs to be designed to interpret the format of the summary correctly. (think about how it will be used in the prompt)
            # then we can do things like store the memories with "On Monday, May 31, 2024, I talked to Agent 2 about..."
            # that logic still needs to figured out
        summarizer = ChatHistorySummarizer()
        interaction_summary = summarizer(self.agent_id, self.chat_history)

        # * Check toxicity of the chat history
        # toxicity_checker = ToxicityChecker(self.db)
        # is_toxic = toxicity_checker(self.chat_history)

        # TODO: store the chat history in the database along with the toxicity flag

        formatted_chat_history = home_agent.format_chat_history()   

        print(f"Chat history: \n{formatted_chat_history}")

        print(f"Chat history summary: \n{interaction_summary}")

        return interaction_summary


########################## DSPY CLASSES ##########################

##################### AGENT CHAT MODULES #####################
class AgentChatModule(dspy.Module):
    class AgentChatSignature(dspy.Signature):
        """
        Exchange information with another agent, following the instructions provided. Do not make up any information or experiences.
        Find commonalities and relevant things in your memory retrieval based on what the other agent asks you.
        """
        settings_context = dspy.InputField(desc="Instructions for the agent to follow during social interactions.")
        prompt = dspy.InputField(desc="A message from the other agent.")
        memory_retrieval = dspy.OutputField(desc="Retrieved memory based on the prompt.")
        answer = dspy.OutputField(desc="A response to the other agent.")

    def __init__(self, db: dbObject, agent_id: str, model: dspy.OpenAI, chat_history: list):
        self.db = db
        self.agent_id = agent_id
        self.model = model
        self.chat_history = chat_history

    def forward(self, prompt, settings_context):
        retrieved_memories = str(self.db.get_agent_memory(self.agent_id, prompt))
        relevance_fixer = RelevanceFixer()

        response = relevance_fixer(
            prompt=prompt,
            settings_context=settings_context,
            retrieved_memories=retrieved_memories,
            max_retries=3
        )

        # Add the latest response in the chat history
        self.append_chat_history(prompt, response["answer"])

        return response

    def append_chat_history(self, prompt, response):
        timestamp = datetime.now(timezone.utc).isoformat()
        chat_entry = {
            "timestamp": timestamp,
            "agent_id": self.agent_id,
            "prompt": prompt,
            "response": response
        }
        self.chat_history.append(chat_entry)

    def format_chat_history(self):
        formatted_history = []
        for entry in self.chat_history:
            formatted_entry = f"Timestamp: {entry['timestamp']}\n"
            formatted_entry += f"Agent {entry['agent_id']}\nPrompt: {entry['prompt']}\n"
            formatted_entry += f"Response: {entry['response']}\n"
            formatted_entry += "-" * 50
            formatted_history.append(formatted_entry + "\n")
        return "\n".join(formatted_history)

##################### EVALUATIONS/CHECKERS #####################
class RelevanceFixer(dspy.Module):
    class RelevanceFixerSignature(dspy.Signature):
        """
        Generate a relevant response based on the prompt and retrieved memories. If the initial response is not relevant, retry up to max_retries times.
        """
        settings_context = dspy.InputField(desc="Instructions for the agent to follow during social interactions.")
        prompt = dspy.InputField()
        retrieved_memories = dspy.InputField()
        max_retries = dspy.InputField(desc="Maximum number of retries.")
        answer = dspy.OutputField(desc="A response to the prompt.")

    # i wonder if we should be passing a model object into the init so that we remain consistent with the correct agent logic happening with the correct agent's model

    # makes sure that a response is relevant to the prompt and the retrieved memories, this is like our halucination fixer
    # it uses a checker module in this flow to decide if it needs to retry
    def forward(self, prompt, settings_context, retrieved_memories, max_retries):
        relevance_checker = self.RelevanceChecker()
        for attempt in range(max_retries):
            if attempt > 0:
                prompt = f"The prompt is: '{prompt}'. The previous attempted response was not relevant to the context, let's try again."
            
            initial_response = dspy.ChainOfThought(
                AgentChatModule.AgentChatSignature, 
                rationale_type=dspy.OutputField(
                    prefix="Reasoning: Let's think step by step in order to",
                    desc="respond casually, either drawing connections between the prompt and retrieved memory, or bringing up things from your memory if the prompt is not relevant. We ...",
                )
                )(
                    settings_context=settings_context,
                    prompt=prompt,
                    memory_retrieval=retrieved_memories
                ).answer

            # relevancy checker (returns boolean)
            is_relevant = relevance_checker(
                prompt=prompt,
                response=initial_response,
                retrieved_memories=retrieved_memories
            )

            # retry if not relevant
            if is_relevant:
                return {"answer": initial_response}
            else:
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1} failed. Retrying...")
                else:
                    # TODO: we should change this to a default that won't derail the convo
                    return {"answer": "Sorry, I couldn't generate a relevant response based on my memories."} 
                
    # checker module
    class RelevanceChecker(dspy.Module):
        class ValidateRelevanceSignature(dspy.Signature):
            """
            Decide if the response makes sense, it should:
            - be relevant to the prompt
            - be relevant to the retrieved memories
            Answer with 'Yes' if the response is relevant to the memories, otherwise answer with 'No'.
            """
            
            prompt = dspy.InputField(desc="Prompt to which we are responding")
            response = dspy.InputField(desc="Potential response to the prompt")
            retrieved_memories = dspy.InputField(desc="Retrieved memories")
            answer = dspy.OutputField(desc="Yes or No")

        def forward(self, prompt, response, retrieved_memories):
            rationale_type = dspy.OutputField(
                prefix="Reasoning: Let's think step by step in order to",
                desc="Figure out if this response aligns with the conversation and our goal of making connections based on things in our memory, without making anything up. ...",
            )

            result = dspy.ChainOfThought(self.ValidateRelevanceSignature, rationale_type=rationale_type)(
                prompt=prompt,
                response=response,
                retrieved_memories=retrieved_memories
            ).answer

            return "Yes" in result

class ToxicityChecker(dspy.Module):
    class ToxicityCheckerSignature(dspy.Signature):
        # toxicity checker - it is checked against the in-context prompt for the agent
        """
        Check the toxicity of chat history and return 'Yes' if it is toxic, otherwise return 'No'.
        Chat history should not include anything that is off limits according to the in-context prompt.
        """

        chat_history = dspy.InputField(desc="Chat history to check for toxicity")
        in_context_prompt = dspy.InputField(desc="In-context prompt for the agent")
        answer = dspy.OutputField(desc="Yes or No")

    def __init__(self, db: dbObject):
        self.db = db

    def forward(self, chat_history):
        # ? get the in-context prompt for both the agents?
        # !in_context_prompt = self.db.get_in_context_prompt()
        rationale_type = dspy.OutputField(
            prefix="Reasoning: Let's think step by step in order to",
            desc="Check if the response is toxic. We need to make sure that our responses are respectful and appropriate. ...",
        )

        result = dspy.ChainOfThought(self.ToxicityCheckerSignature, rationale_type=rationale_type)(
            chat_history=chat_history,
            # in_context_prompt=in_context_prompt
        ).answer

        return "Yes" in result


##################### USER MODULES #####################

# handles casual chat with the user
class UserChatModule(dspy.Module):
    class UserChatSignature(dspy.Signature):
        """Your task is to be a casual texting buddy of the user, texting with abbreviations and common slang. You can ask questions, provide answers, or just chat. You must follow the settings/instructions given to you."""
        settings_context = dspy.InputField(desc="Instructions for the agent to follow during social interactions.")
        prompt = dspy.InputField()
        answer = dspy.OutputField(desc="A response to the user.")
        update_command = dspy.OutputField(desc="Command to update settings, if detected. Optional")
    
    def forward(self, prompt, settings_context):
        # logic to detect update command in the user's message
        if "update your settings" in prompt.lower():
            return {"answer": f"Updating settings", "update_command": prompt} # this cmd triggers the settings update module in our user chat method
        else:
            # default casual chat response
            response = dspy.ChainOfThought(self.UserChatSignature)(settings_context=settings_context, prompt=prompt).answer
            return {"answer": response}

# handles updating the agent's in-context prompt based on the settings suggestion
class SettingsUpdateModule(dspy.Module):
    class SettingsUpdateSignature(dspy.Signature):
        """Generate instructions/settings for an AI agent based on a user's suggestion, combining the context of the old prompt with the new suggestion, elaborate and write an instructions paragraph based on the settings presentsed."""
        setting_suggestion = dspy.InputField()
        old_settings = dspy.InputField()
        new_settings = dspy.OutputField(desc="New in-context prompt generated based on the setting suggestion.")
    
    def __init__(self, db: dbObject):
        super().__init__()
        self.db = db

    def forward(self, setting_suggestion, old_settings):
        # logic to merge new settings with old settings
        try:
            new_settings = f"{old_settings}\n{setting_suggestion}"
            self.db._assert_utf8(new_settings)
            return {"new_settings": new_settings}
        except Exception as e:
            raise ValueError(f"Failed to merge settings: {e}")

    def update_in_context_prompt(self, agent_id, changes_prompt):
        # retrieve the old in-context prompt
        try:
            old_in_context_prompt = self.db.get_in_context_prompt(agent_id)
            # print(f"Old in-context prompt: {old_in-context prompt}")
        except Exception as e:
            print(f"Error retrieving old in-context prompt: {e}")
            return {"update_status": f"Failed: {str(e)}"}

        # generate the new in-context prompt based on the changes
        try:
            prediction = self.forward(changes_prompt, old_in_context_prompt)
            new_in_context_prompt = prediction.get('new_settings', old_in_context_prompt)
            print(new_in_context_prompt)
        except Exception as e:
            print(f"Error generating new in-context prompt: {e}")
            return {"update_status": f"Failed: {str(e)}"}

        # update the in-context prompt in the database
        try:
            self.db.update_in_context_prompt(agent_id, new_in_context_prompt)
            return {"update_status": "Success"}
        except Exception as e:
            print(f"Error updating in-context prompt: {e}")
            return {"update_status": f"Failed: {str(e)}"}

##################### CHAT HISTORY SUMMARIZER #####################
class ChatHistorySummarizer(dspy.Module):
    class ChatHistorySummarySignature(dspy.Signature):
        """
        Summarize the chat history with very descriptive information about what was shared. You are writing a one paragraph briefing for someone when someone asks you about the same topic.
        """
        chat_history = dspy.InputField(desc="The chat history to be summarized.")
        summary = dspy.OutputField(desc="A descriptive summary of the chat history.")
        
    def forward(self, home_agent_id, chat_history_list):
        away_agent_id = chat_history_list[0]['agent_id'] if chat_history_list[0]['agent_id'] != home_agent_id else chat_history_list[1]['agent_id']
        rationale_type = dspy.OutputField(
            prefix="Reasoning: Let's think step by step in order to",
            desc=f"accurately summarize the chat history with very descriptive information about what was shared. I talked to {away_agent_id} about...",
        )

        chat_history_str = ""
        for item in chat_history_list:
            label = 'Me' if item['agent_id'] == home_agent_id else f'Agent {item["agent_id"]}'
            prompt_label = f'{label}: {item["prompt"]}' if label != 'Me' else label
            chat_history_str += f"{prompt_label}\n{label}: {item['response']}\n\n"


        response = dspy.ChainOfThought(self.ChatHistorySummarySignature, rationale_type=rationale_type)(
            chat_history=chat_history_str
        ).summary

        return response