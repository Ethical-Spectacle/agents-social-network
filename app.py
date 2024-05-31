from flask import Flask, request, jsonify, stream_with_context, Response
from agentObject import Agent

app = Flask(__name__)

# this needs to be passed in by the request but for now it's just for testing user interactions
# to run a user chat, pyhton3 app.py, then python3 userChatDemo.py
agent = Agent(network_id="grapevine-test", agent_id="1")

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

if __name__ == "__main__":
    app.run(debug=True, port=5000)
