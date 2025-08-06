import pandas as pd
import zipfile
import os
from pathlib import Path
import io
from country_eic import country_eic

def concatenate_csvs_from_zips(folder_path):
    """
    Extract CSV files from all zip files in a folder and concatenate them into a single DataFrame.
    
    Args:
        folder_path (str): Path to the folder containing zip files
        
    Returns:
        pd.DataFrame: Concatenated DataFrame from all CSV files
    """
    folder_path = Path(folder_path)
    all_dataframes = []
    
    # Find all zip files in the folder
    zip_files = list(folder_path.glob("*.zip"))
    
    if not zip_files:
        print(f"No zip files found in {folder_path}")
        return pd.DataFrame()
    
    print(f"Found {len(zip_files)} zip files")
    
    for zip_file in zip_files:
        print(f"Processing: {zip_file.name}")
        
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                # Get list of files in the zip
                file_list = zip_ref.namelist()
                
                # Find CSV files in the zip
                csv_files = [f for f in file_list if f.lower().endswith('.csv')]
                
                if not csv_files:
                    print(f"  No CSV files found in {zip_file.name}")
                    continue
                
                # Process each CSV file in the zip
                for csv_file in csv_files:
                    print(f"  Extracting: {csv_file}")
                    
                    # Read the CSV file directly from the zip
                    with zip_ref.open(csv_file) as file:
                        # Read the CSV content into a DataFrame
                        csv_content = file.read()
                        df = pd.read_csv(io.BytesIO(csv_content), sep='\t')
                        
                        # Add source information (optional)
                        df['source_zip'] = zip_file.name
                        df['source_csv'] = csv_file
                        
                        all_dataframes.append(df)
                        print(f"    Added {len(df)} rows from {csv_file}")
        
        except zipfile.BadZipFile:
            print(f"  Error: {zip_file.name} is not a valid zip file")
        except Exception as e:
            print(f"  Error processing {zip_file.name}: {str(e)}")
    
    # Concatenate all DataFrames
    if all_dataframes:
        result_df = pd.concat(all_dataframes, ignore_index=True)
        print(f"\nConcatenation complete!")
        print(f"Total rows: {len(result_df)}")
        print(f"Total columns: {len(result_df.columns)}")
        return result_df
    else:
        print("No CSV files were successfully processed")
        return pd.DataFrame()


# Specify your folder path here
folder_path = "data/"

# Concatenate all CSVs from zip files
combined_df = concatenate_csvs_from_zips(folder_path)

# Filter Area Type to be country ('CTY')
combined_df = combined_df[combined_df['AreaTypeCode']=='CTY']
# Get Country names instead of EICs
combined_df = combined_df[combined_df['AreaCode'].map(country_eic).notna()]
combined_df['Country'] = combined_df['AreaCode'].map(country_eic)

# Filter columns we need
combined_df = combined_df[['DateTime','Country','ResolutionCode','ProductionType','ActualGenerationOutput']]

# Calculate fossil, coal and gas generation
fossil_fuels = ['Fossil Gas', 'Fossil Hard coal', 'Fossil Oil', 'Fossil Coal-derived gas', 'Fossil Oil shale', 'Fossil Brown coal/Lignite', 'Fossil Peat']
coal = ['Fossil Hard coal', 'Fossil Coal-derived gas', 'Fossil Brown coal/Lignite']
gas = ['Fossil Gas']

fossil_generation = combined_df[combined_df['ProductionType'].isin(fossil_fuels)].groupby(['DateTime','Country','ResolutionCode']).sum('ActualGenerationOutput').reset_index()
fossil_generation = fossil_generation.rename(columns={'ActualGenerationOutput':'Generation'})
fossil_generation['Fuel'] = 'Fossil fuel' 

coal_generation = combined_df[combined_df['ProductionType'].isin(coal)].groupby(['DateTime','Country','ResolutionCode']).sum('ActualGenerationOutput').reset_index()
coal_generation = coal_generation.rename(columns={'ActualGenerationOutput':'Generation'})
coal_generation['Fuel'] =  'Coal'

gas_generation = combined_df[combined_df['ProductionType'].isin(gas)].groupby(['DateTime','Country','ResolutionCode']).sum('ActualGenerationOutput').reset_index()
gas_generation = gas_generation.rename(columns={'ActualGenerationOutput':'Generation'})
gas_generation['Fuel'] = 'Gas'

#Concate the three tables
df_generation = pd.concat([fossil_generation,coal_generation,gas_generation])

# Calculate total generation
total_generation = combined_df.groupby(['DateTime','Country','ResolutionCode']).sum('ActualGenerationOutput').reset_index()
total_generation = total_generation.rename(columns={'ActualGenerationOutput':'TotalGeneration'})

#Concate the three tables

# Merge both and calculate fossil share
df_generation = total_generation.merge(df_generation,how='left')
df_generation['Generation'].fillna(0, inplace = True)
df_generation['Fuel'].fillna('Fossil fuel', inplace = True)

df_generation['Share'] = df_generation['Generation']/df_generation['TotalGeneration']*100

# Get Month and year from DateTime, and get the amount of hour associated to each entry
df_generation['DateTime'] = pd.to_datetime(df_generation['DateTime'])
df_generation['Hour'] = df_generation['ResolutionCode'].apply(
    lambda x: 0.25 if x == 'PT15M' else (0.5 if x == 'PT30M' else 1)
)
df_generation['Year'] = df_generation['DateTime'].dt.year
df_generation['Month'] = df_generation['DateTime'].dt.month

bins = [0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, float('inf')]
labels = ['<1%', '<5%', '<10%', '<15%', '<20%', '<25%', '<30%', '<35%', '<40%', '<45%', '<50%', '<55%', '<60%', '<65%', '<70%', '<75%', '<80%', '<85%', '<90%', '<95%', '>=95%']

# Classify to discrete categories
df_generation['Share_bins'] = pd.cut(df_generation['Share'], 
                                   bins=bins, 
                                   labels=labels, 
                                   include_lowest=True)

# Convert to categorical if not already
df_generation['Share_bins'] = df_generation['Share_bins'].astype('category')
df_generation['Fuel'] = pd.Categorical(df_generation['Fuel'], ['Coal','Gas','Fossil fuel'])

result = df_generation.groupby(['Year', 'Month', 'Country','Fuel', 'Share_bins'],observed=False)['Hour'].sum().reset_index()


result = result.sort_values(['Year', 'Month', 'Country', 'Fuel', 'Share_bins'])
result['Cumulative_Hours'] = result.groupby(['Year', 'Month', 'Country', 'Fuel'])['Hour'].cumsum()

result.to_csv("share_of_generation_monthly2.csv",index=False)