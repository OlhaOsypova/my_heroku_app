#!/usr/bin/env python
# coding: utf-8

# In[11]:


import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px

# Завантаження основного датафрейму
df_main = pd.read_csv('missiles_attacks_cleaned.csv')

# Видалення рядків з пропусками у стовпчику 'launched'
df_main = df_main.dropna(subset=['launched'])

# Перетворення стовпця 'time_start' на формат datetime
df_main['time_start'] = pd.to_datetime(df_main['time_start'])

# Додавання стовпчика 'year' для агрегації за роками
df_main['year'] = df_main['time_start'].dt.year

# Заміняємо невідомі категорії на 'Unknown'
df_main['category'] = df_main['category'].fillna('Unknown')

# Перевірка унікальних значень у стовпчику 'launch_place'
print(df_main['launch_place'].unique())

# Геокодування міст, якщо потрібно, встановлення координат вручну для проблемних місць
df_main.loc[df_main['launch_place'] == 'Moscow', ['latitude', 'longitude']] = [55.7558, 37.6173]

# Агрегація даних за датами для графіка
df_daily = df_main.groupby(df_main['time_start'].dt.date).agg({
    'launched': 'sum',
    'destroyed': 'sum',
    'destroyed_ratio': 'mean'
}).reset_index()

# Перетворення стовпця з групованими датами на тип datetime
df_daily['time_start'] = pd.to_datetime(df_daily['time_start'])

# Агрегація даних за категоріями та роками з округленням destroyed_ratio
df_aggregated = df_main.groupby(['category', 'year'], dropna=False).agg({
    'launched': 'sum',
    'destroyed_ratio': lambda x: round(x.mean(), 2)  # Округлення до 2 знаків після коми
}).reset_index()

# Агрегація даних за цілями (target) для топ-10 атакованих місць
df_target = df_main.groupby('target').agg({'launched': 'sum'}).reset_index()
df_target = df_target.sort_values(by='launched', ascending=False).head(10)

# Створення зведеної таблиці та сортування
pivot_df = df_main.pivot_table(
    index=['time_start', 'target'], 
    columns='category', 
    values='launched', 
    aggfunc='sum'
).reset_index()

# Додавання стовпчика із загальною сумою по всіх категоріях
pivot_df['Total'] = pivot_df.select_dtypes(include='number').sum(axis=1)

# Сортування за стовпчиком 'Total' і відбір топ-10 записів
sorted_df = pivot_df.sort_values(by='Total', ascending=False).head(10)
sorted_df['time_start'] = sorted_df['time_start'].dt.strftime('%d-%m-%Y')

# Створення кругової діаграми з налаштуванням шрифтів
pie_chart = px.pie(df_main.groupby('category')['launched'].sum().reset_index(), 
                   names='category', 
                   values='launched')

# Налаштування шрифтів для заголовка, легенди та написів
pie_chart.update_layout(
    title={
        'text': "Distribution of Launched Objects by Category",
        'x': 0.5,
        'xanchor': 'center',
        'yanchor': 'top',
        'font': dict(family="Times New Roman", size=20, color="Black")
    },
    legend=dict(
        font=dict(family="Times New Roman", size=14, color="Black")
    ),
    font=dict(family="Times New Roman", size=14, color="Black")  # Налаштування шрифтів для написів на графіку
)

# Створення застосунку Dash
app = dash.Dash(__name__)

# Макет застосунку
app.layout = html.Div([
    html.H1('Visualization of Missile and Drone Attacks in Ukraine '),

    # Вкладки для переключення між графіками
    dcc.Tabs(id='tabs', value='tab-1', children=[
        dcc.Tab(label='Attacks Overview', value='tab-general'),
        dcc.Tab(label='Timeline of Attacks', value='tab-1'),
        dcc.Tab(label='Geography of Attacks', value='tab-2'),
    ]),

    # Контейнер для відображення вмісту вкладок
    html.Div(id='tabs-content')
])

