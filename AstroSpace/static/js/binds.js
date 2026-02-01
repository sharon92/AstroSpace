import { updateLocationDetails } from "./utils.js";
import { readFITSHeader } from "./fitsUtils.js";


export function bindLocationInput() {
    const locInput = document.getElementById("locationInput");
    if (!locInput) return;

    const elements = {
        lat: document.getElementById("location_lat"),
        lng: document.getElementById("location_lng"),
        elev: document.getElementById("location_elev"),
    };

    locInput.addEventListener("change", () => {
        const q = locInput.value.trim();
        if (q) updateLocationDetails(q, elements);
    });

    if (locInput.value.trim()) {
        updateLocationDetails(locInput.value.trim(), elements);
    }
}

export let metaStore = {
    meta: [],
    filenames: [],
    wbpp_stats: {}
};

export function bindLightFramesAnalyse() {
    const wbppInput = document.getElementById("wbppLogInput");
    const input = document.getElementById("lightFramesInput");
    const analyseBtn = document.getElementById("analyseLightsBtn");

    if (!input || !analyseBtn) return;

    analyseBtn.addEventListener("click", async () => {
        if (wbppInput) {
            const file = wbppInput.files[0]; // only the first file
            if (file && file.name.toLowerCase().endsWith(".log")) {
                const formData = new FormData();
                formData.append("wbpp_log_file", file, file.name);

                try {
                    const res = await fetch("/extract_stats", {
                        method: "POST",
                        body: formData
                    });

                    const data = await res.json();

                    if (data.error) {
                        console.error("WBPP log error:", data.error);
                    }

                    // Merge or replace WBPP stats in metaStore
                    metaStore.wbpp_stats = data;

                    // Refresh table
                    // populateWBPPTable(metaStore.wbpp_stats);

                } catch (err) {
                    console.error("WBPP log fetch error:", err);
                }
            }
        }
        
        //fits
        const files = Array.from(input.files);
        if (files.length === 0) return;

        // Send header to Flask
        const formData = new FormData();
        for (const file of files) {
            const name = file.name.toLowerCase();

            if (!(name.endsWith(".fits") || name.endsWith(".fit"))) {
                continue;
            }

            try {
                const headerBytes = await readFITSHeader(file);

                formData.append(
                    "header_files",
                    new Blob([headerBytes], { type: "application/octet-stream" }),
                    file.name + ".header"
                );

            } catch (err) {
                const li = document.createElement("li");
                li.textContent = `${file.name}: Error reading header (${err.message})`;
                outputList.appendChild(li);
            }
        }

        // Nothing valid selected
        if (!formData.has("header_files")) {
            return;
        }

        if (metaStore.meta.length > 0 || Object.keys(metaStore.wbpp_stats).length > 0) {
            formData.append(
            "meta_store",
            new Blob(
                [JSON.stringify(metaStore)],
                { type: "application/json" }
             )
           );
        }

        const res = await fetch("/extract_meta", {
            method: "POST",
            body: formData
        });

        const data = await res.json();
        metaStore.meta = data.meta;
        metaStore.filenames = data.filenames;
        metaStore.constant = data.constant;
        metaStore.variable = data.variable;
        metaStore.comments = data.comments;

        // Constants table
        const constTbody = document.querySelector("#constantsTable tbody");
        constTbody.innerHTML = "";
        if (data.constant) {
            Object.entries(data.constant).forEach(([key, value]) => {
                const tr = document.createElement("tr");

                const tdKey = document.createElement("td");
                tdKey.textContent = key;
                tdKey.className = "border px-2 py-1 font-mono text-gray-700 dark:text-gray-300";

                const tdVal = document.createElement("td");
                tdVal.textContent = value;
                tdVal.className = "border px-2 py-1 text-gray-700 dark:text-gray-300";

                const tdComment = document.createElement("td");
                tdComment.textContent = data.comments[key] || "";
                tdComment.className = "border px-2 py-1 text-gray-700 dark:text-gray-300";

                tr.append(tdKey, tdVal, tdComment);
                constTbody.appendChild(tr);
            });
        }

        // Variables table
        const varTable = document.getElementById("variablesTable");
        const thead = varTable.querySelector("thead");
        const tbody = varTable.querySelector("tbody");

        thead.innerHTML = "";
        tbody.innerHTML = "";

        const d_files = data.variable._files;

        // all variable keywords (excluding _files)
        const keywords = Object.keys(data.variable).filter(k => k !== "_files");

        /* ---------- HEADER ---------- */
        const headerRow = document.createElement("tr");

        // first column: File
        const thFile = document.createElement("th");
        thFile.textContent = "File";
        thFile.className = "border px-2 py-1 text-left text-black";
        headerRow.appendChild(thFile);

        // keyword columns
        keywords.forEach(key => {
            const th = document.createElement("th");
            th.innerHTML = `
                <div class="font-mono text-black">${key}</div>
                <div class="text-xs text-gray-500">${data.comments[key] || ""}</div>
            `;
            th.className = "border px-2 py-1 text-left";
            headerRow.appendChild(th);
        });

        thead.appendChild(headerRow);

        /* ---------- BODY ---------- */
        d_files.forEach((file, rowIdx) => {
            const tr = document.createElement("tr");

            const tdFile = document.createElement("td");
            tdFile.textContent = file;
            tdFile.className = "border px-2 py-1 font-mono";
            tr.appendChild(tdFile);

            keywords.forEach(key => {
                const td = document.createElement("td");
                const val = data.variable[key][rowIdx];
                td.textContent = val ?? "";
                td.className = "border px-2 py-1";
                tr.appendChild(td);
            });

            tbody.appendChild(tr);
        });
    });
}
