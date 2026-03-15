import json

import pandas as pd


def legacy_plot_payload(title, message=None):
    return {
        "kind": title.lower(),
        "legacy": True,
        "message": message
        or f"{title} plot was generated with a legacy renderer. Re-save the image to regenerate it.",
    }


def parser(phd_log_file: str) -> dict:
    print(f"Parsing PHD2 log file: {phd_log_file}")
    with open(phd_log_file, "r", encoding="utf-8", errors="ignore") as handle:
        lines = handle.readlines()

    indices = [i for i, line in enumerate(lines) if "Begins at" in line]
    indices.append(len(lines))
    logs = [lines[start:end] for start, end in zip(indices[:-1], indices[1:])]

    log_dict = {}
    for log in logs:
        if not log:
            continue

        log_type, log_date_begin = log[0].strip().split(" Begins at ")
        section_heading = []
        for i in range(len(log)):
            if log[i].startswith("Direction,Step,dx"):
                break
            if log[i].startswith("Frame,Time,mount,dx"):
                break
            section_heading.append(log[i].strip())
        else:
            continue

        header = log[i].strip().split(",")
        block = []
        events = []
        for i in range(i + 1, len(log)):
            line = log[i].strip()
            if not line:
                continue

            if "calibration complete" in line.lower():
                section_heading.append(line)
            elif log_type == "Guiding" and line.startswith("INFO: "):
                event = line.replace("INFO: ", "").strip()
                frame = 1 if not block else int(block[-1][0])
                events.append([frame, event])
            elif line[0].isdigit() or any(
                line.lower().startswith(side)
                for side in ["north,", "east,", "west,", "south,", "backlash,"]
            ):
                block.append(line.split(","))

        if not block:
            continue

        if log_type == "Guiding":
            header += ["error_msg"]
            block = _normalize_rows(block, len(header))
            df = pd.DataFrame(block, columns=header)

            _coerce_numeric_columns(
                df,
                int_columns=[df.columns[0], df.columns[17]],
                float_columns=[
                    df.columns[1],
                    df.columns[3],
                    df.columns[4],
                    df.columns[5],
                    df.columns[6],
                    df.columns[7],
                    df.columns[8],
                    df.columns[9],
                    df.columns[11],
                    df.columns[13],
                    df.columns[14],
                    df.columns[15],
                    df.columns[16],
                ],
            )

            df.set_index(df.columns[0], inplace=True)
            df.index.name = "Frame"
            df["event"] = 0
            df["event_text"] = ""

            start_frames, end_frames = [], []
            for frame, event in events:
                if "started" in event.lower():
                    start_frames.append(frame)
                elif any(finish in event.lower() for finish in ["complete", "failed"]):
                    end_frames.append(frame)

            for start, end in zip(start_frames, end_frames):
                df.loc[start:end, "event"] = 1

            for frame, event in events:
                if frame in df.index:
                    df.loc[frame, "event_text"] += event + "|"
        else:
            block = _normalize_rows(block, len(header))
            df = pd.DataFrame(block, columns=header)
            _coerce_numeric_columns(
                df,
                int_columns=["Step"],
                float_columns=df.columns[2:],
            )

        log_dict[(log_type, log_date_begin)] = (df, section_heading)

    return log_dict


def _pixel_scale_from_heading(heading_lines):
    for line in heading_lines:
        if line.startswith("Pixel Scale"):
            try:
                return float(line.split("Pixel Scale = ")[1].split(" arc-sec")[0])
            except (IndexError, ValueError):
                return 1.0
    return 1.0


def _normalize_rows(rows, expected_length):
    normalized = []
    for row in rows:
        if len(row) < expected_length:
            row = [*row, *([""] * (expected_length - len(row)))]
        elif len(row) > expected_length:
            row = [*row[: expected_length - 1], ",".join(row[expected_length - 1 :])]
        normalized.append(row)
    return normalized


def _coerce_numeric_columns(frame, int_columns=None, float_columns=None):
    for column in ([] if int_columns is None else int_columns):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).astype(int)

    for column in ([] if float_columns is None else float_columns):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0).astype(float)


def _series_values(frame, column, default=0.0):
    if column not in frame.columns:
        return [default] * len(frame.index)
    return frame[column].fillna(default).round(4).tolist()


def _signed_peak(series):
    if series.empty:
        return 0.0

    peak_index = series.abs().idxmax()
    return float(series.loc[peak_index])


