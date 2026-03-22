# HTML шаблоны карточек

## ✅ Финальный рабочий шаблон (frosted glass, центрирование)

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { width: 900px; height: 900px; font-family: 'Nunito', sans-serif; overflow: hidden; }
.card { width: 900px; height: 900px; position: relative; overflow: hidden; }
.bg {
  position: absolute; inset: 0;
  background-image: url('file:///tmp/result.jpg');
  background-size: cover; background-position: center;
}
.left-gradient {
  position: absolute; inset: 0;
  background: linear-gradient(105deg,
    rgba(255,245,235,0.6) 0%, rgba(255,245,235,0.4) 35%,
    rgba(255,245,235,0.0) 52%);
}
.content {
  position: relative; z-index: 10;
  height: 100%; display: flex; flex-direction: column;
  padding: 50px 44px; max-width: 430px;
}
.brand {
  display: inline-block; background: #1A1A1A; color: #fff;
  font-size: 12px; font-weight: 800; letter-spacing: 3.5px;
  padding: 7px 18px; border-radius: 4px; width: fit-content;
  text-transform: uppercase;
}
.age-badge {
  display: inline-flex; align-items: center; justify-content: center;
  background: #F5A623; color: #fff;
  font-size: 20px; font-weight: 900;
  width: 54px; height: 54px; border-radius: 50%;
  margin-top: 12px;
  box-shadow: 0 6px 20px rgba(245,166,35,0.4);
}
.text-block { margin-top: auto; }
.big-number {
  font-size: 96px; font-weight: 900; color: #E68900;
  line-height: 0.88; letter-spacing: -3px;
}
.big-number-sub { font-size: 22px; font-weight: 800; color: #E68900; margin-top: 6px; }
.main-title {
  font-size: 40px; font-weight: 900; color: #1A1A1A;
  line-height: 1.1; margin-top: 18px; text-transform: uppercase;
}
.subtitle { font-size: 16px; font-weight: 600; color: #7a6a55; margin-top: 8px; font-style: italic; }
.pills { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 20px; }
.pill {
  background: rgba(255,255,255,0.75); border: 1.5px solid rgba(230,137,0,0.35);
  color: #b85c00; font-size: 12.5px; font-weight: 700;
  padding: 6px 13px; border-radius: 100px;
}
.bottom-bar {
  margin-top: 20px; padding-top: 14px;
  border-top: 1.5px solid rgba(0,0,0,0.1);
  display: flex; gap: 18px; flex-wrap: wrap;
}
.check-item { font-size: 11.5px; font-weight: 700; color: #666; display: flex; align-items: center; gap: 4px; }
.check { color: #E68900; font-size: 14px; }
</style>
</head>
<body>
<div class="card">
  <div class="bg"></div>
  <div class="left-gradient"></div>
  <div class="content">
    <div class="brand">BRAND</div>
    <div class="age-badge">0+</div>
    <div class="text-block">
      <div class="big-number">60+</div>
      <div class="big-number-sub">мелодий и звуков</div>
      <div class="main-title">Название<br>товара</div>
      <div class="subtitle">Подзаголовок</div>
      <div class="pills">
        <div class="pill">💡 Фича 1</div>
        <div class="pill">🌿 Фича 2</div>
        <div class="pill">🔋 Фича 3</div>
      </div>
      <div class="bottom-bar">
        <div class="check-item"><span class="check">✓</span> Сертифицировано</div>
        <div class="check-item"><span class="check">✓</span> Безопасно</div>
        <div class="check-item"><span class="check">✓</span> Гарантия 1 год</div>
      </div>
    </div>
  </div>
</div>
</body>
</html>
```

## Цветовые схемы

| Тема | Акцент | Фон градиент | Текст |
|------|--------|--------------|-------|
| Детская / тёплая | `#E68900` | `rgba(255,245,235,0.6)` | `#1A1A1A` |
| Тёмная / премиум | `#C8A96E` | `rgba(10,10,20,0.65)` | `#FFFFFF` |
| Свежая / зелёная | `#2E9E5B` | `rgba(235,248,240,0.6)` | `#1A1A1A` |
| Розовая / женская | `#D4618A` | `rgba(255,240,245,0.6)` | `#1A1A1A` |

## Размеры для разных платформ

| Платформа | Размер | Aspect ratio |
|-----------|--------|--------------|
| WB / Ozon (квадрат) | 900×900 | 1:1 |
| WB (портрет) | 900×1200 | 3:4 |
| Instagram | 1080×1080 | 1:1 |
| Instagram Stories | 1080×1920 | 9:16 |
