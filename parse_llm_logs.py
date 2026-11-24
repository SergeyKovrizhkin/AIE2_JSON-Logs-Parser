import json
import sys
import argparse

TOKENS_LIMIT = 1000

def InputFile(input_path):
    data = []
    error_status = 0
    logs_count = 0
    try:
        with open(input_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line:
                    try:
                        single_log = json.loads(line)
                        if not isinstance(single_log, dict):
                            print("Warning: строка входного файла не является словарем", file=sys.stderr)                            
                        elif 'tokens_used' in single_log:
                            if isinstance(single_log['tokens_used'], int):
                                logs_count += 1
                                data.append(single_log)
                            else:
                                print("Warning: tokens_used не является целым числом", file=sys.stderr)
                    except json.JSONDecodeError:
                        print("Warning: строка не является корректным JSON", file=sys.stderr)                            
    except FileNotFoundError:
        error_status = 1
        print("Error: Входной файл не найден", file=sys.stderr)
    except PermissionError:
        error_status = 1
        print("Error: Нет доступа к входному файлу", file=sys.stderr)    
    if error_status == 0 and logs_count == 0:
        error_status = 1
        print("Error: Во входном файле отсутствуют корректные данные", file=sys.stderr)
    return data, error_status, logs_count

def AnalyseData(data, metrics):
    result_data = [] 
    for single_log in data:
        if single_log['tokens_used'] > TOKENS_LIMIT:
            metrics['filtered_count'] += 1
            metrics['total_tokens'] += single_log['tokens_used']
            result_data.append(single_log)
            metrics = LatencyCalcs(single_log, metrics)
            if 'error' in single_log and single_log['error'] != "":
                metrics['errors_in_log_count'] += 1            
    if metrics['count_avg_latency'] > 0:
        metrics['avg_latency_ms'] = round(metrics['total_latency_ms'] / metrics['count_avg_latency'], 1)    
    return result_data, metrics

def LatencyCalcs(single_log, metrics):
    if 'latency_ms' in single_log:
        if isinstance(single_log['latency_ms'], int):
            metrics['count_avg_latency'] += 1
            metrics['total_latency_ms'] += single_log['latency_ms']
            if single_log['latency_ms'] > metrics['max_latency_ms']:
                metrics['max_latency_ms'] = single_log['latency_ms']
        else:
            print("Warning: latency_ms не является целым числом", file=sys.stderr)
    return metrics

def OutputFile(output_path, result_data):
    error_status = 0
    try:
        with open(output_path, 'w', encoding='utf-8') as output_file:
            json.dump(result_data, output_file, ensure_ascii=False, indent=4)
    except FileNotFoundError:
        error_status = 1
        print("Error: Выходной файл не найден", file=sys.stderr)
    except PermissionError:
        error_status = 1
        print("Error: Нет доступа к выходному файлу", file=sys.stderr)
    return error_status
        
def OutputReport(report_path, logs_count, metrics):
    error_status = 0
    report = {
        'total_entries': logs_count,
        'filtered_entries': metrics['filtered_count'],
        'token_threshold': TOKENS_LIMIT,
        'total_tokens': metrics['total_tokens'],
        'avg_latency_ms': metrics['avg_latency_ms'],
        'extra_latency_metric': {"name": "max_latency_ms", "value": metrics['max_latency_ms']},
        'errors_in_log_count': metrics['errors_in_log_count']
    }
    try:
        with open(report_path, 'w', encoding='utf-8') as report_file:
            json.dump(report, report_file, ensure_ascii=False, indent=4)  
    except FileNotFoundError:
        error_status = 1
        print("Error: Файл отчета не найден", file=sys.stderr)
    except PermissionError:
        error_status = 1
        print("Error: Нет доступа к файлу отчета", file=sys.stderr)
    return error_status    

def main():
    
    parser = argparse.ArgumentParser(description="Программа для обработки логов запросов к ИИ")
    parser.add_argument("--input_path", help="Путь к входному файлу", default="data/logs.jsonl")
    parser.add_argument("--output_path", help="Путь к выходному файлу", default="results/filtered_logs.json")
    parser.add_argument("--report_path", help="Путь к файлу отчета", default="results/report.json")
    args = parser.parse_args()
    
    error_status = 0
    result_data = []
    input_path = args.input_path
    output_path = args.output_path
    report_path = args.report_path
    logs_count = 0
    metrics = {
        'filtered_count': 0,
        'total_tokens': 0,
        'count_avg_latency': 0,
        'total_latency_ms': 0,
        'avg_latency_ms': 0,
        'max_latency_ms': 0,
        'errors_in_log_count': 0
        }
    
    data, error_status, logs_count = InputFile(input_path)
    if error_status == 0:
        result_data, metrics = AnalyseData(data, metrics)
    error_status += OutputFile(output_path, result_data)
    error_status += OutputReport(report_path, logs_count, metrics)
    if error_status > 1:
        error_status = 1
    
    print(f"Общее количество обработанных записей: {logs_count}")
    print(f"Количество записей, прошедших фильтр: {metrics['filtered_count']}")
    print(f"Выбранный порог: более {TOKENS_LIMIT} токенов")
    
    sys.exit(error_status)
    
    
if __name__ == '__main__':
    main()