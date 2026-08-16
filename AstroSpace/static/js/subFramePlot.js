const DATE_AXIS_CANDIDATES = ["DATE-OBS", "DATE-AVG", "DATE-LOC"];

const PLOT_PRESET_DEFINITIONS = [
    {
        id: "night-overview",
        label: "Night overview",
        description: "Air mass, altitude, sky brightness, and cloud conditions across the capture.",
        groups: [
            { candidates: ["AIRMASS", "CENTALT"], type: "line" },
            { candidates: ["SUNANGLE", "MOONANGL"], type: "line" },
            { candidates: ["CLOUDCVR"], type: "scatter" },
        ],
    },
    {
        id: "thermal-humidity",
        label: "Temperature & humidity",
        description: "Ambient, sensor, dew-point, and humidity trends for spotting thermal changes.",
        groups: [
            { candidates: ["AMBTEMP", "CCD-TEMP", "DEWPOINT"], type: "line" },
            { candidates: ["HUMIDITY"], type: "line" },
            { candidates: ["PRESSURE"], type: "scatter" },
        ],
    },
    {
        id: "wind-pressure",
        label: "Wind & pressure",
        description: "Wind speed, direction, gusts, and pressure during the session.",
        groups: [
            { candidates: ["WINDSPD", "WINDGUST"], type: "line" },
            { candidates: ["WINDDIR"], type: "scatter" },
            { candidates: ["PRESSURE"], type: "line" },
        ],
    },
    {
        id: "pointing",
        label: "Pointing & orientation",
        description: "Target coordinates and rotation metadata over time.",
        groups: [
            { candidates: ["RA", "OBJCTRA"], type: "line" },
            { candidates: ["DEC", "OBJCTDEC"], type: "line" },
            { candidates: ["OBJCTROT"], type: "scatter" },
        ],
    },
    {
        id: "frame-quality",
        label: "Frame quality",
        description: "Available focus, star-shape, signal, and stacking-quality measurements.",
        groups: [
            { candidates: ["FWHM", "HFR", "HFD", "SNR", "STARCOUNT"], type: "line" },
            { candidates: ["ECCENTRICITY", "ROUNDNESS", "BACKGROUND"], type: "scatter" },
            { candidates: ["WBPP weight 1", "WBPP weight 2", "WBPP weight 3"], type: "line" },
        ],
    },
];

const PLOT_COLORS = [
    "#2563eb",
    "#dc2626",
    "#16a34a",
    "#d97706",
    "#7c3aed",
    "#0891b2",
    "#db2777",
    "#4f46e5",
];

function metadataKeys(metaVariable) {
    return Object.keys(metaVariable || {}).filter(key => key !== "_files");
}

function isNumericSeries(values) {
    return Array.isArray(values) && values.some(value => {
        if (value === null || value === undefined || value === "") return false;
        return Number.isFinite(Number(value));
    });
}

function isDateSeries(values) {
    return Array.isArray(values) && values.some(value => {
        if (typeof value !== "string" || !value.trim()) return false;
        return Number.isFinite(Date.parse(value));
    });
}

function numericKeys(metaVariable) {
    return metadataKeys(metaVariable).filter(key => isNumericSeries(metaVariable[key]));
}

function chooseXKey(metaVariable, keys = metadataKeys(metaVariable)) {
    return DATE_AXIS_CANDIDATES.find(key => keys.includes(key))
        || keys.find(key => isDateSeries(metaVariable[key]))
        || keys.find(key => isNumericSeries(metaVariable[key]))
        || keys[0];
}

function resolvePresetGroups(metaVariable, definition) {
    const numeric = new Set(numericKeys(metaVariable));
    return definition.groups
        .map(group => ({
            keys: group.candidates.filter(key => numeric.has(key)),
            type: group.type,
        }))
        .filter(group => group.keys.length > 0);
}

