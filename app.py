import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import calendar
import os

# Set page config
st.set_page_config(
    page_title="BFF fossil generation heatmap", page_icon=":bar_chart:", layout="wide"
)


@st.cache_data
def load_data(filepath):
    return pd.read_csv(filepath)


# Logo
st.logo(
    "images/BFF.png",
    icon_image="images/BFF-small.png",
)

# Load data
df = load_data("generation_data.csv")
df["Cumulative_Hours"] = round(df["Cumulative_Hours"], 0)

# Sidebar for filters
st.sidebar.title("Heatmap filters")
# Country filter
available_countries = ["Europe average"] + sorted(
    [
        country
        for country in df["Country"].unique()
        if country not in (["Europe average", "United Kingdom", "Ukraine"])
    ]
)
selected_country = st.sidebar.selectbox(
    "Select a country:", options=available_countries, index=1
)

# Fuel filter
available_fuels = ["Coal", "Gas", "Fossil fuel"]  # sorted(df['Fuel'].unique())
selected_fuel = st.sidebar.radio(
    "Select the type of fossil fuel:", options=available_fuels, index=0
)

# Share_bins filter
available_share_bins = ["<1%", "<3%", "<5%", "<10%", "<20%", "<30%", "<40%", "<50%"]
# sorted(df['Share_bins'].unique())
selected_share_bin = st.sidebar.select_slider(
    "Select the fossil fuel share (% of total generation):",
    options=available_share_bins,
)
st.sidebar.info(
    """
    **💡 How to read this heatmap**  

    ▪️ Each square = one month in a given year  
    ▪️ Color shows how many hours fossil fuel use fell below your chosen threshold  

    **🎨 Color scale**  
    - 🟩 Green → More hours below threshold (lower fossil fuel reliance)  
    - 🟥 Red → Fewer hours below threshold (higher fossil fuel reliance)  

    **🕒 Trends over time**  
    Greener tones highlight progress toward cleaner energy.  
    The heatmap shows **monthly patterns** (left → right) and **year-to-year changes** (bottom → top).  
    """
)
# Year filter
available_years = sorted(df["Year"].unique())
selected_years = available_years

# Filter the data
filtered_df = df[
    (df["Fuel"] == selected_fuel)
    & (df["Share_bins"] == selected_share_bin)
    & (df["Year"].isin(selected_years))
    & (df["Country"].isin([selected_country]))
]

# Check if filtered data is empty
if filtered_df.empty:
    st.warning(
        "⚠️ No data available for the selected filters. Please adjust your selections."
    )
    st.stop()

# Create pivot table for heatmap (Month vs Year)
# Group by Year and Month, then aggregate Cumulative_Hours values (you can change aggregation method)
heatmap_data = (
    filtered_df.groupby(["Year", "Month"])["Cumulative_Hours"].sum().reset_index()
)

# Create a pivot table with Year as rows and Month as columns
pivot_table = heatmap_data.pivot(
    index="Year", columns="Month", values="Cumulative_Hours"
)

# Keep NaN values as NaN (don't fill with 0)
matrix = pivot_table.values
years = pivot_table.index.tolist()
months = pivot_table.columns.tolist()


# Create month labels
month_labels = [calendar.month_name[int(m)] for m in months]

# Create the heatmap
fig = go.Figure()

# First heatmap: actual data
fig.add_trace(
    go.Heatmap(
        z=matrix,
        x=month_labels,
        y=[str(year) for year in years],
        colorscale=[[0, "#8A2852"], [0.5, "#FFD301"], [1, "#9CBB18"]],
        colorbar=dict(title="Colorscale: number of hours"),
        hoverongaps=False,
        hovertemplate="Date: %{x} %{y}<br>Number of hours: %{z}<extra></extra>",
        showscale=True,
        zmin=0,
        zmax=744,
        connectgaps=False,
    )
)

st.title(f"BFF heatmap - {selected_fuel.lower()} share in generation")
fig.update_layout(
    title=f"<i>{selected_country.upper()}</i>: Number of hours when <i>{selected_fuel.upper()}</i> represented <i>{selected_share_bin}</i> of total generation",
    title_x=0.1,
    xaxis_title="Month",
    yaxis_title="Year",
    width=800,
    height=600,
)
fig.update_xaxes(showgrid=False)
fig.update_yaxes(showgrid=False)


# Display the heatmap
st.plotly_chart(fig, use_container_width=True)
st.markdown("Source: Beyond Fossil Fuels elaboration based on ENTSO-E data")
if selected_country == "Europe average":
    st.markdown(
        '⚠️ "Europe average" represents the average across all listed countries, excluding Italy due to data quality concerns, and Ukraine due to missing data. It shows the mean number of hours when generation from the selected fuel source fell below the specified percentage threshold.'
    )
elif selected_country == "Italy":
    st.markdown("⚠️ Data quality for Italy is questionable, particularly prior to 2018.")


# Display filtered data table
with st.expander("🔢 View data"):
    st.dataframe(filtered_df, use_container_width=True, height=400)

# Data download
csv = filtered_df.to_csv(index=False)
st.download_button(
    label="📥 Download data as CSV",
    data=csv,
    file_name=f"filtered_data_{selected_fuel}_{selected_share_bin}.csv",
    mime="text/csv",
)
