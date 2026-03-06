#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import openpyxl
from openpyxl import load_workbook

def update_summary_sheet(filename):
    print("=== ОБНОВЛЕНИЕ ТАБЛИЦЫ ИТОГОВ ===")
    
    wb = load_workbook(filename, data_only=False)
    ws_dec = wb['Декомпозиция']
    ws_summary = wb['Итоги']
    
    # Подсчет по фазам
    print("\nПодсчет по фазам:")
    
    # Phase 1: строки 4-11 (8 задач)
    phase1_hours = 0
    phase1_cost = 0
    print("\nPhase 1 (строки 4-11):")
    for row in range(4, 12):
        hours = ws_dec[f'K{row}'].value or 0
        cost = ws_dec[f'L{row}'].value or 0
        phase1_hours += hours
        phase1_cost += cost
        print(f"  Строка {row}: {hours} ч, {cost:,} ₽")
    
    # Phase 2: строки 12-24 (13 задач) 
    phase2_hours = 0
    phase2_cost = 0
    print("\nPhase 2 (строки 12-24):")
    for row in range(12, 25):
        hours = ws_dec[f'K{row}'].value or 0
        cost = ws_dec[f'L{row}'].value or 0
        phase2_hours += hours
        phase2_cost += cost
        print(f"  Строка {row}: {hours} ч, {cost:,} ₽")
    
    # Phase 3: строки 25-34 (10 задач)
    phase3_hours = 0
    phase3_cost = 0
    print("\nPhase 3 (строки 25-34):")
    for row in range(25, 35):
        hours = ws_dec[f'K{row}'].value or 0
        cost = ws_dec[f'L{row}'].value or 0
        phase3_hours += hours
        phase3_cost += cost
        print(f"  Строка {row}: {hours} ч, {cost:,} ₽")
    
    # Итого
    total_hours = phase1_hours + phase2_hours + phase3_hours
    total_cost = phase1_cost + phase2_cost + phase3_cost
    
    # Стоимость с буфером +15%
    phase1_buffer = phase1_cost * 1.15
    phase2_buffer = phase2_cost * 1.15
    phase3_buffer = phase3_cost * 1.15
    total_buffer = total_cost * 1.15
    total_hours_buffer = total_hours * 1.15
    
    print(f"\nИТОГИ:")
    print(f"Phase 1: {phase1_hours} ч, {phase1_cost:,} ₽ (без буфера), {phase1_buffer:,.0f} ₽ (с буфером)")
    print(f"Phase 2: {phase2_hours} ч, {phase2_cost:,} ₽ (без буфера), {phase2_buffer:,.0f} ₽ (с буфером)")
    print(f"Phase 3: {phase3_hours} ч, {phase3_cost:,} ₽ (без буфера), {phase3_buffer:,.0f} ₽ (с буфером)")
    print(f"ВСЕГО: {total_hours} ч, {total_cost:,} ₽ (без буфера)")
    print(f"С БУФЕРОМ: {total_hours_buffer:.0f} ч, {total_buffer:,.0f} ₽")
    
    # Обновляем таблицу итогов
    print(f"\nОбновляю таблицу итогов...")
    
    # Phase 1
    ws_summary['C4'] = phase1_hours
    ws_summary['D4'] = phase1_cost
    ws_summary['E4'] = phase1_buffer
    
    # Phase 2
    ws_summary['C5'] = phase2_hours
    ws_summary['D5'] = phase2_cost
    ws_summary['E5'] = phase2_buffer
    
    # Phase 3
    ws_summary['C6'] = phase3_hours
    ws_summary['D6'] = phase3_cost
    ws_summary['E6'] = phase3_buffer
    
    # Итого с буфером
    ws_summary['C7'] = total_hours_buffer
    ws_summary['D7'] = total_cost
    ws_summary['E7'] = total_buffer
    
    # Сохраняем файл
    output_filename = filename.replace('_calculated.xlsx', '_final.xlsx')
    wb.save(output_filename)
    wb.close()
    
    print(f"Сохранен итоговый файл: {output_filename}")
    
    return output_filename, {
        'phase1': {'hours': phase1_hours, 'cost': phase1_cost, 'buffer_cost': phase1_buffer},
        'phase2': {'hours': phase2_hours, 'cost': phase2_cost, 'buffer_cost': phase2_buffer},
        'phase3': {'hours': phase3_hours, 'cost': phase3_cost, 'buffer_cost': phase3_buffer},
        'total': {'hours': total_hours, 'cost': total_cost, 'buffer_hours': total_hours_buffer, 'buffer_cost': total_buffer}
    }

def verify_results(result_data):
    print(f"\n=== СРАВНЕНИЕ С ОЖИДАЕМЫМИ РЕЗУЛЬТАТАМИ ===")
    
    expected_hours = 994
    expected_cost = 2624000
    
    actual_hours = result_data['total']['hours']
    actual_cost = result_data['total']['cost']
    actual_buffer_cost = result_data['total']['buffer_cost']
    
    print(f"Ожидалось: {expected_hours} часов, {expected_cost:,} ₽")
    print(f"Получено (без буфера): {actual_hours} часов, {actual_cost:,} ₽")
    print(f"Получено (с буфером): {result_data['total']['buffer_hours']:.0f} часов, {actual_buffer_cost:,.0f} ₽")
    
    hours_diff = actual_hours - expected_hours
    cost_diff = actual_cost - expected_cost
    
    print(f"Разница (без буфера): {hours_diff} часов, {cost_diff:,} ₽")
    
    if abs(hours_diff) <= 10 and abs(cost_diff) <= 50000:
        print("✅ Результаты в пределах допустимой погрешности!")
        return True
    else:
        print("❌ Значительные отклонения от ожидаемых результатов")
        return False

if __name__ == "__main__":
    filename = "/home/clawdbot/.openclaw/workspace/drafts/SyncVoice_Decomposition_v1_fixed_calculated.xlsx"
    
    final_file, results = update_summary_sheet(filename)
    is_accurate = verify_results(results)
    
    print(f"\n=== ФИНАЛЬНЫЕ РЕЗУЛЬТАТЫ ===")
    print(f"✅ Файл успешно исправлен и сохранен: {final_file}")
    print(f"✅ Всего часов: {results['total']['hours']}")
    print(f"✅ Стоимость с буфером: {results['total']['buffer_cost']:,.0f} ₽")
    
    if is_accurate:
        print("✅ Расчеты корректны!")
    else:
        print("⚠️  Требуется дополнительная проверка данных")