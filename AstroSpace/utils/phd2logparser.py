import json
import numpy as np
import pandas as pd
from bokeh.layouts import column, row
from bokeh.models import (
    ColumnDataSource,
    Select,
    Div,
    CustomJS,
    LabelSet,
    WheelZoomTool,
    BoxZoomTool,
    PanTool,
    ResetTool,
)
from bokeh.plotting import figure
from bokeh.embed import file_html
from bokeh.resources import CDN


def parser(phd_log_file: str) -> dict:
    print(f"Parsing PHD2 log file: {phd_log_file}")
    with open(phd_log_file, "r") as f:
        lines = f.readlines()

    idx = []
    for i, line in enumerate(lines):
        if "Begins at" in line:
            idx += [i]
    idx += [len(lines)]

    logs = [lines[s:e] for s, e in zip(idx[:-1], idx[1:])]

    log_dict = {}
    for log in logs:
        log_type, log_date_begin = log[0].strip().split(" Begins at ")
        section_heading = []
        for i in range(len(log)):
            if log[i].startswith("Direction,Step,dx"):
                break
            if log[i].startswith("Frame,Time,mount,dx"):
                break
            section_heading += [log[i]]

        header = log[i].strip().split(",")
        block = []
        events = []
        for i in range(i + 1, len(log)):
            if "calibration complete" in log[i]:
                section_heading += [log[i]]

            elif log_type == "Guiding" and log[i].startswith("INFO: "):
                event = log[i].replace("INFO: ", "").strip()
                if len(block) == 0:
                    events += [[1, event]]
                else:
                    events += [[int(block[-1][0]), event]]

            elif log[i][0].isdigit() or any(
                log[i].lower().startswith(side)
                for side in ["north,", "east,", "west,", "south,", "backlash,"]
            ):
                block += [log[i].strip().split(",")]

        if log_type == "Guiding":
            header += ["error_msg"]
            block = [b if len(b) == 19 else [*b, ""] for b in block]
            df = pd.DataFrame(block, columns=header)

            int_cols = [0, 17]
            df[df.columns[int_cols]] = df[df.columns[int_cols]].astype(int)

            float_cols = [1, 3, 4, 5, 6, 7, 8, 9, 11, 13, 14, 15, 16]
            df[df.columns[float_cols]] = (
                df[df.columns[float_cols]].replace("", "0.0").astype(float)
            )

            df.set_index("Frame", inplace=True)

            start, end = [], []
            for frame, event in events:
                if "started" in event.lower():
                    start += [frame]
                elif any(
                    [finish in event.lower() for finish in ["complete", "failed"]]
                ):
                    end += [frame]
            idx = [se for s, e in zip(start, end) for se in range(s, e + 1)]
            df["event"] = 0
            df.loc[idx, "event"] = 1

            df["event_text"] = ""
            for frame, event in events:
                df.loc[frame, "event_text"] += event + "|"

        else:
            df = pd.DataFrame(block, columns=header)
            df["Step"] = df["Step"].astype(int)
            df[df.columns[2:]] = df[df.columns[2:]].astype(float)
        log_dict[log_type, log_date_begin] = df, section_heading
    return log_dict

