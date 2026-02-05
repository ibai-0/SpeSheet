from tabs import tab1, tab2, tab3
from dash import callback, Output, Input

## -- all layouts --
@callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'active_tab'),
)
def render_tab_layout(tab):
    """
    Master Layout Router: Decides what HTML structure to show based on the tab.
    """
    if tab == 'tab-1':
        return tab1.layout()

    # --- TAB 2: PROSPERITY ---
    elif tab == 'tab-2':
        return tab2.layout()

    # --- TAB 3: CORRELATION ---
    elif tab == 'tab-3':
        return tab3.layout()

    return html.Div("Select a tab")



