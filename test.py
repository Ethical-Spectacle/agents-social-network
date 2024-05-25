import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import os
import dspy
from agent import Agent, UserChatModule, RAGModule, MemoryUpdateModule
from dbObject import dbObject

class TestAgentSystem(unittest.TestCase):

    @patch('dbObject.weaviate.Client')
    def setUp(self, MockClient):
        self.mock_client = MockClient.return_value
        self.db = dbObject()
        self.network_id = 'test-network'
        self.agent = Agent(network_id=self.network_id)

    def test_create_agent(self):
        agent_id = self.agent.agent_id
        self.assertIsNotNone(agent_id)
        print(f"[TEST CREATE AGENT] Agent created successfully with ID: {agent_id}")

    def test_update_in_context_prompt(self):
        agent_id = self.agent.agent_id
        new_prompt = "This is a new in-context prompt for testing."
        self.db.update_in_context_prompt(agent_id, new_prompt)
        print(f"[TEST UPDATE PROMPT] In-context prompt updated for agent ID: {agent_id}")

        # Mock the response from the Weaviate client
        self.mock_client.query.get.return_value.with_bm25.return_value.do.return_value = {
            'data': {
                'Get': {
                    f'AgentData_{agent_id}': [
                        {'dataContent': new_prompt, 'createdAt': datetime.now(timezone.utc).isoformat()}
                    ]
                }
            }
        }

        prompt_response = self.db.get_in_context_prompt(agent_id)
        self.assertIsNotNone(prompt_response)
        retrieved_prompt = prompt_response['data']['Get'][f'AgentData_{agent_id}'][0]['dataContent']
        self.assertEqual(retrieved_prompt, new_prompt)
        print(f"[TEST UPDATE PROMPT] In-context prompt retrieved successfully: {retrieved_prompt}")

    def test_handle_user_chat_update_settings(self):
        message = "update your settings to be more responsive."
        with patch.object(dspy.ChainOfThought, '__call__', return_value={'output': {'answer': "Generated prompt based on new setting"}}):
            response = self.agent.handle_user_chat(message)
            self.assertIn("Updating settings to include: to be more responsive.", response)
            self.assertIn("Memory update status: Success", response)
            print(f"[TEST UPDATE SETTINGS] Response: {response}")

    def test_handle_user_chat_normal_message(self):
        message = "Hello, how are you?"
        response = self.agent.handle_user_chat(message)
        self.assertNotIn("update your settings", response.lower())
        print(f"[TEST NORMAL CHAT] Response: {response}")

    def test_add_agent_data(self):
        agent_id = self.agent.agent_id
        data_content = "This is a test memory entry."
        self.db.add_agent_data(agent_id, data_content, toxicity_flag=False)
        print(f"[TEST ADD MEMORY] Memory added for agent ID: {agent_id}")

        # Mock the response from the Weaviate client
        self.mock_client.query.get.return_value.do.return_value = {
            'data': {
                'Get': {
                    f'AgentData_{agent_id}': [
                        {'dataContent': data_content, 'createdAt': datetime.now(timezone.utc).isoformat(), 'toxicityFlag': False}
                    ]
                }
            }
        }

        memory_response = self.db.get_agent_memory(agent_id)
        self.assertIsNotNone(memory_response)
        retrieved_memory = memory_response['data']['Get'][f'AgentData_{agent_id}'][0]['dataContent']
        self.assertEqual(retrieved_memory, data_content)
        print(f"[TEST ADD MEMORY] Memory entry retrieved successfully: {retrieved_memory}")

if __name__ == '__main__':
    unittest.main()
