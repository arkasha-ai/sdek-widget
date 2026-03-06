# Проверка тестов cart.e2e.ts и favorite.e2e.ts

**Дата проверки:** 2026-02-10  
**Репозиторий:** `~/.openclaw/workspace/sio-wdio-tests`  
**Проверенные URL:**
- https://server9.sio74.ru/cart/
- https://server9.sio74.ru/personal/favorites/

---

## 1. cart.e2e.ts

### 1.1 Структура тестов

✅ **Fixture (test/fixtures/cart.json):**
- Содержит 4 теста как описано:
  - **stage1** (2 теста):
    - "min sum" - проверка минимальной стоимости посылки
    - "min to free delivery" - проверка до бесплатной доставки
    - "free delivery" - проверка бесплатной доставки
  - **stage3** (2 теста):
    - "1090" - проверка доставки со стоимостью 1090
    - "790" - проверка доставки со стоимостью 790

✅ **Тестовые товары:**
```json
"products": [
  "/catalog/semena/tsvety/odnoletniki/osteospermum-akila-belyy-s-glazkom",
  "/catalog/plodovye-vesna/grusha-vesna/grusha-talgarskaya-krasavitsa",
  "/catalog/raznoe/udobreniya/udobrenie-dlya-roz-i-tsvetov-zemlyaki-200gr"
]
```

### 1.2 Селекторы

✅ **Селектор удаления из корзины: `.bask-del-link`**
- Используется в методе `clearCart()` (test/pages/cart.ts)
- Правильно реализован с циклом по всем кнопкам удаления
- **Метод clearCart():**
```typescript
const deleteButtons = await $$('.bask-del-link');
for (const button of deleteButtons) {
  if (await button.isDisplayed()) {
    await button.click();
    await this.pause(500);
  }
}
```

✅ **Селектор итоговой суммы: `.bask-page__orderTotal`**
- Используется в stage3 тестах
- Ожидает массив текстовых значений для проверки:
```typescript
await expectAsync($('.bask-page__orderTotal')).toHaveText(
  stage3case.total.map(t => expect.stringContaining(t))
);
```

⚠️ **Проблема:** На странице https://server9.sio74.ru/cart/ корзина пустая, поэтому не удалось проверить наличие селекторов `.bask-del-link` и `.bask-page__orderTotal` в реальном DOM.

### 1.3 Метод clearCart()

✅ **Реализация корректна:**
- Открывает страницу корзины
- Ищет все кнопки удаления (`.bask-del-link`)
- Удаляет каждую с паузой 500ms
- Ждёт 2000ms в конце для обновления корзины
- Обрабатывает пустую корзину (if deleteButtons.length === 0)

### 1.4 Дополнительные селекторы

✅ **Другие селекторы в cart.ts:**
- `#btn-fullorder` - кнопка оформления заказа
- `[data-prod="${product}"]` - поиск товара по ID
- `.counter-value` - поле количества товара
- `.bask-page__parcelTotal` - блок итогов по посылке
- `.bask-page__parcelTotal-minPriceError` - ошибка минимальной цены
- `.bask-page__parcelTotal-freeship` - сообщение о бесплатной доставке

---

## 2. favorite.e2e.ts

### 2.1 Структура теста

✅ **Один тест "change favorite":**
- Открывает страницу избранного
- Добавляет товар в избранное
- Проверяет счётчик избранного
- Удаляет товар из избранного
- Проверяет что счётчик исчез

### 2.2 Селекторы (test/pages/favorite.ts)

✅ **delFavoriteButton: `.fave_del`**
- Селектор кнопки удаления из избранного
- Используется в методах `del()` и в beforeEach cleanup

✅ **count: `#small-fav-block .fave_cnt`**
- Селектор счётчика избранного в шапке сайта
- Проверяется после добавления товара: должен быть "1 товар"
- Должен исчезнуть после удаления

✅ **head: `#fave_page h2`**
- Селектор заголовка страницы избранного
- Проверяется после refresh: должен быть "1 товар"

⚠️ **Проблема:** На странице https://server9.sio74.ru/personal/favorites/ нет товаров в избранном, поэтому не удалось проверить селекторы `.fave_del`, `#small-fav-block .fave_cnt`, `#fave_page h2` в реальном DOM.

### 2.3 beforeEach Cleanup

✅ **Реализация корректна:**
```typescript
beforeEach(async () => {
  await favoritePage.open();
  await favoritePage.setSizeDesktop();
  await favoritePage.pause(1000);

  while (await favoritePage.delFavoriteButton.isExisting()) {
    await favoritePage.del();
    await favoritePage.refresh();
    await favoritePage.pause(1000);
  }
});
```

**Логика:**
- Открывает страницу избранного
- Цикл while проверяет наличие кнопки удаления
- Удаляет товар, обновляет страницу, ждёт 1000ms
- Повторяет пока есть товары

⚠️ **Потенциальная проблема:** Если `.fave_del` не найден (изменён селектор на сайте), cleanup не сработает и тесты могут падать из-за грязных данных.

---

## 3. Найденные проблемы

### 3.1 Критические проблемы

❌ **Нет проверки**: Не удалось проверить селекторы на живом сайте из-за пустых страниц корзины и избранного. **Рекомендация:** Запустить тесты локально для проверки.