export function buildPlotPresets(metaVariable) {
    const xKey = chooseXKey(metaVariable);
    if (!xKey) return [];

    const presets = PLOT_PRESET_DEFINITIONS
        .map(definition => {
            const groups = resolvePresetGroups(metaVariable, definition);
            if (!groups.length) return null;
            return {
                id: definition.id,
                label: definition.label,
                description: definition.description,
                xKey,
                yKeys: groups.map(group => group.keys),
                chartTypes: groups.map(group => group.type),
            };
        })
        .filter(Boolean);

    const allNumeric = numericKeys(metaVariable).filter(key => key !== xKey);
    if (allNumeric.length) {
        presets.push({
            id: "all-available",
            label: "All available numeric channels",
            description: "A broad view of every numeric metadata channel; use Advanced plot to refine it.",
            xKey,
            yKeys: [allNumeric],
            chartTypes: ["scatter"],
        });
    }

    return presets;
}

function appendOptions(select, keys, selectedKeys = []) {
    if (!select) return;
    select.replaceChildren();
    keys.forEach(key => {
        const option = document.createElement("option");
        option.value = key;
        option.textContent = key;
        option.selected = selectedKeys.includes(key);
        select.appendChild(option);
    });
}

export function populateAxisSelects(metaVariable) {
    const xSel = document.getElementById("xAxisSelect");
    const ySel1 = document.getElementById("yAxisSelect1");
    const ySel2 = document.getElementById("yAxisSelect2");
    const ySel3 = document.getElementById("yAxisSelect3");
    const keys = metadataKeys(metaVariable);
    if (!keys.length) return;

    const xValue = chooseXKey(metaVariable, keys);
    const numeric = numericKeys(metaVariable);
    const firstNumeric = numeric[0] || keys[0];
    const y1Value = ["WBPP weight 1", "WBPP weight 2", "WBPP weight 3"].filter(key => numeric.includes(key));
    const y2Value = ["FWHM", "HFR", "HFD", "AMBTEMP"].find(key => numeric.includes(key)) || firstNumeric;
    const y3Value = ["AMBTEMP", "CCD-TEMP", "HUMIDITY"].find(key => numeric.includes(key)) || firstNumeric;

    appendOptions(xSel, keys, [xValue]);
    appendOptions(ySel1, numeric.length ? numeric : keys, y1Value.length ? y1Value : [firstNumeric]);
    appendOptions(ySel2, numeric.length ? numeric : keys, [y2Value]);
    appendOptions(ySel3, numeric.length ? numeric : keys, [y3Value]);
}

function parseDateValue(value) {
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : null;
}

export function buildDateRangeBreaks(values, minimumGapHours = 4) {
    const timestamps = [...new Set(
        (Array.isArray(values) ? values : [])
            .map(parseDateValue)
            .filter(timestamp => timestamp !== null)
    )].sort((left, right) => left - right);

    const minimumGap = minimumGapHours * 60 * 60 * 1000;
    const breaks = [];
    for (let index = 1; index < timestamps.length; index += 1) {
        const previous = timestamps[index - 1];
        const current = timestamps[index];
        const gap = current - previous;
        if (gap <= minimumGap) continue;

        const padding = Math.min(15 * 60 * 1000, Math.floor(gap / 4));
        breaks.push({
            bounds: [
                new Date(previous + padding).toISOString(),
                new Date(current - padding).toISOString(),
            ],
        });
    }
    return breaks;
}

function isDateAxis(xKey, xValues) {
    return DATE_AXIS_CANDIDATES.includes(xKey) || isDateSeries(xValues);
}

function normalizeXValue(value, dateAxis) {
    if (dateAxis) {
        const timestamp = parseDateValue(value);
        return timestamp === null ? null : new Date(timestamp).toISOString();
    }

    const number = Number(value);
    return Number.isFinite(number) ? number : (value === null || value === undefined ? null : value);
}

