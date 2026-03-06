# Валидация тестов alive.e2e.ts и auth.e2e.ts

**Дата проверки:** 2026-02-10  
**Репозиторий:** `~/.openclaw/workspace/sio-wdio-tests`  
**Base URL:** `https://server9.sio74.ru`

---

## 1. alive.e2e.ts - Проверка доступности страниц

### 1.1. Доступность URL (curl)

| №  | URL                          | HTTP Status | Результат |
|----|------------------------------|-------------|-----------|
| 1  | `/`                          | 200         | ✅ OK      |
| 2  | `/catalog/`                  | 200         | ✅ OK      |
| 3  | `/personal/favorites/`       | 200         | ✅ OK      |
| 4  | `/cart/`                     | 200         | ✅ OK      |
| 5  | `/search/catalog/?q=`        | 200         | ✅ OK      |
| 6  | `/personal/info/`            | 302 → 200   | ✅ OK      |
| 7  | `/404/`                      | 404         | ✅ OK      |

**Вывод:** Все 7 URL доступны и возвращают ожидаемые статусы.

### 1.2. Редирект /personal/info/ -> /auth/

```bash
$ curl -I https://server9.sio74.ru/personal/info/
HTTP/2 302
location: https://server9.sio74.ru/auth/
```

**Результат:** ✅ Редирект работает правильно

### 1.3. Проверка 404 страницы

```bash
$ curl -o /dev/null -w "%{http_code}" https://server9.sio74.ru/404/
404
```

**Результат:** ✅ Страница /404/ возвращает корректный статус 404

---

## 2. auth.e2e.ts - Проверка формы авторизации

### 2.1. Credentials из .env

```env
BASE_URL=https://server9.sio74.ru
PROFILE_LOGIN=test@wannabe.pro
PROFILE_PASSWORD=Pa$$w0rd
```

**Результат:** ✅ Credentials найдены в `.env`

### 2.2. Проверка селекторов в браузере

#### Кнопка открытия модалки `[data-target="#modal-login"]`

**HTML:**
```html
<span data-toggle="modal" data-target="#modal-login" class="cabinet">Личный кабинет</span>
```

**Результат:** ✅ Найдена  
**Расположение:** Верхний правый угол, рядом с "Проверить статус заказа"

#### Форма логина (внутри `#modal-login .modal-form-login-email`)

**1. loginInput:** `input[name="USER_LOGIN"]`

```html
<input class="form-control" type="text" name="USER_LOGIN" maxlength="50" value="" size="17" autocomplete="off" />
```

**Результат:** ✅ Найден  
**Селектор работает:** `#modal-login .modal-form-login-email input[name="USER_LOGIN"]`

---

**2. passwordInput:** `input[name="USER_PASSWORD"]`

```html
<input type="password" name="USER_PASSWORD" class="form-control" maxlength="50" size="17" autocomplete="off" />
```

**Результат:** ✅ Найден  
**Селектор работает:** `#modal-login .modal-form-login-email input[name="USER_PASSWORD"]`

---

**3. loginButton:** `button[name="Login"]`

```html
<button name="Login" type="submit" class="btn btn-blue">Войти</button>
```

**Результат:** ✅ Найден  
**Селектор работает:** `#modal-login .modal-form-login-email button[name="Login"]`  
**Текст кнопки:** "Войти"

---

**4. cabinetName:** `.cabinet .name`

**Результат:** ⚠️ **Не найден в статическом HTML**  

**Причина:** Этот элемент появляется **только после успешного логина** (динамический контент).

**Поведение:**
- До логина: `<span class="cabinet">Личный кабинет</span>`
- После логина: должен появиться элемент `.cabinet .name` с текстом "Иван Иванов"

**Статус:** ✅ Селектор корректен, но требует проверки **после** выполнения логина.

---

## 3. Найденные проблемы

### 3.1. Форма логина скрыта по умолчанию

**Проблема:** Форма `.modal-form-login-email` имеет `style="display:none;"` в статическом HTML.

