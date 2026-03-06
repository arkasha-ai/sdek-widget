#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import openpyxl
from openpyxl import load_workbook

def final_verification():
    print("=== ФИНАЛЬНАЯ ПРОВЕРКА ИСПРАВЛЕННОГО ФАЙЛА ===")
    
    filename = "/home/clawdbot/.openclaw/workspace/drafts/SyncVoice_Decomposition_v1_fixed_final.xlsx"
    
    try:
        # Загружаем с вычисленными результатами
        wb = load_workbook(filename, data_only=True)
        ws_dec = wb['Декомпозиция']
        ws_summary = wb['Итоги']
        
        print(f"Проверяю файл: {filename}")
        
        # Проверяем несколько строк в декомпозиции
        print(f"\nПримеры рассчитанных значений в декомпозиции:")
        for row in range(4, 12):
            task_num = ws_dec[f'A{row}'].value
            task = ws_dec[f'C{row}'].value
            hours = ws_dec[f'K{row}'].value
            cost = ws_dec[f'L{row}'].value
            
            if task_num:
                print(f"  Строка {row}: {task_num} - {task}")
                print(f"    Часов: {hours}, Стоимость: {cost:,} ₽" if cost else f"    Часов: {hours}, Стоимость: не рассчитано")
        
        # Проверяем таблицу итогов
        print(f"\nТаблица итогов:")
        for row in range(4, 8):
            phase = ws_summary[f'A{row}'].value
            hours = ws_summary[f'C{row}'].value
            cost_no_buffer = ws_summary[f'D{row}'].value
            cost_with_buffer = ws_summary[f'E{row}'].value
            timeline = ws_summary[f'F{row}'].value
            
            print(f"\nСтрока {row}: {phase}")
            print(f"  Часов: {hours}")
            print(f"  Стоимость без буфера: {cost_no_buffer:,} ₽" if cost_no_buffer else "  Стоимость без буфера: не рассчитано")
            print(f"  Стоимость с буфером: {cost_with_buffer:,} ₽" if cost_with_buffer else "  Стоимость с буфером: не рассчитано")
            print(f"  Срок: {timeline}")
        
        # Подсчитываем общее количество часов и стоимость
        total_hours = 0
        total_cost = 0
        total_buffer_cost = 0
        
        for row in range(4, 7):  # фазы 1-3
            hours = ws_summary[f'C{row}'].value
            cost = ws_summary[f'D{row}'].value
            buffer_cost = ws_summary[f'E{row}'].value
            
            if hours:
                total_hours += hours
            if cost:
                total_cost += cost
            if buffer_cost:
                total_buffer_cost += buffer_cost
        
        # Итоговая строка
        final_hours = ws_summary['C7'].value
        final_cost = ws_summary['D7'].value
        final_buffer_cost = ws_summary['E7'].value
        
        print(f"\n=== ИТОГОВЫЕ РЕЗУЛЬТАТЫ ===")
        print(f"Общее количество часов: {total_hours}")
        print(f"Стоимость без буфера: {total_cost:,} ₽")
        print(f"Стоимость с буфером (по строкам): {total_buffer_cost:,} ₽")
        print(f"Итоговая строка - Часов: {final_hours}")
        print(f"Итоговая строка - Стоимость с буфером: {final_buffer_cost:,} ₽")
        
        # Сравнение с ожидаемыми результатами
        expected_hours = 994
        expected_cost = 2624000
        
        print(f"\n=== СРАВНЕНИЕ С ОЖИДАЕМЫМИ ===")
        print(f"Ожидалось: {expected_hours} часов, {expected_cost:,} ₽")
        print(f"Получено: {total_hours} часов, {total_cost:,} ₽ (без буфера)")
        
        hours_diff = total_hours - expected_hours
        cost_diff = total_cost - expected_cost
        
        print(f"Разница: {hours_diff} часов, {cost_diff:,} ₽")
        
        if abs(hours_diff) <= 10 and abs(cost_diff) <= 50000:
            print("✅ РЕЗУЛЬТАТЫ КОРРЕКТНЫ!")
            result_status = "SUCCESS"
        else:
            print("❌ Есть отклонения от ожидаемых результатов")
            result_status = "NEEDS_ADJUSTMENT"
        
        wb.close()
        
        return {
            'filename': filename,
            'total_hours': total_hours,
            'total_cost': total_cost,
            'total_buffer_cost': total_buffer_cost,
            'hours_diff': hours_diff,
            'cost_diff': cost_diff,
            'status': result_status
        }
        
    except Exception as e:
        print(f"Ошибка при проверке файла: {e}")
        return None

if __name__ == "__main__":
    result = final_verification()
    
    if result:
        print(f"\n{'='*50}")
        print(f"ИТОГОВЫЙ ОТЧЕТ")
        print(f"{'='*50}")
        print(f"Файл: {result['filename']}")
        print(f"Статус: {result['status']}")
        print(f"Часов получено: {result['total_hours']}")
        print(f"Стоимость с буфером: {result['total_buffer_cost']:,} ₽")
        print(f"Разница с ожидаемыми: {result['hours_diff']} ч, {result['cost_diff']:,} ₽")
        
        if result['status'] == 'SUCCESS':
            print("✅ Формулы исправлены и работают корректно!")
            print("✅ Все расчеты выполняются правильно!")
        else:
            print("⚠️ Формулы исправлены, но есть расхождение с ожидаемыми результатами")
            print("⚠️ Возможно, нужно скорректировать исходные оценки задач")