import requests
import json
from tabulate import tabulate
import pandas as pd

def get_model_prices():
    # Fetch data from the URL
    url = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
    response = requests.get(url)
    data = response.json()
    
    # Create a list to store the model information
    models_list = []
    
    for model_name, details in data.items():
        # Skip the sample_spec entry
        if model_name == "sample_spec":
            continue
            
        # Get the cost information
        input_cost = details.get('input_cost_per_token', 0)
        output_cost = details.get('output_cost_per_token', 0)
        total_cost = input_cost + output_cost
        
        # Get the context window information
        max_tokens = details.get('max_tokens', 'N/A')
        provider = details.get('litellm_provider', 'N/A')
        mode = details.get('mode', 'N/A')
        
        # Add to our list
        models_list.append({
            'Model': model_name,
            'Provider': provider,
            'Mode': mode,
            'Total Cost per Token': total_cost,
            'Input Cost': input_cost,
            'Output Cost': output_cost,
            'Max Tokens': max_tokens
        })
    
    # Convert to DataFrame and sort by total cost
    df = pd.DataFrame(models_list)
    df = df.sort_values('Total Cost per Token')
    
    # Format the cost columns to scientific notation
    for col in ['Total Cost per Token', 'Input Cost', 'Output Cost']:
        df[col] = df[col].apply(lambda x: f"{x:.2e}" if isinstance(x, (int, float)) else x)
    
    # Print the table
    print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))

if __name__ == "__main__":
    get_model_prices()