function prepareSeries(xValues, yValues, files, dateAxis) {
    const rows = [];
    const length = Math.min(xValues.length, yValues.length);
    for (let index = 0; index < length; index += 1) {
        const x = normalizeXValue(xValues[index], dateAxis);
        const y = Number(yValues[index]);
        if (x === null || !Number.isFinite(y)) continue;
        rows.push({ x, y, file: files?.[index] || "" });
    }

    if (dateAxis) {
        rows.sort((left, right) => Date.parse(left.x) - Date.parse(right.x));
    }

    return {
        x: rows.map(row => row.x),
        y: rows.map(row => row.y),
        files: rows.map(row => row.file),
    };
}

function colorFor(key, index) {
    if (key === "WBPP weight 1") return "#dc2626";
    if (key === "WBPP weight 2") return "#16a34a";
    if (key === "WBPP weight 3") return "#2563eb";
    return PLOT_COLORS[index % PLOT_COLORS.length];
}

export function drawVariablePlot(
    metaVariable,
    metaComments,
    xKey,
    yKeys,
    chartTypes,
    options = {}
) {
    const plot = document.getElementById("framesPlot");
    const xValues = Array.isArray(metaVariable?.[xKey]) ? metaVariable[xKey] : [];
    if (!plot || !xValues.length) return;

    const dateAxis = isDateAxis(xKey, xValues);
    const files = Array.isArray(metaVariable?._files) ? metaVariable._files : [];
    const traces = [];
    let colorIndex = 0;

    (Array.isArray(yKeys) ? yKeys : []).forEach((axisKeys, axisIndex) => {
        if (!Array.isArray(axisKeys)) return;

        const chartType = chartTypes?.[axisIndex] || (axisIndex === 0 ? "line" : "scatter");
        axisKeys.forEach(yKey => {
            const yValues = metaVariable?.[yKey];
            if (!Array.isArray(yValues) || !isNumericSeries(yValues)) return;

            const series = prepareSeries(xValues, yValues, files, dateAxis);
            if (!series.x.length) return;

            const color = colorFor(yKey, colorIndex);
            colorIndex += 1;
            const isBar = chartType === "bar";
            const isLine = chartType === "line";
            const label = metaComments?.[yKey]?.label ?? yKey;
            traces.push({
                x: series.x,
                y: series.y,
                name: label,
                yaxis: `y${axisIndex + 1}`,
                type: isBar ? "bar" : "scatter",
                mode: isBar ? undefined : (isLine ? "lines" : "markers"),
                marker: { color, size: isLine ? undefined : 6 },
                line: isLine ? { color, width: 2 } : undefined,
                customdata: series.files,
                hovertemplate: `%{x}<br>${label}: %{y}<br>%{customdata}<extra></extra>`,
                connectgaps: false,
            });
        });
    });

    if (!traces.length) {
        plot.replaceChildren();
        return;
    }

    const axisTitle = axisKeys => (axisKeys?.length ? axisKeys
        .map(key => metaComments?.[key]?.label ?? key)
        .join(", ") : "");
    const xaxis = {
        title: metaComments?.[xKey]?.label ?? xKey,
        type: dateAxis ? "date" : undefined,
        rangebreaks: dateAxis ? buildDateRangeBreaks(xValues) : undefined,
        tickformat: dateAxis ? "%b %d\n%H:%M" : undefined,
    };

    Plotly.react(
        plot,
        traces,
        {
            title: options.title || xKey,
            paper_bgcolor: "transparent",
            plot_bgcolor: "transparent",
            hovermode: "x unified",
            margin: { t: 55, r: 90, b: 70, l: 65 },
            xaxis,
            yaxis: { title: axisTitle(yKeys?.[0]), gridcolor: "rgba(148,163,184,0.2)" },
            yaxis2: {
                title: axisTitle(yKeys?.[1]),
                overlaying: "y",
                side: "right",
                showgrid: false,
            },
            yaxis3: {
                title: axisTitle(yKeys?.[2]),
                overlaying: "y",
                side: "right",
                anchor: "free",
                position: 1.08,
                showgrid: false,
            },
            legend: { orientation: "h", x: 0.5, y: 1.12, xanchor: "center" },
        },
        { responsive: true, displaylogo: false }
    );
}
