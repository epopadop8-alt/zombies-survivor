const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");

// ================= GAME STATE =================
let keys = {};
let bullets = [];
let zombies = [];
let turrets = [];
let grenades = [];

let gameOver = false;
let waveClear = false;
let shopOpen = false;

let wave = 1;
let kills = 0;
let killGoal = 5;
let money = 0;
let zombiesSpawned = 0;

let nukes = 0;

// ================= PLAYER =================
let player = {
  x: 400,
  y: 300,
  width: 30,
  height: 42,
  speed: 5,
  health: 3,
  maxHealth: 3,
  damage: 1,
  lastHit: 0
};

// ================= SHOP =================
let shopButtons = [
  { text: "Damage +1 ($50)", cost: 50, action: () => player.damage++ },
  { text: "Max Health +1 ($75)", cost: 75, action: () => { player.maxHealth++; player.health++; }},
  { text: "Buy Grenade ($40)", cost: 40, action: () => grenades.push({}) },
  { text: "Buy Nuke ($300)", cost: 300, action: () => nukes++ }
];

// ================= INPUT =================
document.addEventListener("keydown", (e) => {
  keys[e.key.toLowerCase()] = true;

  if (gameOver && e.key === " ") restartGame();

  // Grenade
  if (e.key === "g" && grenades.length > 0 && !shopOpen) {
    grenades.pop();
    zombies = [];
  }

  // Nuke
  if (e.key === "n" && nukes > 0 && !shopOpen) {
    nukes--;
    zombies = [];
  }

  // Start next wave from shop
  if (shopOpen && e.key === "Enter") {
    shopOpen = false;
    waveClear = false;
    nextWave();
  }
});

document.addEventListener("keyup", (e) => {
  keys[e.key.toLowerCase()] = false;
});

// Shop clicking
canvas.addEventListener("click", (e) => {
  if (!shopOpen) return;

  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;

  shopButtons.forEach((btn, i) => {
    let bx = 250;
    let by = 200 + i * 60;
    let bw = 300;
    let bh = 45;

    if (mx > bx && mx < bx + bw && my > by && my < by + bh) {
      if (money >= btn.cost) {
        money -= btn.cost;
        btn.action();
      }
    }
  });
});

// Shooting
canvas.addEventListener("click", (e) => {
  if (gameOver || waveClear || shopOpen) return;

  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  let angle = Math.atan2(
    mouseY - (player.y + player.height / 2),
    mouseX - (player.x + player.width / 2)
  );

  bullets.push({
    x: player.x + player.width / 2,
    y: player.y + player.height / 2,
    dx: Math.cos(angle) * 10,
    dy: Math.sin(angle) * 10,
    radius: 5
  });
});

// ================= SPAWN =================
function spawnZombie() {
  if (gameOver || waveClear || shopOpen) return;
  if (zombiesSpawned >= killGoal) return;

  let side = Math.floor(Math.random() * 4);
  let x, y;

  if (side === 0) { x = Math.random() * canvas.width; y = -50; }
  if (side === 1) { x = Math.random() * canvas.width; y = canvas.height + 50; }
  if (side === 2) { x = -50; y = Math.random() * canvas.height; }
  if (side === 3) { x = canvas.width + 50; y = Math.random() * canvas.height; }

  zombies.push({
    x,
    y,
    width: 40,
    height: 50,
    speed: 1.2 + wave * 0.2,
    health: 2 + Math.floor(wave / 2)
  });

  zombiesSpawned++;
}
setInterval(spawnZombie, 800);

// ================= GAME CONTROL =================
function restartGame() {
  bullets = [];
  zombies = [];
  grenades = [];
  nukes = 0;

  wave = 1;
  kills = 0;
  killGoal = 5;
  money = 0;
  zombiesSpawned = 0;

  player.health = 3;
  player.maxHealth = 3;
  player.damage = 1;
  player.x = 400;
  player.y = 300;

  gameOver = false;
  waveClear = false;
  shopOpen = false;
}

