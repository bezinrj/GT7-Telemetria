from typing import List

import bokeh
from bokeh.layouts import layout
from bokeh.models import ColumnDataSource, Label, Scatter, Column, Line, TableColumn, DataTable, Range1d
from bokeh.plotting import figure

from gt7dashboard import gt7helper
from gt7dashboard.gt7lap import Lap


def get_throttle_braking_race_line_diagram():
    # TODO Make this work, tooltips just show breakpoint
    race_line_tooltips = [("index", "$index")]
    s_race_line = figure(
        title="Race Line",
        match_aspect=True,
        active_scroll="wheel_zoom",
        tooltips=race_line_tooltips,
    )

    # We set this to true, since maps appear flipped in the game
    # compared to their actual coordinates
    s_race_line.y_range.flipped = True

    s_race_line.toolbar.autohide = True

    s_race_line.axis.visible = False
    s_race_line.xgrid.visible = False
    s_race_line.ygrid.visible = False

    throttle_line = s_race_line.line(
        x="raceline_x_throttle",
        y="raceline_z_throttle",
        legend_label="Throttle Last Lap",
        line_width=5,
        color="green",
        source=ColumnDataSource(
            data={"raceline_z_throttle": [], "raceline_x_throttle": []}
        ),
    )
    breaking_line = s_race_line.line(
        x="raceline_x_braking",
        y="raceline_z_braking",
        legend_label="Braking Last Lap",
        line_width=5,
        color="red",
        source=ColumnDataSource(
            data={"raceline_z_braking": [], "raceline_x_braking": []}
        ),
    )

    coasting_line = s_race_line.line(
        x="raceline_x_coasting",
        y="raceline_z_coasting",
        legend_label="Coasting Last Lap",
        line_width=5,
        color="blue",
        source=ColumnDataSource(
            data={"raceline_z_coasting": [], "raceline_x_coasting": []}
        ),
    )

    # Reference Lap

    reference_throttle_line = s_race_line.line(
        x="raceline_x_throttle",
        y="raceline_z_throttle",
        legend_label="Throttle Reference",
        line_width=15,
        alpha=0.3,
        color="green",
        source=ColumnDataSource(
            data={"raceline_z_throttle": [], "raceline_x_throttle": []}
        ),
    )
    reference_breaking_line = s_race_line.line(
        x="raceline_x_braking",
        y="raceline_z_braking",
        legend_label="Braking Reference",
        line_width=15,
        alpha=0.3,
        color="red",
        source=ColumnDataSource(
            data={"raceline_z_braking": [], "raceline_x_braking": []}
        ),
    )

    reference_coasting_line = s_race_line.line(
        x="raceline_x_coasting",
        y="raceline_z_coasting",
        legend_label="Coasting Reference",
        line_width=15,
        alpha=0.3,
        color="blue",
        source=ColumnDataSource(
            data={"raceline_z_coasting": [], "raceline_x_coasting": []}
        ),
    )

    s_race_line.legend.visible = True

    s_race_line.add_layout(s_race_line.legend[0], "right")

    s_race_line.legend.click_policy = "hide"

    return (
        s_race_line,
        throttle_line,
        breaking_line,
        coasting_line,
        reference_throttle_line,
        reference_breaking_line,
        reference_coasting_line,
    )

class RaceTimeTable(object):

    def __init__(self):

        self.columns = [
            TableColumn(field="number", title="#"),
            TableColumn(field="time", title="Time"),
            TableColumn(field="diff", title="Diff"),
            TableColumn(field="info", title="Info"),
            TableColumn(field="fuelconsumed", title="Fuel Cons."),
            TableColumn(field="fullthrottle", title="Full Throt."),
            TableColumn(field="fullbreak", title="Full Break"),
            TableColumn(field="nothrottle", title="Coast"),
            TableColumn(field="tyrespinning", title="Tire Spin"),
            TableColumn(field="car_name", title="Car"),
        ]

        self.lap_times_source = ColumnDataSource(
            gt7helper.pd_data_frame_from_lap([], best_lap_time=0)
        )
        self.t_lap_times: DataTable

        self.t_lap_times = DataTable(
            source=self.lap_times_source, columns=self.columns, index_position=None, css_classes=["lap_times_table"]
        )
        # This will lead to not being rendered
        # self.t_lap_times.autosize_mode = "fit_columns"
        # Maybe this is related: https://github.com/bokeh/bokeh/issues/10512 ?


    def show_laps(self, laps: List[Lap]):
        best_lap = gt7helper.get_best_lap(laps)
        new_df = gt7helper.pd_data_frame_from_lap(laps, best_lap_time=best_lap.lap_finish_time)
        self.lap_times_source.data = ColumnDataSource.from_df(new_df)

