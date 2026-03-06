#!/usr/bin/env python3
"""
Создание Excel файла с декомпозицией проекта
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime, timedelta

# Создаём workbook
wb = Workbook()
ws = wb.active
ws.title = "Декомпозиция"

# Стили
header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
border_style = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)
center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
left_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

# Заголовки
headers = ['ID', 'Этап', 'Задача', 'Подзадачи', 'Исполнитель', 'Срок', 'Статус', 'Приоритет']

# Ширина колонок
ws.column_dimensions['A'].width = 8
ws.column_dimensions['B'].width = 15
ws.column_dimensions['C'].width = 30
ws.column_dimensions['D'].width = 35
ws.column_dimensions['E'].width = 15
ws.column_dimensions['F'].width = 12
ws.column_dimensions['G'].width = 12
ws.column_dimensions['H'].width = 10

# Рисуем заголовки
for col_num, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col_num)
    cell.value = header
    cell.font = header_font
    cell.fill = header_fill
    cell.border = border_style
    cell.alignment = center_alignment

# Данные декомпозиции (LLM проект для Gravity)
data = [
    [
        '1.0',
        'Подготовка',
        'Анализ требований',
        'Сбор требований от стейкхолдеров\nАнализ текущей системы\nОпределение KPI',
        'Тимлид',
        '3 дня',
        '✅ Готово',
        'Высокий'
    ],
    [
        '1.1',
        '',
        '',
        'Интервью с PM, Dev, QA\nДокументирование use cases\nАнализ gaps',
        '',
        '',
        '',
        ''
    ],
    [
        '2.0',
        'Архитектура',
        'Проектирование системы',
        'Выбор LLM модели\nПроектирование API\nАрхитектура БД',
        'Архитектор',
        '5 дней',
        '🟡 В работе',
        'Высокий'
    ],
    [
        '2.1',
        '',
        '',
        'Анализ GLM-4.7, Qwen, GPT\nREST API design\nPostgreSQL + Qdrant',
        '',
        '',
        '',
        ''
    ],
    [
        '3.0',
        'Разработка',
        'Backend API',
        'FastAPI приложение\nEndpoints для LLM\nRate limiting',
        'Backend Dev',
        '7 дней',
        '🟡 В работе',
        'Высокий'
    ],
    [
        '3.1',
        '',
        '',
        'Auth middleware\nRAG implementation\nCaching strategy',
        '',
        '',
        '',
        ''
    ],
    [
        '3.2',
        '',
        'Frontend',
        'React/Vue приложение\nUI для чата\nАдмин-панель',
        'Frontend Dev',
        '10 дней',
        '⏳ Планируется',
        'Средний'
    ],
    [
        '4.0',
        'Интеграция',
        'LLM Integration',
        'Настройка LiteLLM\nFine-tuning модели\nPrompt engineering',
        'ML Engineer',
        '5 дней',
        '⏳ Планируется',
        'Высокий'
    ],
    [
        '4.1',
        '',
        '',
        'API подключение\nTest prompts\nQuality checks',
        '',
        '',
        '',
        ''
    ],
    [
        '5.0',
        'Тестирование',
        'QA Testing',
        'Unit тесты\nIntegration тесты\nE2E тесты',
        'QA Engineer',
        '6 дней',
        '⏳ Планируется',
        'Высокий'
    ],
    [
        '5.1',
        '',
        '',
        'pytest coverage\nLoad testing\nSecurity audit',
        '',
        '',
        '',
        ''
    ],
    [
        '6.0',
        'Деплой',
        'CI/CD',
        'GitLab CI/CD пайплайн\nDocker контейнеры\nMonitoring',
        'DevOps',
        '4 дня',
        '⏳ Планируется',
        'Средний'
    ],
    [
        '7.0',
        'Документация',
        'Tech docs',
        'API документация\nUser guide\nRunbooks',
        'Tech Writer',
        '3 дня',
        '⏳ Планируется',
        'Низкий'
    ],
    [
        '8.0',
        'Запуск',
        'Production',
        'Blue-green deploy\nRollback plan\nMonitoring alerts',
        'DevOps',
        '2 дня',
        '⏳ Планируется',
        'Критический'
    ],
]

# Заполняем данные
for row_num, row_data in enumerate(data, 2):
    for col_num, cell_value in enumerate(row_data, 1):
        cell = ws.cell(row=row_num, column=col_num)
        cell.value = cell_value
        cell.border = border_style

        # Выравнивание по содержимому
        if col_num in [1, 5, 6, 7, 8]:  # ID, исполнитель, срок, статус, приоритет
            cell.alignment = center_alignment
        else:
            cell.alignment = left_alignment

        # Цвет для статусов
        if col_num == 7:  # Статус
            if '✅' in str(cell_value):
                cell.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
            elif '🟡' in str(cell_value):
                cell.fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
            elif '⏳' in str(cell_value):
                cell.fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')

        # Цвет для приоритетов
        if col_num == 8:  # Приоритет
            if 'Критический' in str(cell_value):
                cell.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
            elif 'Высокий' in str(cell_value):
                cell.fill = PatternFill(start_color='FCE4D6', end_color='FCE4D6', fill_type='solid')

# Выравниваем высоту строк
for row in ws.iter_rows():
    ws.row_dimensions[row[0].row].height = 25

# Добавляем легенду
ws.row_dimensions[1].height = 30

# Сохраняем
output_file = '/home/clawdbot/.openclaw/workspace/drafts/gravity_llm_decomposition.xlsx'
wb.save(output_file)

print(f"✅ Файл создан: {output_file}")
print("📊 Декомпозиция LLM проекта для Gravity")
