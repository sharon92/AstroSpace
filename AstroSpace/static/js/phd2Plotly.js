function setPanelLines(container, lines) {
    container.replaceChildren();
    const safeLines = Array.isArray(lines) ? lines.filter(Boolean) : [];

    if (safeLines.length === 0) {
        const empty = document.createElement("p");
        empty.className = "text-sm text-gray-500 dark:text-gray-400";
        empty.textContent = "No metadata available.";
        container.appendChild(empty);
        return;
    }

    const pre = document.createElement("pre");
    pre.className = "whitespace-pre-wrap break-words text-xs text-gray-700 dark:text-gray-300";
    pre.textContent = safeLines.join("\n");
    container.appendChild(pre);
}

function setMessage(container, message) {
    container.replaceChildren();
    const note = document.createElement("p");
    note.className = "text-sm text-gray-500 dark:text-gray-400";
    note.textContent = message;
    container.appendChild(note);
}

function setStats(container, stats) {
    container.replaceChildren();
    if (!stats) {
        setMessage(container, "No statistics available.");
        return;
    }

    const normalizeZero = value => Math.abs(Number(value) || 0) < 0.0005 ? 0 : Number(value);
    const formatNumber = (value, digits = 2) => normalizeZero(value).toFixed(digits);
    const formatMetric = (arcsec, pixels) => `${formatNumber(arcsec)}" (${formatNumber(pixels)} px)`;
    const rows = [
        ["RA", formatMetric(stats.rms_ra_arcsec, stats.rms_ra_pixels), formatMetric(stats.peak_ra_arcsec, stats.peak_ra_pixels)],
        ["Dec", formatMetric(stats.rms_dec_arcsec, stats.rms_dec_pixels), formatMetric(stats.peak_dec_arcsec, stats.peak_dec_pixels)],
        ["Total", formatMetric(stats.rms_total_arcsec, stats.rms_total_pixels), formatMetric(stats.peak_total_arcsec, stats.peak_total_pixels)],
    ];

    const scale = document.createElement("p");
    scale.className = "mb-2 text-xs font-semibold text-gray-600 dark:text-gray-300";
    scale.textContent = `Pixel scale: ${formatNumber(stats.pixel_scale)}" / px`;
    container.appendChild(scale);

    const table = document.createElement("table");
    table.className = "w-full table-auto text-sm text-left border-collapse";

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["", "RMS", "Peak"].forEach((label, index) => {
        const cell = document.createElement(index === 0 ? "th" : "td");
        cell.className = "border-b border-gray-200 py-1 pr-4 font-semibold text-gray-700 dark:border-gray-700 dark:text-gray-200";
        cell.textContent = label;
        headerRow.appendChild(cell);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    rows.forEach(([label, rmsValue, peakValue]) => {
        const row = document.createElement("tr");
        row.className = "border-b border-gray-200 dark:border-gray-700";

        const labelCell = document.createElement("th");
        labelCell.className = "py-1 pr-4 font-semibold text-gray-700 dark:text-gray-200";
        labelCell.textContent = label;

        const rmsCell = document.createElement("td");
        rmsCell.className = "py-1 pr-4 text-gray-600 dark:text-gray-300";
        rmsCell.textContent = rmsValue;

        const peakCell = document.createElement("td");
        peakCell.className = "py-1 text-gray-600 dark:text-gray-300";
        peakCell.textContent = peakValue;

        row.append(labelCell, rmsCell, peakCell);
        tbody.appendChild(row);
    });
    table.appendChild(tbody);

    container.appendChild(table);
}

function buildSessionMap(payload) {
    const sessions = Array.isArray(payload?.sessions) ? payload.sessions : [];
    return new Map(sessions.map(session => [session.key, session]));
}

function defaultSessionKey(payload, sessionKeys, sessions) {
    return sessionKeys[sessionKeys.length - 1];
}

function squarePlotHeight(plot, fallback = 640) {
    const width = plot.clientWidth || plot.parentElement?.clientWidth || fallback;
    return Math.max(320, Math.round(width));
}

function toFiniteNumber(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizedGuidingRows(session) {
    const time = Array.isArray(session?.series?.time) ? session.series.time : [];
    return time.map((timestamp, index) => ({
        time: timestamp,
        raRaw: toFiniteNumber(session?.series?.ra_raw?.[index]),
        decRaw: toFiniteNumber(session?.series?.dec_raw?.[index]),
        raGuide: toFiniteNumber(session?.series?.ra_guide?.[index]),
        decGuide: toFiniteNumber(session?.series?.dec_guide?.[index]),
    }));
}

function buildGuidingTraces(session) {
    const rows = normalizedGuidingRows(session);
    if (rows.length === 0) {
        return [];
    }

    const time = rows.map(row => row.time);
    const raRaw = rows.map(row => row.raRaw);
    const decRaw = rows.map(row => row.decRaw);
    const raGuide = rows.map(row => row.raGuide);
    const decGuide = rows.map(row => row.decGuide);
    const traces = [
        {
            x: time,
            y: raRaw,
            type: "scattergl",
            mode: "lines",
            name: "RA Raw",
            line: { color: "#2563eb", width: 2 },
        },
        {
            x: time,
            y: decRaw,
            type: "scattergl",
            mode: "lines",
            name: "Dec Raw",
            line: { color: "#dc2626", width: 2 },
        },
    ];

    if (raGuide.some(value => value !== 0)) {
        traces.push({
            x: time,
            y: raGuide,
            type: "bar",
            name: "RA Guide",
            marker: { color: "rgba(37,99,235,0.25)" },
            yaxis: "y2",
        });
    }

    if (decGuide.some(value => value !== 0)) {
        traces.push({
            x: time,
            y: decGuide,
            type: "bar",
            name: "Dec Guide",
            marker: { color: "rgba(220,38,38,0.25)" },
            yaxis: "y2",
        });
    }

    if (Array.isArray(session.events) && session.events.length > 0) {
        const peak = Math.max(
            ...raRaw.map(value => Math.abs(value)),
            ...decRaw.map(value => Math.abs(value)),
            1,
        );

        traces.push({
            x: session.events.map(event => event.time),
            y: session.events.map(() => peak),
            type: "scatter",
            mode: "markers",
            name: "Events",
            marker: {
                color: "#f59e0b",
                size: 10,
                symbol: "diamond",
                line: { color: "#111827", width: 1 },
            },
            customdata: session.events.map(event => event.label),
            hovertemplate: "%{customdata}<extra></extra>",
        });
    }

    return traces;
}

export function renderGuidingPlot(rootId, payload) {
    const root = document.getElementById(rootId);
    if (!root) return;

    const select = root.querySelector("[data-role='session']");
    const stats = root.querySelector("[data-role='stats']");
    const heading = root.querySelector("[data-role='heading']");
    const plot = root.querySelector("[data-role='plot']");

    if (!payload || payload.legacy) {
        const message = payload?.message ?? "No guiding plot has been generated yet.";
        setMessage(stats, message);
        setMessage(heading, message);
        plot.replaceChildren();
        return;
    }

    const sessions = buildSessionMap(payload);
    if (sessions.size === 0) {
        setMessage(stats, "No guiding sessions found in the uploaded logs.");
        setMessage(heading, "No guiding metadata available.");
        plot.replaceChildren();
        return;
    }

    const sessionKeys = [...sessions.keys()];
    select.replaceChildren();
    sessionKeys.forEach(key => {
        const option = document.createElement("option");
        option.value = key;
        option.textContent = key;
        select.appendChild(option);
    });

    const render = () => {
        const session = sessions.get(select.value) ?? sessions.get(payload.default_session) ?? sessions.values().next().value;
        if (!session) return;

        setStats(stats, session.stats);
        setPanelLines(heading, session.heading_lines);
        const traces = buildGuidingTraces(session);
        if (traces.length === 0) {
            setMessage(stats, "No guiding data points were found in the uploaded logs.");
            plot.replaceChildren();
            return;
        }

        const rawValues = traces
            .filter(trace => trace.yaxis !== "y2")
            .flatMap(trace => trace.y ?? [])
            .map(value => Math.abs(toFiniteNumber(value)));
        const guideValues = traces
            .filter(trace => trace.yaxis === "y2")
            .flatMap(trace => trace.y ?? [])
            .map(value => Math.abs(toFiniteNumber(value)));
        const rawExtent = Math.max(...rawValues, 1);
        const guideExtent = Math.max(...guideValues, 1);

        Plotly.react(
            plot,
            traces,
            {
                barmode: "overlay",
                hovermode: "x unified",
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
                margin: { t: 30, r: 60, b: 40, l: 50 },
                legend: { orientation: "h", x: 0.5, y: 1.12, xanchor: "center" },
                xaxis: { title: "Time" },
                yaxis: {
                    title: "Raw Error (px)",
                    zeroline: true,
                    gridcolor: "rgba(148,163,184,0.2)",
                    range: [-(rawExtent * 1.15), rawExtent * 1.15],
                },
                yaxis2: {
                    title: "Guide Pulses (px)",
                    overlaying: "y",
                    side: "right",
                    showgrid: false,
                    range: [-(guideExtent * 1.15), guideExtent * 1.15],
                },
            },
            { responsive: true, displaylogo: false }
        );
    };

    select.value = defaultSessionKey(payload, sessionKeys, sessions);
    select.onchange = render;
    render();
}

function buildCalibrationShapes(axisLimit) {
    const shapes = [];
    for (let radius = 5; radius <= axisLimit; radius += 5) {
        shapes.push({
            type: "circle",
            xref: "x",
            yref: "y",
            x0: -radius,
            x1: radius,
            y0: -radius,
            y1: radius,
            line: {
                color: "rgba(148,163,184,0.25)",
                dash: "dot",
                width: 1,
            },
        });
    }
    return shapes;
}

function normalizedCalibrationPoints(session) {
    const dx = Array.isArray(session?.points?.dx) ? session.points.dx : [];
    const dy = Array.isArray(session?.points?.dy) ? session.points.dy : [];
    const direction = Array.isArray(session?.points?.direction) ? session.points.direction : [];
    const label = Array.isArray(session?.points?.label) ? session.points.label : [];
    const color = Array.isArray(session?.points?.color) ? session.points.color : [];
    const alpha = Array.isArray(session?.points?.alpha) ? session.points.alpha : [];
    const maxLength = Math.min(
        dx.length,
        dy.length,
        direction.length || dx.length,
        label.length || dx.length,
        color.length || dx.length,
        alpha.length || dx.length,
    );

    return Array.from({ length: maxLength }, (_, index) => ({
        dx: toFiniteNumber(dx[index]),
        dy: toFiniteNumber(dy[index]),
        direction: direction[index],
        label: label[index],
        color: color[index],
        alpha: toFiniteNumber(alpha[index], 1),
    }));
}

export function renderCalibrationPlot(rootId, payload) {
    const root = document.getElementById(rootId);
    if (!root) return;

    const select = root.querySelector("[data-role='session']");
    const heading = root.querySelector("[data-role='heading']");
    const plot = root.querySelector("[data-role='plot']");

    if (!payload || payload.legacy) {
        const message = payload?.message ?? "No calibration plot has been generated yet.";
        setMessage(heading, message);
        plot.replaceChildren();
        return;
    }

    const sessions = buildSessionMap(payload);
    if (sessions.size === 0) {
        setMessage(heading, "No calibration sessions found in the uploaded logs.");
        plot.replaceChildren();
        return;
    }

    const sessionKeys = [...sessions.keys()];
    select.replaceChildren();
    sessionKeys.forEach(key => {
        const option = document.createElement("option");
        option.value = key;
        option.textContent = key;
        select.appendChild(option);
    });

    const render = () => {
        const session = sessions.get(select.value) ?? sessions.get(payload.default_session) ?? sessions.values().next().value;
        if (!session) return;

        setPanelLines(heading, session.heading_lines);
        const points = normalizedCalibrationPoints(session);
        if (points.length === 0) {
            setMessage(heading, "No calibration points were found in the uploaded logs.");
            plot.replaceChildren();
            return;
        }

        const axisLimit = Math.max(
            toFiniteNumber(session.axis_limit, 5),
            ...points.map(point => Math.max(Math.abs(point.dx), Math.abs(point.dy))),
            5,
        );

        const traces = [
            {
                x: points.map(point => point.dx),
                y: points.map(point => point.dy),
                type: "scatter",
                mode: points.length <= 30 ? "markers+text" : "markers",
                text: points.map(point => point.label),
                textposition: "top center",
                hovertemplate: "%{text}<br>%{x}, %{y}<extra></extra>",
                marker: {
                    size: 10,
                    color: points.map(point => point.color),
                    opacity: points.map(point => point.alpha),
                    line: { color: "#111827", width: 1 },
                },
                name: "Calibration Steps",
            },
            {
                x: [session.vectors.west[0], session.vectors.west[1]],
                y: [session.vectors.west[2], session.vectors.west[3]],
                type: "scatter",
                mode: "lines+markers",
                line: { color: "#2563eb", width: 3 },
                marker: { size: 8 },
                name: "West Vector",
            },
            {
                x: [session.vectors.north[0], session.vectors.north[1]],
                y: [session.vectors.north[2], session.vectors.north[3]],
                type: "scatter",
                mode: "lines+markers",
                line: { color: "#dc2626", width: 3 },
                marker: { size: 8 },
                name: "North Vector",
            },
        ];

        Plotly.react(
            plot,
            traces,
            {
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
                hovermode: "closest",
                height: squarePlotHeight(plot),
                margin: { t: 30, r: 30, b: 50, l: 50 },
                legend: { orientation: "h", x: 0.5, y: 1.12, xanchor: "center" },
                xaxis: {
                    title: "dx (px)",
                    range: [-axisLimit, axisLimit],
                    zeroline: true,
                    gridcolor: "rgba(148,163,184,0.2)",
                },
                yaxis: {
                    title: "dy (px)",
                    range: [-axisLimit, axisLimit],
                    scaleanchor: "x",
                    scaleratio: 1,
                    zeroline: true,
                    gridcolor: "rgba(148,163,184,0.2)",
                },
                shapes: buildCalibrationShapes(Math.ceil(axisLimit / 5) * 5),
            },
            { responsive: true, displaylogo: false }
        );
    };

    select.value = defaultSessionKey(payload, sessionKeys, sessions);
    select.onchange = render;
    render();
}