def get_data(log_dict, p_type):
    px_scale = 1
    initial_stats = ""
    stats_dict = {}
    data_dict = {}
    heading_dict = {}
    cal_dict = {}
    # --- Extract data for plotting ---
    for (l_type, l_date), (df, heading) in log_dict.items():
        options_key = l_type + " " + l_date
        if l_type == p_type:
            if p_type == "Calibration":

                df["color"] = df["Direction"].map(
                    {
                        "West": "blue",
                        "East": "blue",
                        "North": "red",
                        "South": "red",
                        "Backlash": "red",
                    }
                )
                df["alpha"] = 1.0
                df.loc[
                    df["Direction"].isin(["East", "South", "Backlash"]), "alpha"
                ] = 0.5
                df["label"] = df["Direction"].str[0] + df["Step"].astype(str)

                try:
                    wdf = df.query("Direction == 'West'")
                    wx, wy = wdf.loc[wdf.index[wdf["Step"].argmax()], ["dx", "dy"]]
                    ndf = df.query("Direction == 'North'")
                    nx, ny = ndf.loc[ndf.index[ndf["Step"].argmax()], ["dx", "dy"]]
                except Exception:
                    wx, wy, nx, ny = 0, 0, 0, 0

                cal_dict[options_key] = {
                            "west_angle_x": [0, wx],
                            "west_angle_y": [0, wy],
                            "north_angle_x": [0, nx],
                            "north_angle_y": [0, ny],
                            }

            for il in heading:
                if il.startswith("Pixel Scale"):
                    px_scale = float(
                        il.split("Pixel Scale = ")[1].split(" arc-sec")[0]
                    )
            if "Time" in df.columns:
                df["Time"] = (
                    pd.Timestamp(l_date)
                    + pd.to_timedelta(df["Time"].values, unit="s")
                ).astype(np.int64) // 10**6  # milliseconds
                df["Twidth"] = np.diff(
                    df["Time"].values, prepend=df["Time"].values[0]
                )
                idf = df.query("event == 0")
                rms_ra = (idf["RARawDistance"] ** 2).mean() ** 0.5
                rms_dec = (idf["DECRawDistance"] ** 2).mean() ** 0.5
                rms = (rms_ra**2 + rms_dec**2) ** 0.5
                peak_ra = idf["RARawDistance"].abs().max()
                peak_dec = idf["DECRawDistance"].abs().max()

                stats_dict[options_key] = f"""
                <table>
                    <tr><td></td><th>RMS</th><th>Peak</th></tr>                    

                    <tr><th>RA</th><td>{rms_ra * px_scale:.2f}" ({rms_ra:.2f} px)</td><td>{peak_ra * px_scale:.2f}" ({peak_ra:.2f} px)</td></tr>      
                    <tr><th>Dec</th><td>{rms_dec * px_scale:.2f}" ({rms_dec:.2f} px)</td><td>{peak_dec * px_scale:.2f}" ({peak_dec:.2f} px)</td></tr>               
                    <tr><th>Total</th><td>{rms * px_scale:.2f}" ({rms:.2f} px)</td><td></td></tr>    

                </table>
                """

            if "RARawDistance" in df.columns:
                df["RARawDistance"] = df["RARawDistance"] * -1
            if "DECGuideDistance" in df.columns:
                df["DECGuideDistance"] = df["DECGuideDistance"] * -1
            data_dict[options_key] = df.to_dict(orient="list")
            heading_dict[options_key] = "".join(
                ["<pre>" + ih + "</pre>" for ih in heading]
                )

        # --- Extract JS-safe JSON string for embedding in CustomJS ---
    data_js = json.dumps(data_dict)
    keys = [k for k in data_dict if k.startswith(p_type)]
    source = ColumnDataSource(data_dict[keys[0]])
    initial_heading = heading_dict[keys[0]]
    heading_js = json.dumps(heading_dict)
    if stats_dict != {}:
        initial_stats = stats_dict[keys[0]]
    stats_js = json.dumps(stats_dict)
    return (
        data_js,
        keys,
        source,
        initial_heading,
        heading_js,
        px_scale,
        initial_stats,
        stats_js,
        cal_dict
    )
    
