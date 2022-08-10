from typing import List, Tuple, Union, Any

import pandas
from bokeh.core.has_props import HasProps
from bokeh.core.property.instance import Instance
from bokeh.plotting import figure, curdoc, Figure
from bokeh.driving import linear

from bokeh.plotting import figure
from bokeh.plotting.figure import Figure
from bokeh.models import ColumnDataSource, DataSource, TableColumn, DataTable
from bokeh.layouts import layout
from bokeh.io import show
import pandas as pd

import gt7communication
from gt7helper import secondsToLaptime
from gt7lap import Lap
from gt7plot import get_session_layout, get_x_axis_depending_on_mode, get_best_lap, get_median_lap, get_brake_points


def pd_data_frame_from_lap(laps: List[Lap], best_lap: int) -> pd.core.frame.DataFrame:
    df = pd.DataFrame()
    for lap in laps:
        time_diff = ""
        if best_lap == lap.LapTime:
            # lap_color = 35 # magenta
            # TODO add some formatting
            pass
        elif lap.LapTime < best_lap: # LapTime cannot be smaller than bestlap, bestlap is always the smallest. This can only mean that lap.LapTime is from an earlier race on a different track
            time_diff = "-"
        elif best_lap > 0:
            time_diff = secondsToLaptime(-1 * (best_lap / 1000 - lap.LapTime / 1000))

        df = df.append({'number':lap.Number,
                        'time':secondsToLaptime(lap.LapTime / 1000),
                        'diff':time_diff,
                        'fullthrottle': "%.2f" % (lap.FullThrottleTicks/lap.LapTicks),
                        'throttleandbreak': "%.2f" % (lap.ThrottleAndBrakesTicks/lap.LapTicks),
                        'fullbreak': "%.2f" % (lap.FullBrakeTicks/lap.LapTicks),
                        'nothrottle': "%.2f" % (lap.NoThrottleNoBrakeTicks/lap.LapTicks),
                        'tyrespinning': "%.2f" % (lap.TiresSpinningTicks/lap.LapTicks),
                        },
                       ignore_index=True)

    return df

def get_data_from_lap(lap: Lap, title: str, distance_mode: bool):

    # breakpoints_x, breakpoints_y = get_brake_points(lap)
    data = {
        'throttle': lap.DataThrottle,
        'brake' : lap.DataBraking,
        'speed' : lap.DataSpeed,
        'raceline_y' : lap.PositionsY,
        'raceline_x' : lap.PositionsX,
        'raceline_z' : lap.PositionsZ,
        # 'breakpoints_x' : breakpoints_x,
        # 'breakpoints_y' : breakpoints_y,
        'distance': get_x_axis_depending_on_mode(lap, distance_mode),
        # 'title': title,
    }

    return data

def get_throttle_velocity_diagram_for_best_lap_and_last_lap(laps: List[Lap], distance_mode: bool, width: int) -> tuple[
    Figure, list[ColumnDataSource]]:

    TOOLTIPS = [
        ("index", "$index"),
        ("value", "$y"),
    ]
    colors = ["blue", "magenta", "green"]
    legends = ["Last Lap", "Best Lap", "Median Lap"]

    f = figure(title="Speed/Throttle - Last, Best, Median", x_axis_label="Distance", y_axis_label="Value", width=width, height=500, tooltips=TOOLTIPS)

    sources = []

    for color, legend in zip(colors, legends):

        source = ColumnDataSource(data={})
        sources.append(source)

        f.line(x='distance', y='speed', source=source, legend_label=legend, line_width=1, color=color, line_alpha=1)
        f.line(x='distance', y='throttle', source=source, legend_label=legend, line_width=1, color=color, line_alpha=0.5)
        f.line(x='distance', y='brake', source=source, legend_label=legend, line_width=1, color=color, line_alpha=0.2)

        # line_speed = f.line(x='speed', y='distance', source=source, legend_label=lap.Title, line_width=1, color=colors[i])

    f.legend.click_policy="hide"
    return f, sources

p = figure(plot_width=1000, plot_height=600)
r1 = p.line([], [], color="green", line_width=2)
r2 = p.line([], [], color="blue", line_width=2)
r3 = p.line([], [], color="red", line_width=2)

ds1 = r1.data_source
ds2 = r2.data_source
ds3 = r3.data_source

