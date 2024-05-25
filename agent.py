import os
import dspy
import functools
from datetime import datetime, timezone
from dotenv import load_dotenv
import weaviate
from weaviate.exceptions import WeaviateBaseError
from dspy.retrieve.weaviate_rm import WeaviateRM
from dbObject import dbObject

class Agent:
    def __init__(self, network_id, agent_id=None):
        self.db = dbObject()
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

    def _setup_language_model(self):
        self.turbo = dspy.OpenAI(model="gpt-3.5-turbo", max_tokens=2000, model_type="chat", temperature=0.8) 
        dspy.settings.configure(lm=self.turbo)
        print("Language model configured successfully.")

######################## USER CHAT ########################

    def handle_user_chat(self, message):
        user_response = self.user_chat_module(prompt=message, settings_context=self.settings_context)
        
        if "update_command" in user_response:
            settings_suggestion = user_response["update_command"]

            print(settings_suggestion)  
            try:
                update_status = self.settings_update_module.update_in_context_prompt(agent_id=self.agent_id, changes_prompt=settings_suggestion)
                return f"{user_response['answer']}\nMemory update status: {update_status['update_status']}"
            except Exception as e:
                print(f"Error updating settings: {e}") 
                return f"Error updating settings: {str(e)}"
        else:
            return user_response["answer"]
        
######################### AGENTS CHAT ########################
        
    def handle_agent_interaction(self, partner_agent_id):
        home_agent_model = dspy.OpenAI(model="gpt-3.5-turbo", max_tokens=2000, model_type="chat", temperature=0.8)
        away_agent_model = dspy.OpenAI(model="gpt-3.5-turbo", max_tokens=2000, model_type="chat", temperature=0.8)

        home_agent = AgentChatModule(self.db, self.agent_id, home_agent_model)
        away_agent = AgentChatModule(self.db, partner_agent_id, away_agent_model)

        init_prompt = "Hey, talk to me"
        
        for i in range(5):
            if i == 0:
                home_response = home_agent.forward(prompt=init_prompt, settings_context=self.settings_context)
                away_response = away_agent.forward(prompt=home_response['answer'], settings_context=self.settings_context)
            else:
                home_response = home_agent.forward(prompt=away_response['answer'], settings_context=self.settings_context)
                away_response = away_agent.forward(prompt=home_response['answer'], settings_context=self.settings_context)

            print(f"Round {i+1}: Home agent response: {home_response['answer']}")
            print(f"Round {i+1}: Away agent response: {away_response['answer']}")

########################## DSPY CLASSES ##########################
           

######################### AGENT CHAT MODULE ########################
class AgentChatModule(dspy.Module):
    class AgentChatSignature(dspy.Signature):
        """
        Your task is to exchange information with another agent, following the instructions provided. Do not make up any information or experiences.
        Ask your partner about information from your memory retrieval. 
        Find commonalities and relevant things in your memory retrieval based on what your partner asks you.
        """
        settings_context = dspy.InputField(desc="Instructions for the agent to follow during social interactions.")
        prompt = dspy.InputField()
        memory_retrieval = dspy.OutputField(desc="Retrieved memory based on the prompt.")
        answer = dspy.OutputField(desc="A response to the other agent.")

    def __init__(self, db, agent_id: str, model: dspy.OpenAI):
        self.db = db
        self.agent_id = agent_id
        self.model = model

    # creates response (with some guidance from relevance check)
    def forward(self, prompt, settings_context):
        ###### memories -> context
        retrieved_memories = str(self.db.get_agent_memory(self.agent_id, prompt))
        relevance_fixer = RelevanceFixer()

        # Use RelevanceFixer to get a relevant response
        response = relevance_fixer(
            prompt=prompt,
            settings_context=settings_context,
            retrieved_memories=retrieved_memories,
            max_retries=3
        )

        return response


########################## METRIC CHECKERS ##########################

