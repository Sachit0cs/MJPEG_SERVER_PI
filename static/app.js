const blurSlider = document.getElementById("blur");
const blurValue = document.getElementById("blurValue");
const startBtn = document.getElementById("start");
const stopBtn = document.getElementById("stop");
const fpsBadge = document.getElementById("fps");

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

blurSlider.addEventListener("input", async (e) => {
  const value = parseInt(e.target.value, 10);
  blurValue.textContent = value;
  await postJson("/blur", { strength: value });
});

startBtn.addEventListener("click", async () => {
  await postJson("/control", { action: "start" });
});

stopBtn.addEventListener("click", async () => {
  await postJson("/control", { action: "stop" });
});

async function pollStatus() {
  try {
    const res = await fetch("/status");
    const data = await res.json();
    fpsBadge.textContent = `FPS: ${data.fps}`;
    blurSlider.value = data.blur_strength;
    blurValue.textContent = data.blur_strength;
  } catch (err) {
    fpsBadge.textContent = "FPS: --";
  }
}

setInterval(pollStatus, 1000);
