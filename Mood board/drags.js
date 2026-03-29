const canvas = document.getElementById('myCanvas');
const ctx = canvas.getContext('2d');

const center = { x: canvas.width / 2, y: canvas.height / 2 };

// Load all sprites
const images = { none: new Image() };
images.none.src = 'sprites/none.png';

['A', 'H', 'D', 'S'].forEach(prefix => {
  for (let i = 1; i <= 6; i++) {
    const key = `${prefix}${i}`;
    images[key] = new Image();
    images[key].src = `sprites/${key}.png`;
  }
});

let pos = { x: center.x, y: center.y };
let dragging = false;
let offset = { x: 0, y: 0 };
let currentImage = images.none;

// Detect square quadrant and level (1–6)
function getDirectionAndLevel(p) {
  const dx = p.x - center.x;
  const dy = p.y - center.y;

  if (Math.abs(dx) < 10 && Math.abs(dy) < 10) return 'none'; // near center

  let dir = 'none';
  if (dx < 0 && dy < 0) dir = 'A';       // Top Left
  else if (dx > 0 && dy < 0) dir = 'H';  // Top Right
  else if (dx > 0 && dy > 0) dir = 'D';  // Bottom Right
  else if (dx < 0 && dy > 0) dir = 'S';  // Bottom Left

  const maxX = dir === 'A' || dir === 'S' ? center.x : canvas.width - center.x;
  const maxY = dir === 'A' || dir === 'H' ? center.y : canvas.height - center.y;
  const maxDist = Math.hypot(maxX, maxY);

  const dist = Math.hypot(dx, dy);
  const level = Math.min(6, Math.ceil((dist / maxDist) * 6));

  return dir + level;
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const imageKey = getDirectionAndLevel(pos);
  currentImage = images[imageKey];
  ctx.drawImage(currentImage, pos.x - 50, pos.y - 50, 100, 100);
}

function animateReturn() {
  if (dragging) return;

  const dx = center.x - pos.x;
  const dy = center.y - pos.y;
  const dist = Math.hypot(dx, dy);

  if (dist < 1) {
    pos.x = center.x;
    pos.y = center.y;
    draw();
    return;
  }

  const speed = Math.max(2, dist * 0.1);
  const newX = pos.x + (dx / dist) * speed;
  const newY = pos.y + (dy / dist) * speed;

  pos.x = Math.min(canvas.width - 50, Math.max(50, newX));
  pos.y = Math.min(canvas.height - 50, Math.max(50, newY));

  draw();
  requestAnimationFrame(animateReturn);
}
offseti = 30;
canvas.addEventListener('mousedown', (e) => {
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  if (
    mouseX > pos.x - offseti && mouseX < pos.x + offseti &&
    mouseY > pos.y - offseti && mouseY < pos.y + offseti
  ) {
    dragging = true;
    offset.x = mouseX - pos.x;
    offset.y = mouseY - pos.y;
  }
});

canvas.addEventListener('mousemove', (e) => {
  if (dragging) {
    const rect = canvas.getBoundingClientRect();
    const rawX = e.clientX - rect.left - offset.x;
    const rawY = e.clientY - rect.top - offset.y;

    pos.x = Math.min(canvas.width - offseti, Math.max(offseti, rawX));
    pos.y = Math.min(canvas.height - offseti, Math.max(offseti, rawY));

    draw();
  }
});

canvas.addEventListener('mouseup', () => {
  dragging = false;
  animateReturn();
});

// Wait for all sprites to load
Promise.all(
  Object.values(images).map(
    img => new Promise(resolve => img.onload = resolve)
  )
).then(draw);
