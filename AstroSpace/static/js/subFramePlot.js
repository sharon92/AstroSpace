export function populateAxisSelects(metaVariable) {
    const xSel  = document.getElementById("xAxisSelect");
    const ySel1 = document.getElementById("yAxisSelect1");
    const ySel2 = document.getElementById("yAxisSelect2");
    const ySel3 = document.getElementById("yAxisSelect3");

    [xSel, ySel1, ySel2, ySel3].forEach(sel => sel.innerHTML = "");

    const keys = Object.keys(metaVariable).filter(k => k !== "_files");
    if (keys.length === 0) return;

    // preferred defaults
    const X_DEFAULT  = "DATE-OBS";
    const Y1_DEFAULT = ["WBPP weight 1", "WBPP weight 2", "WBPP weight 3"];
    const Y2_DEFAULT = "FWHM";
    const Y3_DEFAULT = "AMBTEMP";

    const firstKey = keys[0];

    const xValue  = keys.includes(X_DEFAULT) ? X_DEFAULT : firstKey;
    const y1Value = Y1_DEFAULT.filter(k => keys.includes(k));
    const y2Value = keys.includes(Y2_DEFAULT) ? Y2_DEFAULT : firstKey;
    const y3Value = keys.includes(Y3_DEFAULT) ? Y3_DEFAULT : firstKey;

    // X axis (single)
    keys.forEach(key => {
        const opt = document.createElement("option");
        opt.value = key;
        opt.textContent = key;
        if (key === xValue) opt.selected = true;
        xSel.appendChild(opt);
    });

    // Y axis 1 (multi)
    keys.forEach(key => {
        const opt = document.createElement("option");
        opt.value = key;
        opt.textContent = key;
        if (y1Value.length ? y1Value.includes(key) : key === firstKey) {
            opt.selected = true;
        }
        ySel1.appendChild(opt);
    });

    // Y axis 2 (single)
    keys.forEach(key => {
        const opt = document.createElement("option");
        opt.value = key;
        opt.textContent = key;
        if (key === y2Value) opt.selected = true;
        ySel2.appendChild(opt);
    });

    // Y axis 3 (single)
    keys.forEach(key => {
        const opt = document.createElement("option");
        opt.value = key;
        opt.textContent = key;
        if (key === y3Value) opt.selected = true;
        ySel3.appendChild(opt);
    });
}
export function drawVariablePlot(
    metaVariable,
    metaComments,
    xKey,
    yKeys,        // [ [..], [..], [..] ]
    chartTypes    // ["scatter" | "line" | "bar"] per y-axis
) {
    const x = metaVariable[xKey];
    if (!x) return;

    const COLOR_MAP = {
        "WBPP weight 1": "red",
        "WBPP weight 2": "green",
        "WBPP weight 3": "blue"
    };

    const traces = [];

    yKeys.forEach((axisKeys, axisIdx) => {
        if (!Array.isArray(axisKeys)) return;

        const chartType = chartTypes?.[axisIdx] || (axisIdx === 0 ? "line" : "scatter");
        const isBar  = chartType === "bar";
        const isLine = chartType === "line";

        axisKeys.forEach(yKey => {
            if (!metaVariable[yKey]) return;

            traces.push({
                x,
                y: metaVariable[yKey],
                name: yKey,
                yaxis: `y${axisIdx + 1}`,
                type: isBar ? "bar" : "scatter",
                mode: isBar ? undefined : (isLine ? "lines" : "markers"),
                marker: {
                    color: COLOR_MAP[yKey]
                },
                line: isLine
                    ? { color: COLOR_MAP[yKey] }
                    : undefined
            });
        });
    });

    const axisTitle = (axisKeys) => {
        if (!axisKeys?.length) return "";
        return axisKeys
            .map(k => metaComments?.[k]?.label ?? k)
            .join(", ");
    };

    const layout = {
        title: `${xKey}`,
        xaxis: {
            title: metaComments?.[xKey]?.label ?? xKey
        },

        yaxis: {
            title: axisTitle(yKeys[0])
        },
        yaxis2: {
            title: axisTitle(yKeys[1]),
            overlaying: "y",
            side: "right"
        },
        yaxis3: {
            title: axisTitle(yKeys[2]),
            overlaying: "y",
            side: "right",
            anchor: "free",
            position: 1.08
        },

        hovermode: "closest",
        legend: { orientation: "h" }
    };

    Plotly.newPlot("framesPlot", traces, layout, {
        responsive: true,
        displaylogo: false
    });
}
