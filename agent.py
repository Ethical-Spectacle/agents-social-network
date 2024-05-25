import os
import dspy
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

    def _setup_language_model(self):
        self.turbo = dspy.OpenAI(model="gpt-3.5-turbo", max_tokens=2000, model_type="chat")
        dspy.configure(lm=self.turbo)
        print("Language model configured successfully.")

    def handle_user_chat(self, message):
        instructions = self.db.get_in_context_prompt(self.agent_id) # move this to flask endpoint later so it only happens once
        user_response = self.user_chat_module(prompt=message, settings_context=instructions)
        
        if "update_command" in user_response:
            settings_suggestion = user_response["update_command"]

            print(settings_suggestion)  # Debugging output
            try:
                update_status = self.settings_update_module.update_in_context_prompt(agent_id=self.agent_id, changes_prompt=settings_suggestion)
                return f"{user_response['answer']}\nMemory update status: {update_status['update_status']}"
            except Exception as e:
                print(f"Error updating settings: {e}")  # Debugging output
                return f"Error updating settings: {str(e)}"
        else:
            return user_response["answer"]

###################### DSPy CUSTOM CLASSES ############################

# Handles casual chat with the user
class UserChatModule(dspy.Module):
    class UserChatSignature(dspy.Signature):
        """Your task is to be a casual texting buddy of the user, texting with abbreviations and common slang. You can ask questions, provide answers, or just chat. You must follow the settings/instructions given to you."""
        settings_context = dspy.InputField(desc="Instructions for the agent to follow during social interactions.")
        prompt = dspy.InputField()
        answer = dspy.OutputField(desc="A response to the user.")
        # Optional output for updating settings
        update_command = dspy.OutputField(desc="Command to update settings, if detected.", optional=True)
    
    def forward(self, prompt, settings_context):
        # Concatenate instructions with the prompt
        full_prompt = f"""
            Instructions: {settings_context}\n
            User interaction prompt: {prompt}
            """
        # print(f"Full prompt: {full_prompt}")  # Debugging output
        
        # Logic to detect update command in the user's message
        if "update your settings" in prompt.lower():
            return {"answer": f"Updating settings", "update_command": prompt}
        else:
            # Default casual chat response
            response = dspy.ChainOfThought(self.UserChatSignature)(settings_context=settings_context, prompt=full_prompt).answer
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
            # print(f"Old in-context prompt: {old_in_context_prompt}")  # Debugging output
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
