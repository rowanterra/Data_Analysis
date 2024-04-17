from dash import Dash, dcc, html, Input, Output, State, dash_table
import plotly.graph_objects as go
import pandas as pd
import plotly.express as px
import json

# bring in the data, specifying columns to read
df = pd.read_csv('Test_4.15.2024_Liquids.csv', usecols=lambda column: column not in ['Unnamed: 65', 'Unnamed: 66']) # this dataset struggles and always wants to pull columns 65 and 66 so I ignore them here

# sort the data, in my case by season 
df['Season'] = pd.Categorical(df['Season'], categories=['Spring', 'Summer', 'Fall', 'Winter'], ordered=True)
df = df.sort_values(by=['Season', 'Sample'])

# replace <DL with 0. I want <DLs (since measured) to be 0 and NaNs to be NaNs ... which I do below. For some CSVs this has an issue, so sometimes I will find+replace all <DLs or BDLs for a dataset with 0. Just make sure to put in legend. 
df.replace("<DL", 0, inplace=True)

# my numerical data I care about begins column 5 onward, edit for different datasets.
groups = {"all": list(df.columns[5:])} 

# this is a file I made for elemental groups such as CMM, REE, etc. If you have groups within your numerical data you will want to make something similar. 
with open('/Users/rowanterra/Downloads/groups.json') as groups_file:
    groups.update(json.load(groups_file))
    
app = Dash(__name__)

# Note, these are set for my type of datafiles where samples have particular names I want in a particular oreder in the dropdown.
app.layout = html.Div([
    html.H4('Relative Abundance Heatmap'),
    dcc.Graph(id="heatmap"),
    html.P("Filter by Sample:"),
    dcc.Dropdown(
    id='sample-dropdown',
    options=[
        {'label': 'AerationPipe', 'value': 'AerationPipe'},
        {'label': 'APR_1', 'value': 'APR_1'},
        {'label': 'A_1', 'value': 'A_1'},
        {'label': 'B_1', 'value': 'B_1'},
        {'label': 'C_1', 'value': 'C_1'},
        {'label': 'P_1', 'value': 'P_1'},
        {'label': 'P_2', 'value': 'P_2'},
        {'label': 'P_3', 'value': 'P_3'},
        {'label': 'P_4', 'value': 'P_4'}
    ],
    value=['AerationPipe', 'APR_1', 'A_1', 'B_1', 'C_1', 'P_1', 'P_2', 'P_3', 'P_4'], 
    multi=True,  # this allows for multiple selections
),
    html.P("Filter by Season:"),
    dcc.Dropdown(
        id='season-dropdown',
        options=[
            {'label': 'Spring', 'value': 'Spring'},
            {'label': 'Summer', 'value': 'Summer'},
            {'label': 'Fall', 'value': 'Fall'},
            {'label': 'Winter', 'value': 'Winter'}
        ],
        value=['Spring', 'Summer', 'Fall', 'Winter'], 
        multi=True, 
    ),
    html.P("Filter by Elements:"),
    dcc.Dropdown(
        id='elements',
        options=[{'label': element, 'value': element} for element in df.columns[5:]],
        value=list(df.columns[5:]), 
        multi=True,  
    ),
    html.P("Add Element Group:"),
    dcc.Dropdown(
        id='element_groups',
        options=[{'label': group, 'value': group} for group in groups],
        value=None 
    ),
    html.P("Select Normalization Method:"),
    dcc.Dropdown(
        id='normalization-method',
        options=[
            {'label': 'Min-Max Scaling', 'value': 'min_max'},
            {'label': 'Relative Abundance', 'value': 'relative_abundance'},
            {'label': 'Z-score', 'value': 'z_score'}
        ],
        value='min_max',
    ),
    html.Pre(id="filtered-data"),  # Add this line to display the printed data
])

