const titleEl = document.getElementById("lessonTitle");
const descEl = document.getElementById("lessonDescription");
const imageEl = document.getElementById("lessonImage");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");

let lessons = [];
let index = 0;

function render() {
  if (!lessons.length) {
    titleEl.textContent = "Нет материалов";
    descEl.textContent = "Добавьте здания через страницу /admin.";
    imageEl.src = "";
    return;
  }

  const item = lessons[index];
  titleEl.textContent = item.name;
  descEl.textContent = item.description;
  imageEl.src = item.image;
}

async function loadLessons() {
  const res = await fetch("/api/lessons");
  const data = await res.json();
  lessons = data.items || [];
  render();
}

prevBtn.addEventListener("click", () => {
  if (!lessons.length) return;
  index = (index - 1 + lessons.length) % lessons.length;
  render();
});

nextBtn.addEventListener("click", () => {
  if (!lessons.length) return;
  index = (index + 1) % lessons.length;
  render();
});

loadLessons();