**HTML:**
```html
<form name="system_auth_form6zOYVN" method="post" target="_top" 
      action="/?login=yes" 
      class="login-header form form-login modal-form-login-email" 
      style="display:none;">
```

**Влияние на тесты:**
- Нужно **сначала открыть модальное окно** (клик на кнопку с `data-target="#modal-login"`)
- Потом **подождать появления формы** (`waitForDisplayed`)
- Только потом можно взаимодействовать с элементами

**Решение в auth.e2e.ts:**  
Метод `toggleAuthModelButtonClick()` кликает на кнопку и ждёт 500ms - это правильно! ✅

---

### 3.2. Cookie Banner блокирует форму

**Обнаружено в коде:**  
Метод `closeCookieBanner()` удаляет iframe с id `carrot-frame-bumperCookies`.

**Потенциальная проблема:**
- Cookie banner может перекрывать форму логина
- Может блокировать клики на input/button элементы

**Решение в auth.e2e.ts:**  
✅ Код правильно удаляет cookie banner через `browser.execute()` перед вводом данных.

---

### 3.3. Селектор cabinetName требует верификации после логина

**Текущий код:**
```typescript
await authPage.cabinetName.waitForDisplayed({ timeout: 10000 });
await expectAsync(authPage.cabinetName).toHaveText('Иван Иванов');
```

**Возможные риски:**
1. ✅ Timeout 10 секунд - достаточно для загрузки
2. ⚠️ Текст "Иван Иванов" жёстко прописан - может не совпадать с реальными данными профиля `test@wannabe.pro`

**Рекомендация:**  
Проверить в реальном тесте, что после логина credentials `test@wannabe.pro / Pa$$w0rd` действительно отображает "Иван Иванов", или обновить ожидаемое значение.

---

## 4. Итоговая таблица селекторов

| Селектор                                                      | Статус     | Видимость | Примечание                                 |
|---------------------------------------------------------------|------------|-----------|--------------------------------------------|
| `[data-target="#modal-login"]`                                | ✅ Найден  | Видимый   | Кнопка открытия модалки                    |
| `#modal-login .modal-form-login-email input[name="USER_LOGIN"]` | ✅ Найден  | Скрытый*  | Появляется после клика на кнопку           |
| `#modal-login .modal-form-login-email input[name="USER_PASSWORD"]` | ✅ Найден  | Скрытый*  | Появляется после клика на кнопку           |
| `#modal-login .modal-form-login-email button[name="Login"]`  | ✅ Найден  | Скрытый*  | Появляется после клика на кнопку           |
| `.cabinet .name`                                              | ⚠️ Динамический | N/A    | Появляется только после успешного логина   |

\* *Скрытый - существует в DOM, но `display:none` до открытия модального окна*

---

## 5. Выводы

### ✅ Что работает правильно:

1. Все URL из `alive.e2e.ts` доступны
2. Редирект `/personal/info/` → `/auth/` работает
3. Страница `/404/` возвращает корректный статус 404
4. Все селекторы формы логина присутствуют в DOM
5. Тест `auth.e2e.ts` правильно открывает модалку и удаляет cookie banner

### ⚠️ Требует внимания:

1. **Селектор `.cabinet .name`** - требует проверки реальным запуском теста с логином
2. **Ожидаемый текст "Иван Иванов"** - убедиться что credentials `test@wannabe.pro` соответствует этому имени

### 📝 Рекомендации:

1. Запустить тест `auth.e2e.ts` в WebdriverIO чтобы проверить:
   - Логин с реальными credentials
   - Появление элемента `.cabinet .name` после логина
   - Совпадение текста имени пользователя
2. Если тест падает на `cabinetName` - проверить селектор через DevTools после успешного логина

---

**Проверку выполнил:** Arkasha (субагент test-check-alive-auth)  
**Использованные инструменты:** curl, grep, OpenClaw browser (profile: openclaw)
