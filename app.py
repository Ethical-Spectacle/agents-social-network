from flask import Flask, request, jsonify, stream_with_context, Response
from agentObject import Agent
from flask_cors import CORS
from dbObject import dbObject

app = Flask(__name__)
CORS(app)

# this needs to be passed in by the request but for now it's just for testing user interactions
# to run a user chat, pyhton3 app.py, then python3 userChatDemo.py
agent = Agent(network_id="grapevine-test", agent_id="1")

@app.route('/')
def index():
    return "This is SADIE API"

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '')

    def generate():
        response = agent.handle_user_chat(question)
        for char in response:
            yield char
        yield '\n'

    return Response(stream_with_context(generate()), content_type='text/event-stream')

@app.route('/interaction', methods=['POST'])
def interaction():
    data = request.json
    partner_agent_id = data.get('partner_agent_id', '')

    def generate():
        response = agent.handle_agent_interaction(partner_agent_id)
        for char in response:
            yield char
        yield '\n'

    return Response(stream_with_context(generate()), content_type='text/event-stream')

# just added this, it's direct, no agent in the middle to update the agent's context prompt (included at the begining of every prompt).
# post agent_id, and new_instructions
@app.route('/update_instructions', methods=['POST'])
def update_instructions():
    data = request.json
    new_instructions = data.get('new_nstructions', None)
    agent_id = data.get('agent_id', None)

    db_obj = dbObject()
    db_obj.update_instructions(agent_id=agent_id, new_instructions=new_instructions)

    return jsonify({'message': 'Instructions updated :)'})

# post agent_id, and new_toxicity_settings
@app.route('/update_toxicity_settings', methods=['POST'])
def update_toxicity_settings():
    data = request.json
    new_toxicity_settings = data.get('new_toxicity_settings', None)
    agent_id = data.get('agent_id', None)

    db_obj = dbObject()
    db_obj.update_toxicity_settings(agent_id=agent_id, new_toxicity_settings=new_toxicity_settings)

    return jsonify({'message': 'Instructions updated :)'})

if __name__ == "__main__":
    app.run(debug=True, port=3000)