class RaceDiagram(object):
    def __init__(self, width=400):
        """
        Returns figures for time-diff, speed, throttling, braking and coasting.
        All with lines for last lap, best lap and median lap.
        The last return value is the sources object, that has to be altered
        to display data.
        """

        self.speed_lines = []
        self.braking_lines = []
        self.coasting_lines = []
        self.throttle_lines = []
        self.tires_lines = []

        # Data Sources
        self.source_time_diff = None
        self.source_speed_variance = None
        self.source_last_lap = None
        self.source_reference_lap = None
        self.source_median_lap = None
        self.sources_additional_laps = []

        self.additional_laps = List[Lap]

        # This is the number of default laps,
        # last lap, best lap and median lap
        self.number_of_default_laps = 3


        tooltips = [
            ("index", "$index"),
            ("value", "$y"),
            ("Speed", "@speed{0} kph"),
            ("Throttle", "@throttle%"),
            ("Brake", "@brake%"),
            ("Coast", "@coast%"),
            ("Distance", "@distance{0} m"),
        ]

        tooltips_timedelta = [
            ("index", "$index"),
            ("timedelta", "@timedelta{0} ms"),
            ("reference", "@reference{0} ms"),
            ("comparison", "@comparison{0} ms"),
        ]

        self.tooltips_speed_variance = [
            ("index", "$index"),
            ("Distance", "@distance{0} m"),
            ("Spd. Deviation", "@speed_variance{0}"),
        ]

        self.f_speed = figure(
            title="Last, Reference, Median",
            y_axis_label="Speed",
            width=width,
            height=250,
            tooltips=tooltips,
            active_drag="box_zoom",
        )

        self.f_speed_variance = figure(
            y_axis_label="Spd.Dev.",
            x_range=self.f_speed.x_range,
            y_range=Range1d(0, 50),
            width=width,
            height=int(self.f_speed.height / 4),
            tooltips=self.tooltips_speed_variance,
            active_drag="box_zoom",
        )

        self.f_time_diff = figure(
            title="Time Diff - Last, Reference",
            x_range=self.f_speed.x_range,
            y_axis_label="Time / Diff",
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips_timedelta,
            active_drag="box_zoom",
        )

        self.f_throttle = figure(
            x_range=self.f_speed.x_range,
            y_axis_label="Throttle",
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips,
            active_drag="box_zoom",
        )
        self.f_braking = figure(
            x_range=self.f_speed.x_range,
            y_axis_label="Braking",
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips,
            active_drag="box_zoom",
        )

        self.f_coasting = figure(
            x_range=self.f_speed.x_range,
            y_axis_label="Coasting",
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips,
            active_drag="box_zoom",
        )

        self.f_tires = figure(
            x_range=self.f_speed.x_range,
            y_axis_label="Tire Spd / Car Spd",
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips,
            active_drag="box_zoom",
        )

        self.f_speed.toolbar.autohide = True

        span_zero_time_diff = bokeh.models.Span(
            location=0,
            dimension="width",
            line_color="black",
            line_dash="dashed",
            line_width=1,
        )
        self.f_time_diff.add_layout(span_zero_time_diff)

        self.f_time_diff.toolbar.autohide = True

        self.f_speed_variance.xaxis.visible = False
        self.f_speed_variance.toolbar.autohide = True

        self.f_throttle.xaxis.visible = False
        self.f_throttle.toolbar.autohide = True

        self.f_braking.xaxis.visible = False
        self.f_braking.toolbar.autohide = True

        self.f_coasting.xaxis.visible = False
        self.f_coasting.toolbar.autohide = True

        self.f_tires.xaxis.visible = False
        self.f_tires.toolbar.autohide = True

        self.source_time_diff = ColumnDataSource(data={"distance": [], "timedelta": []})
        self.f_time_diff.line(
            x="distance",
            y="timedelta",
            source=self.source_time_diff,
            line_width=1,
            color="blue",
            line_alpha=1,
        )

        self.source_last_lap = self.add_lap_to_race_diagram("blue", "Last Lap", True)

        self.source_reference_lap = self.add_lap_to_race_diagram("magenta", "Reference Lap", True)

        self.source_median_lap = self.add_lap_to_race_diagram("green", "Median Lap", False)

        self.f_speed.legend.click_policy = "hide"
        self.f_throttle.legend.click_policy = self.f_speed.legend.click_policy
        self.f_braking.legend.click_policy = self.f_speed.legend.click_policy
        self.f_coasting.legend.click_policy = self.f_speed.legend.click_policy
        self.f_tires.legend.click_policy = self.f_speed.legend.click_policy

        self.layout = layout(self.f_time_diff, self.f_speed, self.f_speed_variance, self.f_throttle, self.f_braking, self.f_coasting, self.f_tires)

        self.source_speed_variance = ColumnDataSource(data={"distance": [], "speed_variance": []})

        self.f_speed_variance.line(
            x="distance",
            y="speed_variance",
            source=self.source_speed_variance,
            line_width=1,
            color="gray",
            line_alpha=1,
            visible=True
        )

    def add_additional_lap_to_race_diagram(self, color: str, lap: Lap, visible: bool = True):
        source = self.add_lap_to_race_diagram(color, lap.title, visible)
        source.data = lap.get_data_dict()
        self.sources_additional_laps.append(source)

    def update_fastest_laps_variance(self, laps):
        # FIXME, many many data points, mayabe reduce by the amount of laps?
        variance, fastest_laps = gt7helper.get_variance_for_fastest_laps(laps)
        self.source_speed_variance.data = variance
        return fastest_laps

    def add_lap_to_race_diagram(self, color: str, legend: str, visible: bool = True):

        # Set empty data for avoiding warnings about missing columns
        dummy_data = Lap().get_data_dict()

        source = ColumnDataSource(data=dummy_data)

        self.speed_lines.append(self.f_speed.line(
            x="distance",
            y="speed",
            source=source,
            legend_label=legend,
            line_width=1,
            color=color,
            line_alpha=1,
            visible=visible
        ))

        self.throttle_lines.append(self.f_throttle.line(
            x="distance",
            y="throttle",
            source=source,
            legend_label=legend,
            line_width=1,
            color=color,
            line_alpha=1,
            visible=visible
        ))

        self.braking_lines.append(self.f_braking.line(
            x="distance",
            y="brake",
            source=source,
            legend_label=legend,
            line_width=1,
            color=color,
            line_alpha=1,
            visible=visible
        ))

        self.coasting_lines.append(self.f_coasting.line(
            x="distance",
            y="coast",
            source=source,
            legend_label=legend,
            line_width=1,
            color=color,
            line_alpha=1,
            visible=visible
        ))

        self.tires_lines.append(self.f_tires.line(
            x="distance",
            y="tires",
            source=source,
            legend_label=legend,
            line_width=1,
            color=color,
            line_alpha=1,
            visible=visible
        ))

        return source

    def get_layout(self) -> Column:
        return self.layout

    def delete_all_additional_laps(self):
        # Delete all but first three in list
        self.sources_additional_laps = []

        for i, _ in enumerate(self.f_speed.renderers):
            if i >= self.number_of_default_laps:
                self.f_speed.renderers.remove(self.f_speed.renderers[i])  # remove the line renderer
                self.f_throttle.renderers.remove(self.f_throttle.renderers[i])  # remove the line renderer
                self.f_braking.renderers.remove(self.f_braking.renderers[i])  # remove the line renderer
                self.f_coasting.renderers.remove(self.f_coasting.renderers[i])  # remove the line renderer
                self.f_tires.renderers.remove(self.f_tires.renderers[i])  # remove the line renderer
                # self.f_time_diff.renderers.remove(self.f_time_diff.renderers[i])  # remove the line renderer

                self.f_speed.legend.items.pop(i)
                self.f_throttle.legend.items.pop(i)
                self.f_braking.legend.items.pop(i)
                self.f_coasting.legend.items.pop(i)
                self.f_tires.legend.items.pop(i)
                # self.f_time_diff.legend.items.pop(i)






