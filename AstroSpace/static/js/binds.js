import { updateLocationDetails } from "./utils.js";
import { readFITSHeader, readXISFHeader } from "./fitsUtils.js";


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


function emptyMetaStore() {
    return {
        meta: [],
        filenames: [],
        constant: {},
        variable: {},
        comments: {},
        wbpp_stats: {},
        wbpp_log_name: "",
        light_frame_count: 0,
        light_frame_filenames: [],
    };
}


export let metaStore = emptyMetaStore();


function syncMetaStoreInput() {
    const input = document.getElementById("meta_store_input");
    if (input) input.value = JSON.stringify(metaStore);
}


function renderExtractionStatus() {
    const wbppCount = Object.keys(metaStore.wbpp_stats || {}).length;
    const wbppStatus = document.getElementById("wbppExtractionStatus");
    const clearWbpp = document.getElementById("clearWbppData");
    if (wbppStatus) {
        wbppStatus.hidden = wbppCount === 0;
        wbppStatus.textContent = wbppCount
            ? `WBPP log extracted: ${metaStore.wbpp_log_name || "selected log"} · ${wbppCount} frame entries`
            : "";
    }
    if (clearWbpp) clearWbpp.hidden = wbppCount === 0;

    const lightCount = Number(metaStore.light_frame_count || metaStore.filenames?.length || 0);
    const lightStatus = document.getElementById("lightFrameExtractionStatus");
    const clearLight = document.getElementById("clearLightMetadata");
    if (lightStatus) {
        lightStatus.hidden = lightCount === 0;
        lightStatus.textContent = lightCount
            ? `Light-frame metadata extracted: ${lightCount} light frame(s) successfully extracted`
            : "";
    }
    if (clearLight) clearLight.hidden = lightCount === 0;
}


function renderMetadataTables() {
    const constBody = document.querySelector("#constantsTable tbody");
    if (constBody) {
        constBody.innerHTML = "";
        Object.entries(metaStore.constant || {}).forEach(([key, value]) => {
            const row = document.createElement("tr");
            const keyCell = document.createElement("td");
            keyCell.textContent = key;
            keyCell.className = "border px-2 py-1 font-mono text-gray-700 dark:text-gray-300";
            const valueCell = document.createElement("td");
            valueCell.textContent = value;
            valueCell.className = "border px-2 py-1 text-gray-700 dark:text-gray-300";
            const commentCell = document.createElement("td");
            commentCell.textContent = metaStore.comments?.[key] || "";
            commentCell.className = "border px-2 py-1 text-gray-700 dark:text-gray-300";
            row.append(keyCell, valueCell, commentCell);
            constBody.appendChild(row);
        });
    }

    const table = document.getElementById("variablesTable");
    if (!table) return;
    const head = table.querySelector("thead");
    const body = table.querySelector("tbody");
    head.innerHTML = "";
    body.innerHTML = "";

    const files = Array.isArray(metaStore.variable?._files) ? metaStore.variable._files : [];
    const keywords = Object.keys(metaStore.variable || {}).filter((key) => key !== "_files");
    if (!files.length && !keywords.length) return;

    const headerRow = document.createElement("tr");
    const fileHeader = document.createElement("th");
    fileHeader.textContent = "File";
    fileHeader.className = "border px-2 py-1 text-left text-black";
    headerRow.appendChild(fileHeader);
    keywords.forEach((key) => {
        const header = document.createElement("th");
        header.className = "border px-2 py-1 text-left";
        const label = document.createElement("div");
        label.textContent = key;
        label.className = "font-mono text-black";
        const comment = document.createElement("div");
        comment.textContent = metaStore.comments?.[key] || "";
        comment.className = "text-xs text-gray-500";
        header.append(label, comment);
        headerRow.appendChild(header);
    });
    head.appendChild(headerRow);

    files.forEach((file, rowIndex) => {
        const row = document.createElement("tr");
        const fileCell = document.createElement("td");
        fileCell.textContent = file;
        fileCell.className = "border px-2 py-1 font-mono";
        row.appendChild(fileCell);
        keywords.forEach((key) => {
            const cell = document.createElement("td");
            cell.textContent = metaStore.variable[key]?.[rowIndex] ?? "";
            cell.className = "border px-2 py-1";
            row.appendChild(cell);
        });
        body.appendChild(row);
    });
}


function renderMetadata() {
    renderMetadataTables();
    renderExtractionStatus();
    syncMetaStoreInput();
}