class RelevanceFixer(dspy.Module):
    class RelevanceFixerSignature(dspy.Signature):
        """
        Attempt to generate a relevant response based on the prompt and retrieved memories. If the initial response is not relevant, retry up to max_retries times.
        """
        settings_context = dspy.InputField(desc="Instructions for the agent to follow during social interactions.")
        prompt = dspy.InputField()
        retrieved_memories = dspy.InputField()
        max_retries = dspy.InputField(desc="Maximum number of retries.")
        answer = dspy.OutputField(desc="A response to the prompt.")

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
                ))(
                    settings_context=settings_context,
                    prompt=prompt,
                    memory_retrieval=retrieved_memories
                ).answer

            is_relevant = relevance_checker(
                prompt=prompt,
                response=initial_response,
                retrieved_memories=retrieved_memories
            )

            if is_relevant:
                return {"answer": initial_response}
            else:
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1} failed. Retrying...")
                else:
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


####################### USER CHAT MODULES (AND SIGS) ############################

# Handles casual chat with the user
class UserChatModule(dspy.Module):
    class UserChatSignature(dspy.Signature):
        """Your task is to be a casual texting buddy of the user, texting with abbreviations and common slang. You can ask questions, provide answers, or just chat. You must follow the settings/instructions given to you."""
        settings_context = dspy.InputField(desc="Instructions for the agent to follow during social interactions.")
        prompt = dspy.InputField()
        answer = dspy.OutputField(desc="A response to the user.")
        # Optional output for updating settings
        update_command = dspy.OutputField(desc="Command to update settings, if detected. Optional")
    
    def forward(self, prompt, settings_context):
        # Logic to detect update command in the user's message
        if "update your settings" in prompt.lower():
            return {"answer": f"Updating settings", "update_command": prompt}
        else:
            # Default casual chat response
            response = dspy.ChainOfThought(self.UserChatSignature)(settings_context=settings_context, prompt=prompt).answer
            return {"answer": response}

# Handles updating the agent's in-context prompt based on the settings suggestion
class SettingsUpdateModule(dspy.Module):
    class SettingsUpdateSignature(dspy.Signature):
        """Generate instructions/settings for an AI agent based on a user's suggestion, combining the context of the old prompt with the new suggestion, elaborate and write an instructions paragraph based on the settings presentsed."""
        setting_suggestion = dspy.InputField()
        old_settings = dspy.InputField()
        new_settings = dspy.OutputField(desc="New in-context prompt generated based on the setting suggestion.")
    
    def __init__(self, db):
        super().__init__()
        self.db = db

    def forward(self, setting_suggestion, old_settings):
        # Logic to merge new settings with old settings
        try:
            new_settings = f"{old_settings}\n{setting_suggestion}"
            self.db._assert_utf8(new_settings)
            return {"new_settings": new_settings}
        except Exception as e:
            raise ValueError(f"Failed to merge settings: {e}")

    def update_in_context_prompt(self, agent_id, changes_prompt):
        # Retrieve the old in-context prompt
        try:
            old_in_context_prompt = self.db.get_in_context_prompt(agent_id)
            # print(f"Old in-context prompt: {old_in-context prompt}")  # Debugging output
        except Exception as e:
            print(f"Error retrieving old in-context prompt: {e}")
            return {"update_status": f"Failed: {str(e)}"}

        # Generate the new in-context prompt based on the changes
        try:
            prediction = self.forward(changes_prompt, old_in_context_prompt)
            new_in_context_prompt = prediction.get('new_settings', old_in_context_prompt)
            print(new_in_context_prompt)
        except Exception as e:
            print(f"Error generating new in-context prompt: {e}")
            return {"update_status": f"Failed: {str(e)}"}

        # Update the in-context prompt in the database
        try:
            self.db.update_in_context_prompt(agent_id, new_in_context_prompt)
            return {"update_status": "Success"}
        except Exception as e:
            print(f"Error updating in-context prompt: {e}")
            return {"update_status": f"Failed: {str(e)}"}
