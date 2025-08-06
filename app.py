import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import calendar

# Set page config
st.set_page_config(
    page_title="BFF heatmap",
    page_icon=":bar_chart:",
    layout="wide"
)

# Title and description
# st.title("Heatmap - Fossil fuel share in power generation")

@st.cache_data
def load_your_data(filepath):

    # Option 1: CSV file
    return pd.read_csv(filepath)


# Load data
# Replace load_sample_data() with load_your_data() when you have your actual data
df = load_your_data('generation_data.csv')

# Sidebar for filters
st.sidebar.header("Filters")

# Fuel filter
available_fuels = sorted(df['Fuel'].unique())
selected_fuel = st.sidebar.radio(
    "Select fossil fuel:",
    options=available_fuels,
    index=0
)

# Share_bins filter
available_share_bins = ['<1%', '<10%', '<20%', '<30%', '<40%', '<50%', '<60%', '<70%', '<80%', '<90%']
#sorted(df['Share_bins'].unique())
selected_share_bin = st.sidebar.select_slider(
    "Select fossil fuel share:",
    options=available_share_bins
)


# Country filter
available_countries = sorted(df['Country'].unique())
selected_countries = [st.sidebar.selectbox(
    "Select country:",
    options=available_countries
)]

# Year filter
available_years = sorted(df['Year'].unique())
selected_years = available_years
# selected_years = st.sidebar.multiselect(
#     "Select Years:",
#     options=available_years,
#     default=available_years
# )


# Filter the data
filtered_df = df[
    (df['Fuel'] == selected_fuel) & 
    (df['Share_bins'] == selected_share_bin) &
    (df['Year'].isin(selected_years)) &
    (df['Country'].isin(selected_countries))
]

# Check if filtered data is empty
if filtered_df.empty:
    st.warning("⚠️ No data available for the selected filters. Please adjust your selections.")
    st.stop()

# Create pivot table for heatmap (Month vs Year)
# Group by Year and Month, then aggregate Cumulative_Hours values (you can change aggregation method)
heatmap_data = filtered_df.groupby(['Year', 'Month'])['Cumulative_Hours'].sum().reset_index()

# Create a pivot table with Year as rows and Month as columns
pivot_table = heatmap_data.pivot(index='Year', columns='Month', values='Cumulative_Hours')

# Keep NaN values as NaN (don't fill with 0)
matrix = pivot_table.values
years = pivot_table.index.tolist()
months = pivot_table.columns.tolist()


# Create month labels
month_labels = [calendar.month_name[int(m)] for m in months]

# Create the heatmap
fig = go.Figure()

# First heatmap: actual data
fig.add_trace(go.Heatmap(
    z=matrix,
    x=month_labels,
    y=[str(year) for year in years],
    colorscale=[[0, 'red'], [1, 'green']],
    colorbar=dict(title="Hour Values"),
    hoverongaps=False,
    hovertemplate='Month: %{x}<br>Year: %{y}<br>Hour: %{z}<extra></extra>',
    showscale=True,
    zmin=0,
    zmax=744,
    connectgaps=False
))


fig.update_layout(
    title=f'Heatmap representing the number of hours when {selected_fuel} represents less than {selected_share_bin} of total country generation',
    xaxis_title='Month',
    yaxis_title='Year',
    width=800,
    height=600
)


# Display the heatmap
st.plotly_chart(fig, use_container_width=True)
st.text("Source: Beyond Fossil Fuels' elaboration based on ENTSO-E data")


# Display filtered data table
with st.expander("📊 View Filtered Data"):
    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=400
    )

# Data download
csv = filtered_df.to_csv(index=False)
st.download_button(
    label="📥 Download Filtered Data as CSV",
    data=csv,
    file_name=f"filtered_data_{selected_fuel}_{selected_share_bin}.csv",
    mime="text/csv"
)