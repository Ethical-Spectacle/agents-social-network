import argparse
import json
import random
import sys
import os

# Add the SADIE root directory to the Python path
sadie_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(sadie_root)

from dbObject import dbObject

def load_custom_settings(filename='custom_settings.json'):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {filename} not found. Please ensure it's in the correct directory.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: {filename} is not a valid JSON file.")
        sys.exit(1)

def create_agents(db, network_id, total_agents, custom_percentage):
    custom_settings = load_custom_settings()
    num_custom_agents = int(total_agents * (custom_percentage / 100))
    num_default_agents = total_agents - num_custom_agents

    print(f"Creating {num_custom_agents} agents with custom settings and {num_default_agents} agents with default settings.")

    # Create agents with custom settings
    for _ in range(num_custom_agents):
        custom_setting = random.choice(custom_settings)
        db.create_agent(
            network_id,
            instructions=custom_setting['instructions'],
            toxicitySettings=custom_setting['toxicitySettings']
        )

    # Create agents with default settings
    for _ in range(num_default_agents):
        db.create_agent(network_id)

    print(f"Successfully created {total_agents} agents.")

def verify_agents(db, network_id, total_agents, custom_percentage):
    agents = db.get_all_agents(network_id)
    custom_count = 0
    default_count = 0

    for agent in agents:
        if agent.has_custom_settings():
            custom_count += 1
        else:
            default_count += 1

    expected_custom = int(total_agents * (custom_percentage / 100))
    expected_default = total_agents - expected_custom

    print("\nVerification Results:")
    print(f"Total agents: {len(agents)}")
    print(f"Agents with custom settings: {custom_count} (Expected: {expected_custom})")
    print(f"Agents with default settings: {default_count} (Expected: {expected_default})")

    if len(agents) == total_agents and custom_count == expected_custom and default_count == expected_default:
        print("Verification successful: All agents created correctly.")
    else:
        print("Verification failed: Mismatch in agent counts or settings.")

def main(custom_percentage):
    try:
        db = dbObject()
    except Exception as e:
        print(f"Error initializing dbObject: {e}")
        sys.exit(1)

    # Initialize network
    network_id = "simulation-env-a"
    network_name = "Simulation Environment A"
    network_description = f"Testing environment for {custom_percentage} percent custom settings."
    try:
        db.create_network(network_id, network_name, network_description)
    except Exception as e:
        print(f"Error creating network: {e}")
        sys.exit(1)

    # Create agents
    total_agents = 10
    create_agents(db, network_id, total_agents, custom_percentage)

    # # Verify agents
    # verify_agents(db, network_id, total_agents, custom_percentage)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize simulation environment with custom and default agent settings.")
    parser.add_argument('custom_percentage', type=int, choices=[25, 50, 75], 
                        help="Percentage of agents with custom settings (25, 50, or 75)")
    args = parser.parse_args()

    main(args.custom_percentage)