def add_annotations_to_race_line(
    race_line: figure, last_lap: Lap, reference_lap: Lap
):
    """ Adds annotations such as speed peaks and valleys and the starting line to the racing line"""

    remove_all_annotation_text_from_figure(race_line)

    decorations = []
    decorations.extend(
        _add_peaks_and_valley_decorations_for_lap(
            last_lap, race_line, color="blue", offset=0
        )
    )
    decorations.extend(
        _add_peaks_and_valley_decorations_for_lap(
            reference_lap, race_line, color="magenta", offset=0
        )
    )
    add_starting_line_to_diagram(race_line, last_lap)

    # This is multiple times faster by adding all texts at once rather than adding them above
    # With around 20 positions, this took 27s before.
    # Maybe this has something to do with every text being transmitted over network
    race_line.center.extend(decorations)

    # Add peaks and valleys of last lap


def _add_peaks_and_valley_decorations_for_lap(
    lap: Lap, race_line: figure, color, offset
):
    (
        peak_speed_data_x,
        peak_speed_data_y,
        valley_speed_data_x,
        valley_speed_data_y,
    ) = lap.get_speed_peaks_and_valleys()

    decorations = []

    for i in range(len(peak_speed_data_x)):
        # shift 10 px to the left
        position_x = lap.data_position_x[peak_speed_data_y[i]]
        position_y = lap.data_position_z[peak_speed_data_y[i]]

        mytext = Label(
            x=position_x,
            y=position_y,
            text_color=color,
            text_font_size="10pt",
            text_font_style="bold",
            x_offset=offset,
            background_fill_color="white",
            background_fill_alpha=0.75,
        )
        mytext.text = "▴%.0f" % peak_speed_data_x[i]

        decorations.append(mytext)

    for i in range(len(valley_speed_data_x)):
        position_x = lap.data_position_x[valley_speed_data_y[i]]
        position_y = lap.data_position_z[valley_speed_data_y[i]]

        mytext = Label(
            x=position_x,
            y=position_y,
            text_color=color,
            text_font_size="10pt",
            x_offset=offset,
            text_font_style="bold",
            background_fill_color="white",
            background_fill_alpha=0.75,
            text_align="right",
        )
        mytext.text = "%.0f▾" % valley_speed_data_x[i]

        decorations.append(mytext)

    return decorations