export function restoreMetadata(savedMetadata) {
    if (!savedMetadata || typeof savedMetadata !== "object") return;
    metaStore = {
        ...emptyMetaStore(),
        meta: Array.isArray(savedMetadata.meta) ? savedMetadata.meta : [],
        filenames: Array.isArray(savedMetadata.filenames) ? savedMetadata.filenames : [],
        constant: savedMetadata.constant || {},
        variable: savedMetadata.variable || {},
        comments: savedMetadata.comments || {},
        wbpp_stats: savedMetadata.wbpp_stats || {},
        wbpp_log_name: savedMetadata.wbpp_log_name || "",
        light_frame_count: Number(savedMetadata.light_frame_count || savedMetadata.filenames?.length || 0),
        light_frame_filenames: Array.isArray(savedMetadata.light_frame_filenames)
            ? savedMetadata.light_frame_filenames
            : (Array.isArray(savedMetadata.filenames) ? savedMetadata.filenames : []),
    };
    renderMetadata();
}


function csrfHeaders() {
    const token = document.querySelector('meta[name="csrf-token"]')?.content;
    return token ? { "X-CSRFToken": token } : {};
}


export function bindLightFramesAnalyse() {
    const wbppInput = document.getElementById("wbppLogInput");
    const clearWbppFile = document.getElementById("clearWbppFile");
    const inputRows = document.getElementById("lightFramesInputs");
    const analyseBtn = document.getElementById("analyseLightsBtn");
    if (!inputRows || !analyseBtn) return async () => {};

    const filesByInput = new Map();
    let pickerIndex = 1;
    // Keep each multipart request comfortably below the application upload limit.
    // The browser sends compact FITS/XISF headers, never the image payloads.
    const HEADER_BATCH_SIZE = 10;

    const selectedLightFiles = () => {
        const files = [];
        const seen = new Set();
        filesByInput.forEach((inputFiles) => {
            inputFiles.forEach((file) => {
                const key = `${file.name}:${file.size}:${file.lastModified}`;
                if (!seen.has(key)) {
                    seen.add(key);
                    files.push(file);
                }
            });
        });
        return files;
    };

    const renderSelectionStatus = () => {
        const files = selectedLightFiles();
        const status = document.getElementById("lightFrameSelectionStatus");
        if (status) {
            status.hidden = files.length === 0;
            status.textContent = files.length
                ? `${files.length} light file(s) queued from the selected pickers`
                : "";
        }

        inputRows.querySelectorAll(".light-frame-input-row").forEach((row) => {
            const input = row.querySelector(".light-frame-input");
            const clearButton = row.querySelector(".clear-light-frame-selection");
            const hasFiles = (filesByInput.get(input) || []).length > 0;
            if (clearButton) clearButton.disabled = !hasFiles;
        });

        if (clearWbppFile) {
            clearWbppFile.disabled = !(wbppInput?.files?.length);
        }
    };

    const bindLightInputRow = (row) => {
        const input = row.querySelector(".light-frame-input");
        const clearButton = row.querySelector(".clear-light-frame-selection");
        if (!input) return;

        input.addEventListener("change", () => {
            filesByInput.set(input, Array.from(input.files || []));
            renderSelectionStatus();
        });

        clearButton?.addEventListener("click", () => {
            filesByInput.delete(input);
            input.value = "";
            renderSelectionStatus();
        });
    };

    inputRows.querySelectorAll(".light-frame-input-row").forEach(bindLightInputRow);

    document.getElementById("addLightFramesInput")?.addEventListener("click", () => {
        const row = document.createElement("div");
        row.className = "light-frame-input-row flex space-x-2 items-center";
        row.innerHTML = `
            <input
                type="file"
                id="lightFramesInput-${pickerIndex++}"
                multiple
                accept=".fits,.fit,.xisf"
                class="light-frame-input editor-source-file-input flex-1 text-sm
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-full file:border-0
                    file:text-sm file:font-semibold
                    file:bg-blue-50 file:text-blue-700
                    hover:file:bg-blue-100"
            />
            <button type="button" class="clear-light-frame-selection editor-source-clear-button" disabled>
                Clear selected files
            </button>
        `;
        inputRows.appendChild(row);
        bindLightInputRow(row);
        renderSelectionStatus();
    });

    wbppInput?.addEventListener("change", renderSelectionStatus);
    clearWbppFile?.addEventListener("click", () => {
        if (wbppInput) wbppInput.value = "";
        renderSelectionStatus();
    });

    const extractWbpp = async () => {
        const file = wbppInput?.files?.[0];
        if (!file || !file.name.toLowerCase().endsWith(".log")) return;

        const formData = new FormData();
        formData.append("wbpp_log_file", file, file.name);
        const response = await fetch("/extract_stats", {
            method: "POST",
            headers: csrfHeaders(),
            body: formData,
        });
        const data = await response.json();
        if (!response.ok || data.error) {
            throw new Error(data.error || "Unable to extract the WBPP log");
        }

        metaStore.wbpp_stats = data;
        metaStore.wbpp_log_name = file.name;
        wbppInput.value = "";
        renderMetadata();
    };

    const extractLights = async () => {
        const files = selectedLightFiles();
        if (!files.length) return;

        const errors = [];
        let processedCount = 0;
        let lastData = null;
        const accumulated = {
            meta: Array.isArray(metaStore.meta) ? [...metaStore.meta] : [],
            filenames: Array.isArray(metaStore.filenames) ? [...metaStore.filenames] : [],
        };

        for (let batchStart = 0; batchStart < files.length; batchStart += HEADER_BATCH_SIZE) {
            const batchEnd = Math.min(batchStart + HEADER_BATCH_SIZE, files.length);
            const formData = new FormData();
            let batchCount = 0;

            for (const file of files.slice(batchStart, batchEnd)) {
                const name = file.name.toLowerCase();
                if (!(name.endsWith(".fits") || name.endsWith(".fit") || name.endsWith(".xisf"))) continue;
                try {
                    const headerBytes = name.endsWith(".xisf")
                        ? await readXISFHeader(file)
                        : await readFITSHeader(file);
                    formData.append(
                        "header_files",
                        new Blob([headerBytes], { type: "application/octet-stream" }),
                        file.name + ".header"
                    );
                    batchCount += 1;
                } catch (error) {
                    errors.push(`${file.name}: ${error.message}`);
                }
            }

            if (!batchCount) continue;

            if (accumulated.meta.length) {
                formData.append(
                    "meta_store",
                    new Blob([JSON.stringify(accumulated)], { type: "application/json" })
                );
            }

            const status = document.getElementById("lightFrameExtractionStatus");
            if (status) {
                status.hidden = false;
                status.textContent = `Extracting FITS headers: ${batchEnd}/${files.length}`;
            }

            const response = await fetch("/extract_meta", {
                method: "POST",
                headers: csrfHeaders(),
                body: formData,
            });
            const data = await response.json();
            if (!response.ok || data.error) {
                if (response.status === 413) {
                    throw new Error("A header batch was still too large. Please reduce the selected batch and try again.");
                }
                throw new Error(data.error || "Unable to extract light-frame metadata");
            }

            accumulated.meta = Array.isArray(data.meta) ? data.meta : accumulated.meta;
            accumulated.filenames = Array.isArray(data.filenames) ? data.filenames : accumulated.filenames;
            lastData = data;
            processedCount += batchCount;
        }

        if (!processedCount || !lastData) {
            throw new Error(errors.join("; ") || "No FITS light frames were selected");
        }

        metaStore.meta = accumulated.meta;
        metaStore.filenames = accumulated.filenames;
        metaStore.constant = lastData.constant || {};
        metaStore.variable = lastData.variable || {};
        metaStore.comments = lastData.comments || {};
        metaStore.light_frame_count = metaStore.filenames.length;
        metaStore.light_frame_filenames = [...metaStore.filenames];
        filesByInput.clear();
        inputRows.querySelectorAll(".light-frame-input").forEach((input) => {
            input.value = "";
        });
        renderMetadata();
        renderSelectionStatus();

        if (errors.length) {
            const status = document.getElementById("lightFrameExtractionStatus");
            if (status) {
                status.hidden = false;
                status.textContent += ` · ${errors.length} file(s) skipped`;
            }
        }
    };

    const extractSelectedData = async () => {
        await extractWbpp();
        await extractLights();
        renderMetadata();
    };

    analyseBtn.addEventListener("click", async () => {
        if (analyseBtn.disabled) return;
        const idleLabel = analyseBtn.dataset.idleLabel || analyseBtn.textContent.trim();
        analyseBtn.dataset.idleLabel = idleLabel;
        analyseBtn.disabled = true;
        analyseBtn.classList.add("is-extracting");
        analyseBtn.setAttribute("aria-busy", "true");
        analyseBtn.textContent = "Extracting FITS metadata…";
        try {
            await extractLights();
        } catch (error) {
            const status = document.getElementById("lightFrameExtractionStatus");
            if (status) {
                status.hidden = false;
                status.textContent = error.message;
            }
            console.error("FITS metadata extraction error:", error);
        } finally {
            analyseBtn.classList.remove("is-extracting");
            analyseBtn.removeAttribute("aria-busy");
            analyseBtn.disabled = false;
            analyseBtn.textContent = idleLabel;
        }
    });

    document.getElementById("clearWbppData")?.addEventListener("click", () => {
        metaStore.wbpp_stats = {};
        metaStore.wbpp_log_name = "";
        if (wbppInput) wbppInput.value = "";
        renderMetadata();
        renderSelectionStatus();
    });

    document.getElementById("clearLightMetadata")?.addEventListener("click", () => {
        metaStore.meta = [];
        metaStore.filenames = [];
        metaStore.constant = {};
        metaStore.variable = {};
        metaStore.comments = {};
        metaStore.light_frame_count = 0;
        metaStore.light_frame_filenames = [];
        filesByInput.clear();
        inputRows.querySelectorAll(".light-frame-input").forEach((input) => {
            input.value = "";
        });
        renderMetadata();
        renderSelectionStatus();
    });

    renderSelectionStatus();
    return extractSelectedData;
}
