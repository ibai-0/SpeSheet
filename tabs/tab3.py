from dash import html, dcc, callback, Input, Output, State, callback_context as ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def layout():
    return html.Div(className='tab-animacion', children=[
        dbc.Row([
            # Left Column - Map
            dbc.Col([
                dcc.Graph(id='map-graph')
            ], width=8),
            
            # Right Column - Side Plots & Controls
            dbc.Col([
                html.Div(id='subplots-container'),
                dbc.Button("Advanced Analysis", id="open-advanced", color="primary", className="w-100 shadow-sm mt-1", size="sm"),
            ], width=4)
        ]),
        
        # Unified Modal for additional analysis
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Advanced Global Analysis")),
            dbc.ModalBody([
                html.Div(id="modal-advanced-body"),
                html.Hr(className="my-2"),
                dbc.Button("Close Analysis", id="close-advanced", color="secondary", className="float-end btn-sm mb-2"),
            ]),
        ], id="modal-advanced", size="xl", is_open=False),
        
        # Global Store for country selection
        dcc.Store(id='selected-country-store', data=None),
    ])