# def on_server_loaded(server_context):
gt7comm = gt7communication.GT7Communication("192.168.178.120")
gt7comm.start()

source = ColumnDataSource(pd_data_frame_from_lap([], best_lap=gt7comm.session.best_lap))

columns = [
    TableColumn(field='number', title='#'),
    TableColumn(field='time', title='Time'),
    TableColumn(field='diff', title='Diff'),
    TableColumn(field='fullthrottle', title='Full Throttle'),
    TableColumn(field='fullbreak', title='Full Break'),
    TableColumn(field='nothrottle', title='No Throttle'),
    TableColumn(field='tyrespinning', title='Tire Spin')
]

velocity_and_throttle_diagram, data_sources = get_throttle_velocity_diagram_for_best_lap_and_last_lap([], True, 1000)


myTable = DataTable(source=source, columns=columns)
myTable.width=1000

##### Race line

RACE_LINE_TOOLTIPS = [
    ("index", "$index"),
    ("Breakpoint", "")
]

race_line_width = 500
speed_diagram_width = 1200
total_width = race_line_width + speed_diagram_width
s_race_line = figure(title="Race Line", x_axis_label="z", y_axis_label="x", width=500, height=500, tooltips=RACE_LINE_TOOLTIPS)

last_lap_race_line = s_race_line.line(x="raceline_z", y="raceline_x", legend_label="Last Lap", line_width=1, color="blue")
best_lap_race_line = s_race_line.line(x="raceline_z", y="raceline_x", legend_label="Best Lap", line_width=1, color="magenta")


@linear()
def update_last_lap_best_lap(step):
    laps = gt7comm.get_laps()
    if len(laps) > 0:
        last_lap = laps[0]
        best_lap = get_best_lap(laps)
        median_lap = get_median_lap(laps)

        last_lap_data = get_data_from_lap(last_lap, title="Last: %s" % last_lap.Title, distance_mode=True)
        best_lap_data = get_data_from_lap(best_lap, title="Best: %s" % last_lap.Title, distance_mode=True)

        data_sources[0].data = last_lap_data
        data_sources[1].data = best_lap_data
        data_sources[2].data = get_data_from_lap(median_lap, title="Median: %s" % last_lap.Title, distance_mode=True)

        last_lap_race_line.data_source.data = last_lap_data
        best_lap_race_line.data_source.data = best_lap_data

@linear()
def update_laps(step):
    # time, x, y, z = from_csv(reader).next()
    laps = gt7comm.get_laps()
    print("Adding %d laps" % len(laps))
    myTable.source.data = ColumnDataSource.from_df(pd_data_frame_from_lap(laps, best_lap=gt7comm.session.best_lap))
    myTable.trigger('source', myTable.source, myTable.source)

@linear()
def update(step):
    # time, x, y, z = from_csv(reader).next()
    last_package = gt7comm.get_last_data()
    ds1.data['x'].append(last_package.package_id)
    ds2.data['x'].append(last_package.package_id)
    ds3.data['x'].append(last_package.package_id)
    ds1.data['y'].append(last_package.carSpeed)
    ds2.data['y'].append(last_package.throttle)
    ds3.data['y'].append(last_package.brake)
    ds1.trigger('data', ds1.data, ds1.data)
    ds2.trigger('data', ds2.data, ds2.data)
    ds3.trigger('data', ds3.data, ds3.data)

# l = get_session_layout(gt7comm.get_laps(), True)



# df = pd.DataFrame({
#     'SubjectID': ['Subject_01','Subject_02','Subject_03'],
#     'Result_1': ['Positive','Negative','Negative'],
#     'Result_3': ['Negative','Invalid','Positive'],
#     'Result_4': ['Positive','Negative','Negative'],
#     'Result_5': ['Positive','Positive','Negative']
# })

# show(myTable)

l = layout(children=[
    [velocity_and_throttle_diagram],
    # [p],
    [myTable],
    [s_race_line]
])

curdoc().add_root(l)

# Add a periodic callback to be run every 500 milliseconds
# curdoc().add_periodic_callback(update, 60) # best would be 16ms, 60ms is smooth enough
curdoc().add_periodic_callback(update_laps, 1000) # best would be 16ms, 60ms is smooth enough
curdoc().add_periodic_callback(update_last_lap_best_lap, 1000) # best would be 16ms, 60ms is smooth enough