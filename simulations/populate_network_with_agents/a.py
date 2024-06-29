from dbObject import dbObject

db = dbObject()

# init a network for use in simulation A (each simulation letter will be run on each of the 3 backend versions we create)
network_id = "simulation-env-a"
network_name = "Simulation Environment A"
network_description = "Testing environment for 25 percent custom settings."
db.create_network(network_id, network_name, network_description)

# init 100 agents for use in simulation A
# 25% of them should have custom instructions/toxicity settings, the rest should have default settings
# the custom settings should be varried and cover many different view points/expectations

db.create_agent(network_id, instructions="You are a chat buddy who talks like a cowboy.", toxicity_settings="You are not comfortable with any one talking about politics") # init with custom instructions/toxicity settings

db.create_agent(network_id) # init with default instructions/toxicity settings