def remove_all_annotation_text_from_figure(f: figure):
    f.center = [r for r in f.center if not isinstance(r, Label)]


def get_fuel_map_html_table(last_lap):
    fuel_maps = gt7helper.get_fuel_on_consumption_by_relative_fuel_levels(last_lap)
    table = (
        "<table><tr>"
        "<th title='The fuel level relative to the current one'>Fuel Lvl.</th>"
        "<th title='Fuel consumed'>Fuel Cons.</th>"
        "<th title='Laps remaining with this setting'>Laps Rem.</th>"
        "<th title='Time remaining with this setting' >Time Rem.</th>"
        "<th title='Time Diff to last lap with this setting'>Time Diff</th></tr>"
    )
    for fuel_map in fuel_maps:
        no_fuel_consumption = fuel_map.fuel_consumed_per_lap <= 0
        line_style = ""
        if fuel_map.mixture_setting == 0 and not no_fuel_consumption:
            line_style = "background-color:rgba(0,255,0,0.5)"
        table += (
                "<tr id='fuel_map_row_%d' style='%s'>"
                "<td style='text-align:center'>%d</td>"
                "<td style='text-align:center'>%d</td>"
                "<td style='text-align:center'>%.1f</td>"
                "<td style='text-align:center'>%s</td>"
                "<td style='text-align:center'>%s</td>"
                "</tr>"
                % (
                    fuel_map.mixture_setting,
                    line_style,
                    fuel_map.mixture_setting,
                    0 if no_fuel_consumption else fuel_map.fuel_consumed_per_lap,
                    0 if no_fuel_consumption else fuel_map.laps_remaining_on_current_fuel,
                    "No Fuel" if no_fuel_consumption else (gt7helper.seconds_to_lap_time(
                        fuel_map.time_remaining_on_current_fuel / 1000
                    )),
                    "Consumption" if no_fuel_consumption else (gt7helper.seconds_to_lap_time(fuel_map.lap_time_diff / 1000)),
                )
        )
    table += "</table>"
    table += "<p>Fuel Remaining: <b>%d</b></p>" % last_lap.fuel_at_end
    return table


def add_starting_line_to_diagram(race_line: figure, last_lap: Lap):

    if len(last_lap.data_position_z) == 0:
        return

    x = last_lap.data_position_x[0]
    y = last_lap.data_position_z[0]

    # We use a text because scatters are too memory consuming
    # and cannot be easily removed from the diagram
    mytext = Label(
        x=x,
        y=y,
        text_font_size="10pt",
        text_font_style="bold",
        background_fill_color="white",
        background_fill_alpha=0.25,
        text_align="center",
    )
    mytext.text = "===="
    race_line.center.append(mytext)