function nextWave() {
  wave++;
  kills = 0;
  killGoal = 5 + wave * 3;
  zombiesSpawned = 0;
}

// ================= UPDATE =================
function update() {
  if (gameOver || shopOpen) return;

  let now = Date.now();

  // Movement
  if (keys["w"]) player.y -= player.speed;
  if (keys["s"]) player.y += player.speed;
  if (keys["a"]) player.x -= player.speed;
  if (keys["d"]) player.x += player.speed;

  // Bullets
  bullets.forEach((b, bi) => {
    b.x += b.dx;
    b.y += b.dy;
    if (b.x < 0 || b.x > canvas.width || b.y < 0 || b.y > canvas.height) {
      bullets.splice(bi, 1);
    }
  });

  // Zombies
  zombies.forEach((z, zi) => {

    let angle = Math.atan2(player.y - z.y, player.x - z.x);
    z.x += Math.cos(angle) * z.speed;
    z.y += Math.sin(angle) * z.speed;

    // 🔥 PLAYER DAMAGE (FIXED)
    if (
      z.x < player.x + player.width &&
      z.x + z.width > player.x &&
      z.y < player.y + player.height &&
      z.y + z.height > player.y
    ) {
      if (now - player.lastHit > 1000) {
        player.health--;
        player.lastHit = now;

        if (player.health <= 0) {
          gameOver = true;
        }
      }
    }

    // Bullet collision
    bullets.forEach((b, bi) => {
      if (
        b.x > z.x &&
        b.x < z.x + z.width &&
        b.y > z.y &&
        b.y < z.y + z.height
      ) {
        z.health -= player.damage;
        bullets.splice(bi, 1);

        if (z.health <= 0) {
          zombies.splice(zi, 1);
          kills++;
          money += 10;

          if (kills >= killGoal && zombies.length === 0) {
            waveClear = true;
            shopOpen = true;
          }
        }
      }
    });

  });
}

// ================= DRAW =================
function draw() {

  if (shopOpen) {
    ctx.fillStyle = "black";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = "white";
    ctx.font = "36px Arial";
    ctx.fillText("SHOP", 330, 120);
    ctx.fillText("Money: $" + money, 310, 170);

    shopButtons.forEach((btn, i) => {
      ctx.fillStyle = "#444";
      ctx.fillRect(250, 220 + i * 60, 300, 45);

      ctx.fillStyle = "white";
      ctx.font = "18px Arial";
      ctx.fillText(btn.text, 260, 250 + i * 60);
    });

    ctx.fillText("Press ENTER to start next wave", 220, 520);
    return;
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = "#228B22";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = "blue";
  ctx.fillRect(player.x, player.y, player.width, player.height);

  ctx.fillStyle = "yellow";
  bullets.forEach(b => {
    ctx.beginPath();
    ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.fillStyle = "green";
  zombies.forEach(z => {
    ctx.fillRect(z.x, z.y, z.width, z.height);
  });

  ctx.fillStyle = "white";
  ctx.font = "18px Arial";
  ctx.fillText("HP: " + player.health + "/" + player.maxHealth, 20, 30);
  ctx.fillText("Wave: " + wave, 20, 55);
  ctx.fillText("Money: $" + money, 20, 80);
  ctx.fillText("Grenades (G): " + grenades.length, 20, 105);
  ctx.fillText("Nukes (N): " + nukes, 20, 130);

  if (gameOver) {
    ctx.fillStyle = "red";
    ctx.font = "50px Arial";
    ctx.fillText("GAME OVER", 230, 300);
    ctx.font = "20px Arial";
    ctx.fillText("Press SPACE to Restart", 280, 340);
  }
}

function gameLoop() {
  update();
  draw();
  requestAnimationFrame(gameLoop);
}

gameLoop();