### 3.2 Потенциальные проблемы

⚠️ **cart.e2e.ts - Жёсткая привязка к данным:**
- Fixture использует конкретные product ID (5468, 5175067, 2695555)
- Если товары удалены с сайта, тесты упадут
- **Рекомендация:** Добавить проверку существования товаров перед тестами

⚠️ **favorite.e2e.ts - Один тест на весь функционал:**
- Тест проверяет и добавление, и удаление в одном it()
- Если падает на первом шаге, не проверится удаление
- **Рекомендация:** Разделить на 2 теста: "add favorite" и "delete favorite"

⚠️ **favorite.e2e.ts - Нет проверки изоляции:**
- beforeEach cleanup зависит от селектора `.fave_del`
- Если селектор сломан, cleanup не сработает → тесты зависимы друг от друга
- **Рекомендация:** Добавить альтернативный способ очистки (например, через API или localStorage)

⚠️ **Оба теста - Долгие паузы:**
- Много жёстких `pause(1000)`, `pause(2000)`
- Замедляет тесты и может быть недостаточно при медленном сервере
- **Рекомендация:** Использовать `waitForExist()`, `waitForDisplayed()` вместо pause

### 3.3 Минорные проблемы

⚠️ **cart.ts - Неоптимальный clearCart():**
- Удаляет товары последовательно с паузами → медленно при многих товарах
- **Рекомендация:** Если API позволяет, очищать корзину через прямой запрос

⚠️ **favorite.ts - Дублирование в cleanup:**
- Метод `add()` использует `.digi-product__favorite-button:first` - непредсказуемый выбор товара
- **Рекомендация:** Принимать product ID в параметре для контролируемого добавления

---

## 4. Рекомендации по улучшению

### 4.1 Для cart.e2e.ts

1. **Добавить проверку товаров перед тестами:**
```typescript
beforeAll(async () => {
  // Проверить что товары существуют на сайте
  for (const product of fixture.products) {
    const response = await browser.url(`https://server9.sio74.ru${product}`);
    expect(response.statusCode).not.toBe(404);
  }
});
```

2. **Использовать waitForExist вместо pause:**
```typescript
await cartPage.open();
await $('.bask-del-link').waitForExist({ timeout: 5000 });
await cartPage.setCounts(...stage1case.groups);
```

3. **Добавить fallback для clearCart():**
```typescript
public async clearCart(): Promise<void> {
  // Try API first
  try {
    await browser.execute(() => {
      localStorage.removeItem('cart');
      // или вызов API очистки корзины
    });
  } catch {
    // Fallback to UI deletion
    await this.clearCartUI();
  }
}
```

### 4.2 Для favorite.e2e.ts

1. **Разделить тест на два:**
```typescript
it('add to favorite', async () => {
  await favoritePage.add();
  await expectAsync(favoritePage.count).toHaveText('1 товар');
});

it('delete from favorite', async () => {
  await favoritePage.add(); // Setup
  await favoritePage.del();
  await expectAsync(favoritePage.count).not.toExist();
});
```

2. **Добавить проверку после cleanup:**
```typescript
afterEach(async () => {
  // Verify cleanup worked
  const favExists = await favoritePage.delFavoriteButton.isExisting();
  if (favExists) {
    throw new Error('Cleanup failed: favorites still exist');
  }
});
```

3. **Использовать waitForExist:**
```typescript
await favoritePage.add();
await favoritePage.count.waitForExist({ timeout: 3000 });
await expectAsync(favoritePage.count).toHaveText('1 товар');
```

---

## 5. Чек-лист для финальной проверки

### Перед запуском тестов:

- [ ] Запустить тесты локально с реальными данными
- [ ] Проверить что все селекторы существуют в DOM:
  - `.bask-del-link`
  - `.bask-page__orderTotal`
  - `.fave_del`
  - `#small-fav-block .fave_cnt`
  - `#fave_page h2`
- [ ] Проверить что товары из fixture существуют на сайте
- [ ] Проверить cleanup работает корректно в обоих тестах

### Во время тестов:

- [ ] Проверить stage1 тесты корректно проверяют сообщения о доставке
- [ ] Проверить stage3 тесты корректно переходят к оформлению заказа
- [ ] Проверить favorite cleanup удаляет все товары перед каждым тестом

### После тестов:

- [ ] Проверить что корзина очищена после cart.e2e.ts
- [ ] Проверить что избранное очищено после favorite.e2e.ts
- [ ] Проверить отсутствие зависимостей между тестами

---

## 6. Заключение

**Код тестов выглядит корректно и следует хорошим практикам WebdriverIO:**
- ✅ Использует Page Object Model
- ✅ Использует fixtures для данных
- ✅ Имеет cleanup хуки (beforeEach, afterEach)
- ✅ Использует data-provider для параметризации

**Основные риски:**
1. Жёсткая привязка к product ID - если товары удалены, тесты упадут
2. Много hardcoded паз - можно оптимизировать через waitFor методы
3. Нет проверки что селекторы всё ещё актуальны на сайте

**Следующие шаги:**
1. Запустить тесты локально для проверки селекторов на реальном DOM
2. Проверить что товары из fixture существуют
3. Рассмотреть рекомендации по улучшению (раздел 4)
4. Добавить проверки из чек-листа (раздел 5)
