import pandas as pd
import matplotlib.pyplot as plt
import ace_tools as tools

def process_temperature_data(file_path):
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Convert Timestamp column to datetime
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    # Display table
    tools.display_dataframe_to_user(name="Temperature Validation Data", dataframe=df)
    
    # Generate the graph
    plt.figure(figsize=(10, 5))
    plt.plot(df['Timestamp'], df['Multimeter Temp (C)'], marker='o', linestyle='-', label='Multimeter Temp (C)')
    plt.axhline(y=240, color='r', linestyle='--', label='Max Limit (240°C)')
    plt.axhline(y=25, color='g', linestyle='--', label='Min Limit (25°C)')
    plt.xlabel('Timestamp')
    plt.ylabel('Temperature (°C)')
    plt.title('Multimeter Temperature Readings')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

# Example usage
file_path = "temperature_log.csv"  # Ensure this file exists before running
process_temperature_data(file_path)