def bokeh_phd2(log_paths):
    logs = log_paths.split(",")
    log_dict = {}
    for log in logs:
        log_dict.update(parser(log))

    #%% Guiding Plots
    (
    data_js,
    keys,
    source,
    initial_heading,
    heading_js,
    px_scale,
    initial_stats,
    stats_js,
    _
    ) = get_data(log_dict, "Guiding")
    
    p1 = figure(title="Guiding", x_axis_type="datetime", height=400)
    p1.yaxis.axis_label = "pixels"
    # for y_col, color, label in zip(y_cols, ["blue", "red"], legend_labels):
    p1.line(
        "Time",
        "RARawDistance",
        source=source,
        line_color="blue",
        legend_label="RA",
    )

    p1.line(
        "Time",
        "DECRawDistance",
        source=source,
        line_color="red",
        legend_label="Dec",
    )

    p1.vbar(
        x="Time",
        top="RAGuideDistance",
        source=source,
        line_color="blue",
        line_width=0.5,
        fill_color=None,
        width="Twidth",
    )
    p1.vbar(
        x="Time",
        top="DECGuideDistance",
        source=source,
        line_color="red",
        line_width=0.5,
        fill_color=None,
        width="Twidth",
    )

    # Define interaction tools
    wheel_zoom = WheelZoomTool(dimensions="width")  # Scroll = zoom X
    box_zoom_y = BoxZoomTool(dimensions="height")  # Drag up/down = zoom Y
    pan_x = PanTool(dimensions="width")  # Drag left/right = pan X
    reset = ResetTool()

    # Add tools to plot
    p1.add_tools(wheel_zoom, box_zoom_y, pan_x, reset)

    # Set active tools
    p1.toolbar.active_scroll = wheel_zoom  # Scroll = zoom X
    p1.toolbar.active_drag = None  # Let both pan and box_zoom_y respond

    dropdown = Select(value=keys[0], options=keys)

    # Create a text widget
    sec_heading = Div(
        text=initial_heading,
        height=200,
    styles={
        "overflow": "auto",  # keep this if content may be long
        "border": "1px solid lightgray",
        "padding": "5px",
        "white-space": "normal",     # ✅ allow text to wrap
        "word-wrap": "break-word",   # ✅ break long words if needed
        "color": "grey",
    },
    sizing_mode="stretch_width",     # ✅ make it responsive to container
)

    # Create a text widget
    stats_div = Div(
        text=initial_stats,
        styles={
            "overflow": "auto",
            "border": "1px solid lightgray",
            "padding": "5px",
            "color": "grey",
        },
    )

    callback = CustomJS(
        args=dict(source=source, select=dropdown, div=sec_heading, s_div=stats_div),
        code=f"""
            const datasets = {data_js};
            const heads = {heading_js};
            
            const selected = select.value;
        
            source.data = datasets[selected];
            source.change.emit();
            div.text = heads[selected];

            const stats = {stats_js};
            s_div.text = stats[selected];
        """,
    )

    dropdown.js_on_change("value", callback)
    p1.sizing_mode = "stretch_width"
    col1 = column(row(column(dropdown,stats_div), sec_heading), p1, sizing_mode="stretch_width"
    )

    ##################################################
    #%%calibration Plots
    (
    c_data_js,
    c_keys,
    c_source,
    c_initial_heading,
    c_heading_js,
    c_px_scale,
    _,
    _,
    cal_dict
) = get_data(log_dict, "Calibration")
    
    cal_source = ColumnDataSource(cal_dict[c_keys[0]])
    cal_source_js = json.dumps(cal_dict)    
    p2 = figure(
        title="Calibration",
        height=400,
        width=400,
        # x_range=(-max_radius, max_radius),
        # y_range=(-max_radius, max_radius),
        match_aspect=True,
        # sizing_mode="stretch_width",
    )
    p2.scatter(
        "dx", "dy", source=c_source, color="color", fill_alpha="alpha", size=10
    )
    labels = LabelSet(
        x="dx",
        y="dy",
        text="label",
        source=c_source,
        x_offset=5,
        y_offset=5,
        text_font_size="8pt",
    )
    p2.add_layout(labels)

    # Circular grid rings
    for r in range(5, int(30) + 5, 5):
        p2.circle(
            x=0,
            y=0,
            radius=r,
            fill_color=None,
            line_color="grey",
            line_dash="dotted",
        )

    # Calibration angles (degrees to radians)
    p2.line("west_angle_x","west_angle_y", source=cal_source, line_color="blue", line_width=2, legend_label="West")
    p2.line("north_angle_x","north_angle_y", source=cal_source, line_color="red", line_width=2, legend_label="North")

    p2.legend.location = "bottom_right"

    c_dropdown = Select(value=c_keys[0], options=c_keys)
    
    # Create a text widget
    c_sec_heading = Div(
        text=c_initial_heading,
            styles={
        "overflow": "auto",  # keep this if content may be long
        "border": "1px solid lightgray",
        "padding": "5px",
        "white-space": "normal",     # ✅ allow text to wrap
        "word-wrap": "break-word",   # ✅ break long words if needed
        "color": "grey",
    },
    css_classes=["calibration-heading"],
    )

    c_callback = CustomJS(
        args=dict(c_source=c_source, c_select=c_dropdown, div=c_sec_heading,cal_source=cal_source),
        code=f"""
            const datasets = {c_data_js};
            const heads = {c_heading_js};
            const cal = {cal_source_js};
            
            const selected = c_select.value;
        
            c_source.data = datasets[selected];
            c_source.change.emit();

            cal_source.data = cal[selected];
            cal_source.change.emit();

            div.text = heads[selected];
        """,
    )
    c_dropdown.js_on_change("value", c_callback)

    col2 = column(c_dropdown, c_sec_heading, p2, sizing_mode="stretch_width")


    html1 = file_html(col1, CDN, "PHD2 Guiding Graphs")
    html2 = file_html(col2, CDN, "PHD2 Calibration Graphs")
    return (html1, html2)