# Колбек для відображення вмісту відповідної вкладки
@app.callback(Output('tabs-content', 'children'),
              Input('tabs', 'value'))
def render_content(tab):
    if tab == 'tab-general':
        return html.Div([
            html.H2('Total Missile and Drone (UAV) Attacks on Ukraine: Breakdown by Weapon Category'),
            html.P(f'Total attacks on Ukraine from {df_main["time_start"].min().strftime("%Y-%m-%d")} to {df_main["time_start"].max().strftime("%Y-%m-%d")}:'),
            html.Ul([
                html.Li(f'Total launched: {df_main["launched"].sum()}'),
                html.Li("By category:", style={'font-weight': 'bold'}),
                *[html.Li(f'{row["category"]}: {row["launched"]}') for _, row in df_main.groupby('category')['launched'].sum().reset_index().iterrows()]
            ]),
            html.H2('Weapon Categories in Launched Attacks'),
            dcc.Graph(figure=pie_chart),  # Додаємо графік з налаштуванням шрифтів
            html.H2('Top 10 Most Massive Attacks by Day and Category'),
            dash_table.DataTable(
                columns=[{"name": i.capitalize(), "id": i} for i in sorted_df.columns],
                data=sorted_df.to_dict('records'),
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
            )
        ])
    elif tab == 'tab-1':
        return html.Div([
            html.H2('Chronology of Missile and Drone Attacks'),
            dcc.Dropdown(
                id='time-filter',
                options=[
                    {'label': 'Number of Launched Missiles and Drones', 'value': 'launched'},
                    {'label': 'Number of Destroyed Missiles and Drones', 'value': 'destroyed'},
                    {'label': 'Destroyed Ratio (%)', 'value': 'destroyed_ratio'},
                ],
                value='launched',
                style={'width': '50%'}
            ),
            dcc.DatePickerRange(
                id='date-picker-range',
                start_date=df_daily['time_start'].min(),
                end_date=df_daily['time_start'].max(),
                display_format='YYYY-MM-DD'
            ),
            dcc.Graph(id='time-series-graph'),
            html.H2('Summary of Missile and Drone (UAV) Attacks by Category and Year'),
            dash_table.DataTable(
                columns=[{"name": i.capitalize(), "id": i} for i in df_aggregated.columns],
                data=df_aggregated.to_dict('records'),
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
            )
        ])
    elif tab == 'tab-2':
        return html.Div([
            html.H2('Geography of Launch Sites'),
            dcc.Graph(figure=px.scatter_geo(df_main, lat='latitude', lon='longitude', color='category',
                                            hover_name='launch_place', title='Interactive Map of Launch Sites',
                                            size='launched', size_max=20).update_geos(showcountries=False, showsubunits=False,
                                                                                      fitbounds="locations", resolution=50,
                                                                                      showland=True, landcolor="LightGrey",
                                                                                      showocean=True, oceancolor="LightBlue")),
            html.H2('Most Targeted Regions: Top 10 Locations'),
            dcc.Graph(figure=px.bar(df_target, x='target', y='launched', title='Frequency of Attacks on Top 10 Targeted Locations',
                                    labels={'target': 'Location', 'launched': 'Number of Launched Missiles and Drones'}))
        ])

# Колбек для оновлення графіку часового аналізу
@app.callback(
    Output('time-series-graph', 'figure'),
    [Input('time-filter', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('tabs', 'value')]
)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          
def update_time_series(selected_filter, start_date, end_date, tab):
    if tab != 'tab-1':
        return dash.no_update

    filtered_df = df_daily[(df_daily['time_start'] >= start_date) & (df_daily['time_start'] <= end_date)]

    if filtered_df.empty:
        return px.scatter(title='No data available for the selected date range.')

    fig = px.scatter(filtered_df, x='time_start', y=selected_filter, title='Time Analysis of Attacks')

    fig.update_traces(marker=dict(size=5, color='#0000FF', opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
    fig.update_layout(xaxis_title='Date', yaxis_title=selected_filter.capitalize(), template='plotly_white')

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)


# In[ ]:




