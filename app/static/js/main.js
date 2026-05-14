const uploadBtn = document.getElementById("upload-btn");
const applyLineBtn = document.getElementById("apply-line-btn");
const startBtn = document.getElementById("start-btn");
const stopBtn = document.getElementById("stop-btn");

const videoFileInput = document.getElementById("video-file");
const videoImg = document.getElementById("video-stream");
const videoPlaceholder = document.getElementById("video-placeholder");

const uploadStatus = document.getElementById("upload-status");
const lineStatus = document.getElementById("line-status");
const resultBody = document.getElementById("result-body");
const fileDropText = document.querySelector(".file-drop strong");
const fileDropHint = document.querySelector(".file-drop small");

const metricRecords = document.getElementById("metric-records");
const metricAvg = document.getElementById("metric-avg");
const metricMax = document.getElementById("metric-max");

let resultTimer = null;

uploadBtn.addEventListener("click", uploadVideo);
applyLineBtn.addEventListener("click", applyLineConfig);
startBtn.addEventListener("click", startDetect);
stopBtn.addEventListener("click", stopDetect);

videoFileInput.addEventListener("change", function () {
    const file = videoFileInput.files[0];
    if (!file) {
        fileDropText.textContent = "点击选择检测视频";
        fileDropHint.textContent = "支持 MP4、AVI、MOV 等常见格式";
        setStatus(uploadStatus, "", "");
        return;
    }

    fileDropText.textContent = file.name;
    fileDropHint.textContent = `${formatFileSize(file.size)} · 点击可重新选择`;
    setStatus(uploadStatus, "视频已选择，点击上传后即可进行检测。", "success");
});

if (videoImg) {
    videoImg.addEventListener("load", () => togglePlaceholder(true));
    videoImg.addEventListener("error", () => togglePlaceholder(false));
}

function togglePlaceholder(hasVideo) {
    if (!videoPlaceholder) return;
    videoPlaceholder.classList.toggle("is-hidden", !!hasVideo);
}

function formatFileSize(bytes) {
    if (!bytes) return "0 B";

    const units = ["B", "KB", "MB", "GB"];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    return `${(bytes / Math.pow(1024, index)).toFixed(index === 0 ? 0 : 2)} ${units[index]}`;
}

function setStatus(element, message, type = "") {
    element.textContent = message;
    element.classList.remove("success", "error");
    if (type) element.classList.add(type);
}

function setButtonLoading(button, isLoading, loadingText) {
    if (!button.dataset.defaultText) {
        button.dataset.defaultText = button.innerHTML;
    }
    button.disabled = isLoading;
    button.innerHTML = isLoading ? loadingText : button.dataset.defaultText;
}

async function uploadVideo() {
    const file = videoFileInput.files[0];

    if (!file) {
        setStatus(uploadStatus, "请先选择视频文件。", "error");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setStatus(uploadStatus, "正在上传视频，请稍候...");
    setButtonLoading(uploadBtn, true, "上传中...");

    try {
        const response = await fetch("/api/video/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        setStatus(uploadStatus, data.message || "上传完成。", data.code === 200 ? "success" : "error");
    } catch (error) {
        setStatus(uploadStatus, "上传失败：" + error.message, "error");
    } finally {
        setButtonLoading(uploadBtn, false);
    }
}

async function applyLineConfig() {
    const payload = window.getSpeedLinePayload();

    setStatus(lineStatus, "正在应用测速线配置...");
    setButtonLoading(applyLineBtn, true, "配置中...");

    try {
        const response = await fetch("/api/line/config", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        const ok = data.code === 200;
        setStatus(lineStatus, data.message || (ok ? "配置成功。" : "配置失败。"), ok ? "success" : "error");
        return ok;
    } catch (error) {
        setStatus(lineStatus, "配置失败：" + error.message, "error");
        return false;
    } finally {
        setButtonLoading(applyLineBtn, false);
    }
}

async function startDetect() {
    const ok = await applyLineConfig();
    if (!ok) return;

    togglePlaceholder(true);
    window.startVideoStream();
    startBtn.classList.add("is-active");

    if (resultTimer) clearInterval(resultTimer);

    loadResults();
    resultTimer = setInterval(loadResults, 1000);
}

function stopDetect() {
    window.stopVideoStream();
    startBtn.classList.remove("is-active");
    togglePlaceholder(false);

    if (resultTimer) {
        clearInterval(resultTimer);
        resultTimer = null;
    }
}

function updateMetrics(results) {
    if (!metricRecords || !metricAvg || !metricMax) return;

    if (!results.length) {
        metricRecords.textContent = "0";
        metricAvg.textContent = "0.0";
        metricMax.textContent = "0.0";
        return;
    }

    const speeds = results
        .map(item => Number(item.speed_kmh))
        .filter(value => !Number.isNaN(value));

    const average = speeds.length
        ? (speeds.reduce((sum, value) => sum + value, 0) / speeds.length).toFixed(1)
        : "0.0";

    const max = speeds.length ? Math.max(...speeds).toFixed(1) : "0.0";

    metricRecords.textContent = String(results.length);
    metricAvg.textContent = average;
    metricMax.textContent = max;
}

async function loadResults() {
    try {
        const response = await fetch("/api/results");
        const data = await response.json();
        const results = data.data || [];

        updateMetrics(results);

        if (results.length === 0) {
            resultBody.innerHTML = `
                <tr>
                    <td colspan="4" class="empty-cell">暂无数据</td>
                </tr>
            `;
            return;
        }

        resultBody.innerHTML = "";

        results.forEach(item => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>#${item.track_id}</strong></td>
                <td>${item.frame_diff}</td>
                <td>${item.time_seconds}</td>
                <td><strong>${item.speed_kmh}</strong></td>
            `;
            resultBody.appendChild(tr);
        });
    } catch (error) {
        console.error(error);
    }
}
