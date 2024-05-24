### dbObject:

 - __init__()
 - _ensure_base_classes_exist()
    - contains schema for network class, and agent custom classes
 - create_network(network_id, name, description)
 - create_agent(agent_id, name, network_id)
    - _create_agent_class(self, agent_id)
 - add_agent_data(agent_id, data_id, data_content, toxicity_flag=False)
    - defaults toxicity flag false
 - get_agent_data(agent_id)

