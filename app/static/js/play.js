const scoreEl = document.getElementById("score");
const promptEl = document.getElementById("questionPrompt");
const optionsEl = document.getElementById("options");
const mainImageWrap = document.getElementById("mainImageWrap");
const mainImage = document.getElementById("mainImage");

const loseModal = document.getElementById("loseModal");
const correctName = document.getElementById("correctName");
const buildingDescription = document.getElementById("buildingDescription");
const restartBtn = document.getElementById("restartBtn");

let currentQuestion = null;
let score = 0;
let isChecking = false;

function setScore(value) {
  score = value;
  scoreEl.textContent = String(score);
}

function setOptionsDisabled(disabled) {
  [...optionsEl.querySelectorAll("button")].forEach((btn) => {
    btn.disabled = disabled;
  });
}

async function loadQuestion() {
  isChecking = false;
  optionsEl.innerHTML = "";
  mainImageWrap.classList.add("hidden");

  const res = await fetch("/api/quiz/next");
  const data = await res.json();

  if (!res.ok) {
    promptEl.textContent = data.detail || "Ошибка загрузки вопроса";
    return;
  }

  currentQuestion = data;
  promptEl.textContent = data.prompt;

  if (data.mode === "image_to_names") {
    mainImageWrap.classList.remove("hidden");
    mainImage.src = data.image;
  }

  data.options.forEach((option) => {
    const btn = document.createElement("button");
    btn.className = data.mode === "question_to_images" ? "option-card image-option" : "option-card text-option";

    if (data.mode === "question_to_images") {
      btn.innerHTML = `
        <img src="${option.image}" alt="Вариант ответа">
      `;
    } else {
      btn.textContent = option.label;
    }

    btn.addEventListener("click", () => submitAnswer(option.id));
    optionsEl.appendChild(btn);
  });
}

async function submitAnswer(selectedId) {
  if (!currentQuestion || isChecking) return;
  isChecking = true;
  setOptionsDisabled(true);

  const res = await fetch("/api/quiz/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: currentQuestion.question_id, selected_id: selectedId }),
  });

  const data = await res.json();

  if (!res.ok) {
    isChecking = false;
    setOptionsDisabled(false);
    promptEl.textContent = data.detail || "Ошибка проверки";
    return;
  }

  if (data.correct) {
    setScore(score + 1);
    setTimeout(loadQuestion, 700);
  } else {
    correctName.textContent = `Правильный ответ: ${data.correct_name}`;
    buildingDescription.textContent = data.description;
    loseModal.classList.remove("hidden");
  }
}

restartBtn.addEventListener("click", () => {
  loseModal.classList.add("hidden");
  setScore(0);
  loadQuestion();
});

loadQuestion();