def _build_guiding_payload(log_dict):
    sessions = []
    for (log_type, log_date), (df, heading_lines) in log_dict.items():
        if log_type != "Guiding":
            continue

        if "Time" not in df.columns:
            continue

        px_scale = _pixel_scale_from_heading(heading_lines)
        frame = df.copy()
        frame["Time"] = (
            pd.Timestamp(log_date) + pd.to_timedelta(frame["Time"].values, unit="s")
        )
        frame["RARawDistance"] = frame.get("RARawDistance", 0.0) * -1
        if "DECGuideDistance" in frame.columns:
            frame["DECGuideDistance"] = frame["DECGuideDistance"] * -1

        event_rows = frame[frame["event_text"].astype(str) != ""]
        metrics = frame[frame["event"] == 0]
        rms_ra = float((metrics["RARawDistance"] ** 2).mean() ** 0.5) if not metrics.empty else 0.0
        rms_dec = float((metrics["DECRawDistance"] ** 2).mean() ** 0.5) if not metrics.empty else 0.0
        rms_total = float((rms_ra**2 + rms_dec**2) ** 0.5)
        peak_ra = _signed_peak(metrics["RARawDistance"]) if not metrics.empty else 0.0
        peak_dec = _signed_peak(metrics["DECRawDistance"]) if not metrics.empty else 0.0
        peak_total = (
            float((((metrics["RARawDistance"] ** 2) + (metrics["DECRawDistance"] ** 2)) ** 0.5).max())
            if not metrics.empty
            else 0.0
        )

        sessions.append(
            {
                "key": f"{log_type} {log_date}",
                "heading_lines": heading_lines,
                "stats": {
                    "pixel_scale": px_scale,
                    "rms_ra_arcsec": round(rms_ra * px_scale, 3),
                    "rms_dec_arcsec": round(rms_dec * px_scale, 3),
                    "rms_total_arcsec": round(rms_total * px_scale, 3),
                    "peak_ra_arcsec": round(peak_ra * px_scale, 3),
                    "peak_dec_arcsec": round(peak_dec * px_scale, 3),
                    "peak_total_arcsec": round(peak_total * px_scale, 3),
                    "rms_ra_pixels": round(rms_ra, 3),
                    "rms_dec_pixels": round(rms_dec, 3),
                    "rms_total_pixels": round(rms_total, 3),
                    "peak_ra_pixels": round(peak_ra, 3),
                    "peak_dec_pixels": round(peak_dec, 3),
                    "peak_total_pixels": round(peak_total, 3),
                },
                "series": {
                    "time": [value.isoformat() for value in frame["Time"]],
                    "ra_raw": _series_values(frame, "RARawDistance"),
                    "dec_raw": _series_values(frame, "DECRawDistance"),
                    "ra_guide": _series_values(frame, "RAGuideDistance"),
                    "dec_guide": _series_values(frame, "DECGuideDistance"),
                },
                "events": [
                    {
                        "time": time.isoformat(),
                        "label": "|".join(part for part in text.split("|") if part),
                    }
                    for time, text in zip(event_rows["Time"], event_rows["event_text"])
                ],
            }
        )

    return {
        "kind": "guiding",
        "default_session": sessions[-1]["key"] if sessions else None,
        "sessions": sessions,
    }


def _build_calibration_payload(log_dict):
    sessions = []
    for (log_type, log_date), (df, heading_lines) in log_dict.items():
        if log_type != "Calibration":
            continue

        frame = df.copy()
        frame["color"] = frame["Direction"].map(
            {
                "West": "#2563eb",
                "East": "#2563eb",
                "North": "#dc2626",
                "South": "#dc2626",
                "Backlash": "#dc2626",
            }
        )
        frame["alpha"] = 1.0
        frame.loc[frame["Direction"].isin(["East", "South", "Backlash"]), "alpha"] = 0.5
        frame["label"] = frame["Direction"].str[0] + frame["Step"].astype(str)

        west = frame.query("Direction == 'West'")
        north = frame.query("Direction == 'North'")
        wx, wy = west.loc[west["Step"].idxmax(), ["dx", "dy"]] if not west.empty else (0.0, 0.0)
        nx, ny = north.loc[north["Step"].idxmax(), ["dx", "dy"]] if not north.empty else (0.0, 0.0)
        axis_limit = max(
            5.0,
            float(frame[["dx", "dy"]].abs().max().max()) + 5,
            abs(float(wx)) + 5,
            abs(float(wy)) + 5,
            abs(float(nx)) + 5,
            abs(float(ny)) + 5,
        )

        sessions.append(
            {
                "key": f"{log_type} {log_date}",
                "heading_lines": heading_lines,
                "axis_limit": round(axis_limit, 3),
                "vectors": {
                    "west": [0.0, float(wx), 0.0, float(wy)],
                    "north": [0.0, float(nx), 0.0, float(ny)],
                },
                "points": {
                    "dx": frame["dx"].round(4).tolist(),
                    "dy": frame["dy"].round(4).tolist(),
                    "direction": frame["Direction"].tolist(),
                    "label": frame["label"].tolist(),
                    "color": frame["color"].tolist(),
                    "alpha": frame["alpha"].tolist(),
                },
            }
        )

    return {
        "kind": "calibration",
        "default_session": sessions[-1]["key"] if sessions else None,
        "sessions": sessions,
    }


def build_plotly_payloads(log_paths):
    log_dict = {}
    for path in filter(None, log_paths.split(",")):
        log_dict.update(parser(path))

    return _build_guiding_payload(log_dict), _build_calibration_payload(log_dict)


def deserialize_plot_payload(raw_payload, title):
    if not raw_payload:
        return None

    if isinstance(raw_payload, dict):
        return raw_payload

    try:
        payload = json.loads(raw_payload)
    except (TypeError, json.JSONDecodeError):
        return legacy_plot_payload(title)

    if isinstance(payload, dict):
        return payload

    return legacy_plot_payload(title, f"Stored {title.lower()} payload is not valid JSON.")
