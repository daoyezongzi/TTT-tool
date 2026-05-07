const ttsForm = document.getElementById("ttsForm");
const textInput = document.getElementById("textInput");
const voiceSelect = document.getElementById("voiceSelect");
const rateInput = document.getElementById("rateInput");
const volumeInput = document.getElementById("volumeInput");
const pitchInput = document.getElementById("pitchInput");
const filenameInput = document.getElementById("filenameInput");
const submitBtn = document.getElementById("submitBtn");
const statusText = document.getElementById("statusText");
const resultSection = document.getElementById("resultSection");
const resultText = document.getElementById("resultText");
const audioPlayer = document.getElementById("audioPlayer");
const downloadLink = document.getElementById("downloadLink");
const rateValue = document.getElementById("rateValue");
const volumeValue = document.getElementById("volumeValue");
const pitchValue = document.getElementById("pitchValue");

function withPercent(value) {
    const n = Number(value);
    return `${n >= 0 ? "+" : ""}${n}%`;
}

function withHz(value) {
    const n = Number(value);
    return `${n >= 0 ? "+" : ""}${n}Hz`;
}

function setStatus(message, type = "") {
    statusText.textContent = message;
    statusText.className = `status ${type}`.trim();
}

function syncSliderText() {
    rateValue.textContent = withPercent(rateInput.value);
    volumeValue.textContent = withPercent(volumeInput.value);
    pitchValue.textContent = withHz(pitchInput.value);
}

async function loadVoices() {
    setStatus("正在加载音源列表...");
    try {
        const resp = await fetch("/api/voices");
        if (!resp.ok) {
            throw new Error("音源加载失败");
        }

        const data = await resp.json();
        const voices = data.voices || [];
        voiceSelect.innerHTML = "";

        voices.forEach((voice) => {
            const option = document.createElement("option");
            option.value = voice.short_name;
            option.textContent = `${voice.short_name} | ${voice.locale} | ${voice.gender}`;
            voiceSelect.appendChild(option);
        });

        const preferred = voices.find((v) => v.short_name === "zh-CN-XiaoxiaoNeural");
        if (preferred) {
            voiceSelect.value = preferred.short_name;
        }

        setStatus(`已加载 ${voices.length} 个音源。`, "success");
    } catch (err) {
        voiceSelect.innerHTML = "<option value=''>加载失败</option>";
        setStatus(`加载音源失败：${err.message}`, "error");
    }
}

async function synthesizeAudio(event) {
    event.preventDefault();
    resultSection.classList.add("hidden");

    const text = textInput.value.trim();
    if (!text) {
        setStatus("请输入文本内容。", "error");
        return;
    }
    if (!voiceSelect.value) {
        setStatus("请选择音源。", "error");
        return;
    }

    submitBtn.disabled = true;
    setStatus("正在生成 MP3，请稍候...");

    const payload = {
        text,
        voice: voiceSelect.value,
        rate: Number(rateInput.value),
        volume: Number(volumeInput.value),
        pitch: Number(pitchInput.value),
        filename: filenameInput.value.trim() || null
    };

    try {
        const resp = await fetch("/api/synthesize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await resp.json();
        if (!resp.ok) {
            throw new Error(data.detail || "生成失败");
        }

        const audioUrl = `${data.download_url}?t=${Date.now()}`;
        resultText.textContent = `已生成文件：${data.file_name}`;
        audioPlayer.src = audioUrl;
        downloadLink.href = audioUrl;
        downloadLink.download = data.file_name;
        resultSection.classList.remove("hidden");
        setStatus("生成成功。", "success");
    } catch (err) {
        setStatus(`生成失败：${err.message}`, "error");
    } finally {
        submitBtn.disabled = false;
    }
}

rateInput.addEventListener("input", syncSliderText);
volumeInput.addEventListener("input", syncSliderText);
pitchInput.addEventListener("input", syncSliderText);
ttsForm.addEventListener("submit", synthesizeAudio);

syncSliderText();
loadVoices();