@app.callback(
    Output("elements", "value"),
    Output("element_groups", "value"),
    Input("element_groups", "value"),
    State("elements", "value")
)
def on_element_groups(group, elements):
    if group is None:
        return elements, None
    group = groups[group]
    for element in group:
        if element not in elements and element in df.columns[5:]:
            elements.append(element)
    return elements, None

@app.callback(
    [Output("heatmap", "figure"),
     Output("filtered-data", "children")],
    [Input("sample-dropdown", "value"),
     Input("season-dropdown", "value"),
     Input("elements", "value"),
     Input("normalization-method", "value")]  # Add the new input
)
def filter_heatmap(selected_samples, selected_seasons, selected_elements, normalization_method):
    # order the heatmap based on the order I care about
    desired_sample_order = ['AerationPipe', 'APR_1', 'A_1', 'B_1', 'C_1', 'P_1', 'P_2', 'P_3', 'P_4']
    selected_samples = [sample for sample in desired_sample_order if sample in selected_samples]

    # order the heatmap seasons 
    desired_season_order = ['Spring', 'Summer', 'Fall', 'Winter']
    selected_seasons = [season for season in desired_season_order if season in selected_seasons]

    # make seasons categorical data
    selected_seasons = pd.Categorical(selected_seasons, categories=desired_season_order, ordered=True)

    # filter based on seasons
    filtered_df = df.query('Season in @selected_seasons')

    # filter based on selected samples
    filtered_df = filtered_df[filtered_df['Sample'].isin(selected_samples)]

    heatmap_data = filtered_df[selected_elements]

    # make data that is non-numeric/NaN read as NaN 
    heatmap_data = heatmap_data.apply(pd.to_numeric, errors='coerce')

    if normalization_method == 'min_max':
        normalized_data = (heatmap_data - heatmap_data.min()) / (heatmap_data.max() - heatmap_data.min())
        title = "Min-Max Scaled Heatmap"
    elif normalization_method == 'relative_abundance':
        normalized_data = heatmap_data.div(heatmap_data.sum(axis=0), axis=1)
        title = "Relative Abundance Heatmap"
    elif normalization_method == 'z_score':
        normalized_data = (heatmap_data - heatmap_data.mean()) / heatmap_data.std()
        title = "Z-score Heatmap"
    else:
        raise ValueError(f"Invalid normalization method: {normalization_method}")

    fig = go.Figure()

    x = []
    y = selected_elements
    z = None
    
    for season, season_df in filtered_df.groupby('Season'):
        for sample in desired_sample_order:
            if sample in season_df['Sample'].values:
                x.append(f"{season} - {sample}")
                z = pd.concat((z, normalized_data.loc[season_df[season_df['Sample'] == sample].index, selected_elements].transpose()), axis=1)

 
    fig.add_trace(go.Heatmap(
        y=y,
        x=x,
        z=z,
        #name=season,
        colorscale='GnBu',
    ))
    num_elements = len(selected_elements)
    num_samples = len(selected_samples)
    height = max(500, num_elements * 20) 
    width = max(500, num_samples * 80)    

    fig.update_layout(
        title=title,
        xaxis_title="Season - Sample",
        yaxis_title="Elements",
        height=height,
        width=width,
        yaxis=dict(tickangle=0, dtick=1),
        xaxis=dict(tickangle=-90, dtick=1)
    )

    # Print filtered data with selected normalization method
    filtered_data_str = f"Filtered Data:\n{filtered_df.to_string(index=False)}"
    if normalization_method == 'min_max':
        filtered_data_str += f"\n\nMin-Max Scaled:\n{normalized_data.to_string(index=False)}"
    elif normalization_method == 'relative_abundance':
        filtered_data_str += f"\n\nRelative Abundance:\n{normalized_data.to_string(index=False)}"
    elif normalization_method == 'z_score':
        filtered_data_str += f"\n\nZ-scores:\n{normalized_data.to_string(index=False)}"

    return fig, filtered_data_str

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8070, debug=True)