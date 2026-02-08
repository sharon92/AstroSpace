// plotHR.js
export function drawHRDiagram(overlayData) {
    //const db1 = overlayData.overlays;
    const db2 = overlayData.plots;
    const db = db2["hr"];

    const trace = {
        x: db.x,
        y: db.y,
        text: db.name.map(
            (n, i) =>
                `${n}<br>B–V: ${db.x[i]}<br>Mv: ${db.y[i]}<br>${db["Spectral Class"][i] || ""}`
        ),
        mode: "markers",
        type: "scatter",
        marker: {
            size: 5,
            color: db.color,
            line: {
                color: 'rgba(0, 0, 0, 1)',
                width: 1
            }
        },
        hovertemplate: "%{text}<extra></extra>"
    };

    const layout = {
        title: {
            text: "Hertzsprung–Russell Diagram",
            x: 0.5,
            font: { size: 20 },
        },
        xaxis: {
            title: { text: "Color Index (B–V)  →  Spectral Class" },
            range: [Math.min(...db.x), Math.max(...db.x)],
            showgrid: false,
            zeroline: false,
            showline: true,
            linecolor: 'black',
            linewidth: 3,
            mirror: true,
        },
        yaxis: {
            title: { text: "Absolute Magnitude (Mv)" },
            range: [20, -15],
            showgrid: false,
            zeroline: false,
            showline: true,
            linecolor: 'black',
            linewidth: 3,
            mirror: true,
        },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        hovermode: "closest",
        margin: { l: 60, r: 40, b: 60, t: 80 },
        annotations: [
            { x: 0.6, y: 6.5, text: 'main sequence', font: { size: 12, color: 'black' }, showarrow: true, arrowcolor: 'yellow', ax: 40, ay: 60 },
            { x: 1.8, y: -1, text: 'giants', font: { size: 15, color: 'black' }, showarrow: true, arrowcolor: 'orange', ax: 30, ay: -50 },
            { x: 0.5, y: -14, text: 'supergiants', font: { size: 20, color: 'black' }, showarrow: false },
            { x: 0, y: 16, text: 'white dwarfs', font: { size: 8, color: 'black' }, showarrow: false }
        ]
    };

    Plotly.newPlot(
        "dist-scatter",
        [trace],
        layout,
        { displaylogo: false, responsive: true, modeBarButtonsToRemove: ['zoom2d', 'toImage', 'pan2d', 'lasso2d', 'zoomin2d', 'zoomOut2d', 'autoscale2d', 'select2d'] }
    );
}
