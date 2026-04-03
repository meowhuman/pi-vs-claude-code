#!/usr/bin/env python3
"""
ARTLIKE HK — New Tour Generator
Run: python3 generate-tour.py
Or called by /ALI:ali-new-tour slash command
"""

import json
import csv
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
EXPORTS_DIR = BASE_DIR / 'exports'
EXPORTS_DIR.mkdir(exist_ok=True)


def load_rates():
    with open(DATA_DIR / 'rates.json') as f:
        r = json.load(f)
    return r


def load_existing_dancers():
    """Load dancer list from most recent tour for reuse."""
    tour_files = sorted(DATA_DIR.glob('tour-*.json'))
    if not tour_files:
        return []
    with open(tour_files[-1]) as f:
        data = json.load(f)
    return data.get('dancers', [])


def prompt(msg, default=None):
    suffix = f' [{default}]' if default else ''
    val = input(f'{msg}{suffix}: ').strip()
    return val if val else default


def prompt_list(msg):
    print(f'{msg} (逐個輸入，空白行完成)')
    items = []
    while True:
        val = input('  > ').strip()
        if not val:
            break
        items.append(val)
    return items


def build_dancer_map(existing_dancers):
    """Show existing dancers and let user reuse or add new ones."""
    if existing_dancers:
        print('\n現有舞蹈員名單：')
        for i, d in enumerate(existing_dancers, 1):
            print(f'  {i:2}. {d["nickname"]:10} {d["name_zh"]}')
        print('  (直接輸入編號選擇，或輸入新舞蹈員 "英文名,中文名")')
    return existing_dancers


def select_dancers(existing_dancers, label='舞蹈員'):
    """Interactive dancer selection — reuse existing or add new."""
    dancer_map = {d['nickname'].lower(): d for d in existing_dancers}
    selected = []
    print(f'\n選擇{label} (輸入英文名/編號，空白完成，"all" = 全選上站):')
    while True:
        val = input('  > ').strip()
        if not val:
            break
        if val.lower() == 'all':
            return [d['id'] for d in existing_dancers if d.get('role') != 'choreographer']
        if val.isdigit():
            idx = int(val) - 1
            if 0 <= idx < len(existing_dancers):
                selected.append(existing_dancers[idx]['id'])
        elif ',' in val:
            # New dancer: "nickname,中文名"
            parts = val.split(',', 1)
            new_d = {
                'id': parts[0].strip().lower(),
                'nickname': parts[0].strip(),
                'name_zh': parts[1].strip()
            }
            existing_dancers.append(new_d)
            dancer_map[new_d['id']] = new_d
            selected.append(new_d['id'])
            print(f'  ✓ 新增: {new_d["nickname"]} {new_d["name_zh"]}')
        else:
            match = dancer_map.get(val.lower())
            if match:
                selected.append(match['id'])
            else:
                print(f'  ⚠ 找不到 "{val}"，略過')
    return selected


def collect_reh_groups(dancer_ids, existing_dancers):
    """Collect rehearsal hours — supports split groups."""
    print('\n排練時數設定：')
    print('  "all,20" = 所有人20小時')
    print('  "20" 然後分組輸入 = 不同人不同時數')
    groups = []
    first = input('  全部相同時數？輸入小時數，或按 Enter 分組: ').strip()
    if first.isdigit():
        groups.append({'hours': int(first), 'dancers': 'all', 'count': len(dancer_ids)})
    else:
        remaining = list(dancer_ids)
        while remaining:
            hrs = input(f'  下一組時數 (剩餘 {len(remaining)} 人): ').strip()
            if not hrs.isdigit():
                break
            print(f'  選擇做 {hrs} 小時的舞蹈員 (空白 = 其餘全部):')
            names = input('  英文名 (空格分隔): ').strip().split()
            if not names:
                groups.append({'hours': int(hrs), 'dancers': remaining[:], 'count': len(remaining)})
                remaining = []
            else:
                matched = [n.lower() for n in names if n.lower() in remaining]
                groups.append({'hours': int(hrs), 'dancers': matched, 'count': len(matched)})
                remaining = [r for r in remaining if r not in matched]
    return groups


def calc_station_totals(s, rates):
    r = rates
    shows = s['shows']
    chore_fee = r['choreographer']['double_show'] if shows > 1 else r['choreographer']['standard']

    # Show fees
    dancers_count = len(s['dancers_in_show'])
    puppet = s.get('puppet_dancer')
    standard_count = dancers_count
    show_fee = standard_count * r['dancer']['show_fee_standard'] * shows
    if puppet:
        show_fee = (standard_count * r['dancer']['show_fee_standard'] +
                    r['dancer']['show_fee_puppet']) * shows

    # Reh fee
    reh_fee = 0
    for g in s['reh_groups']:
        count = g['count'] if g['dancers'] == 'all' else len(g['dancers']) if isinstance(g['dancers'], list) else g['count']
        reh_fee += g['hours'] * r['dancer']['reh_fee_per_hour'] * count

    # Full run
    if puppet:
        full_run = (standard_count * r['dancer']['full_run_standard'] +
                    r['dancer']['full_run_puppet'])
    else:
        full_run = standard_count * r['dancer']['full_run_standard']

    # Studio
    studio_hrs = max(g['hours'] for g in s['reh_groups']) if s['reh_groups'] else 0
    studio = studio_hrs * r['studio_per_hour']

    admin = r['admin_fee']
    total = chore_fee + admin + show_fee + reh_fee + full_run + studio

    s['choreographer_fee'] = chore_fee
    s['admin_fee'] = admin
    s['show_fee_total'] = show_fee
    s['reh_fee_total'] = reh_fee
    s['full_run_total'] = full_run
    s['studio_hours'] = studio_hrs
    s['studio_total'] = studio
    s['grand_total'] = total
    return s


def export_csvs(data, rates, tour_slug):
    out_dir = EXPORTS_DIR / tour_slug
    out_dir.mkdir(exist_ok=True)

    # 01 Tour summary
    with open(out_dir / '01-tour-summary.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['站', '城市', '日期', '場次', '人數', '報價總額(HKD)',
                    '編舞費', 'Admin費', 'Show Fee', 'Reh Fee', 'Full Run', '場地費',
                    '收款截止日', '狀態'])
        total = 0
        for s in data['stations']:
            show_date = datetime.strptime(s['date'], '%Y-%m-%d')
            due = show_date + timedelta(days=rates['payment_terms']['client_to_ali_days'])
            w.writerow([f"第{s['id']}站", s['city'], s['date'], s['shows'],
                        s['dancer_count'], s['grand_total'],
                        s['choreographer_fee'], s['admin_fee'],
                        s['show_fee_total'], s['reh_fee_total'],
                        s['full_run_total'], s['studio_total'],
                        due.strftime('%Y-%m-%d'), '待收'])
            total += s['grand_total']
        w.writerow([])
        w.writerow(['', '', '', '', '合計', total])

    # 02 Payroll
    dancer_map = {d['id']: d for d in data['dancers']}
    rows = []
    for s in data['stations']:
        all_dancers = list(s['dancers_in_show'])
        puppet = s.get('puppet_dancer')
        if puppet and puppet not in all_dancers:
            all_dancers.append(puppet)

        reh_hours = {}
        for g in s['reh_groups']:
            hrs = g['hours']
            if g['dancers'] == 'all':
                for did in all_dancers:
                    reh_hours[did] = hrs
            else:
                for did in g['dancers']:
                    reh_hours[did] = hrs

        for did in all_dancers:
            d = dancer_map.get(did, {'nickname': did, 'name_zh': did})
            is_puppet = (did == puppet)
            show_unit = rates['dancer']['show_fee_puppet'] if is_puppet else rates['dancer']['show_fee_standard']
            show_fee = show_unit * s['shows']
            reh_hrs = reh_hours.get(did, 0)
            reh_fee = reh_hrs * rates['dancer']['reh_fee_per_hour']
            full_run = rates['dancer']['full_run_puppet'] if is_puppet else rates['dancer']['full_run_standard']
            total_pay = show_fee + reh_fee + full_run
            rows.append([f"第{s['id']}站 {s['city']}", s['id'], s['city'], s['date'],
                         d.get('name_zh', did), d.get('nickname', did),
                         'Puppet' if is_puppet else 'Dancer',
                         s['shows'], show_unit, show_fee, reh_hrs, reh_fee, full_run, total_pay,
                         '未付', ''])

    with open(out_dir / '02-payroll-all-stations.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['站次', '站號', '城市', '日期', '舞蹈員', '英文名', '角色',
                    '場次', 'Show Fee/場', 'Show Fee小計',
                    '排練時數', '排練費', 'Full Run', '應付總額', '狀態', '付款日'])
        w.writerows(rows)

    # 03 Dancer summary
    from collections import defaultdict
    earnings = defaultdict(lambda: {'stations': 0, 'total': 0, 'cities': []})
    for r in rows:
        earnings[r[4]]['stations'] += 1
        earnings[r[4]]['total'] += r[13]
        earnings[r[4]]['cities'].append(r[2])

    with open(out_dir / '03-dancer-earnings-summary.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['舞蹈員', '參與站數', '預計總收入(HKD)', '城市'])
        for name, info in sorted(earnings.items(), key=lambda x: -x[1]['total']):
            w.writerow([name, info['stations'], info['total'], ' / '.join(info['cities'])])

    # 04 Payment tracker
    with open(out_dir / '04-payment-tracker.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['站', '城市', '演出日', '金額',
                    '客戶付款截止', '客戶狀態', '實際收款日',
                    '舞蹈員付款期限', '舞蹈員狀態'])
        for s in data['stations']:
            show_date = datetime.strptime(s['date'], '%Y-%m-%d')
            client_due = show_date + timedelta(days=rates['payment_terms']['client_to_ali_days'])
            w.writerow([f"第{s['id']}站", s['city'], s['date'], s['grand_total'],
                        client_due.strftime('%Y-%m-%d'), '待收', '',
                        f"收款後{rates['payment_terms']['ali_to_dancers_days']}天內", '待付'])

    print(f'\n✓ CSV 已輸出至 {out_dir}/')
    return out_dir


def main():
    rates = load_rates()
    existing_dancers = load_existing_dancers()

    print('=' * 50)
    print('ARTLIKE HK — 新巡迴設定')
    print('=' * 50)

    tour_name = prompt('巡迴名稱', 'Leon Concert Tour 2027 走埠')
    client = prompt('客戶', 'Paciwood Music & Entertainment Ltd')
    client_contact = prompt('客戶聯絡人', 'Bryant Chau')
    year = tour_name[:4] if tour_name[:4].isdigit() else '2027'
    tour_slug = f'tour-{year}'

    # Check if file exists
    out_path = DATA_DIR / f'{tour_slug}.json'
    if out_path.exists():
        suffix = prompt(f'{tour_slug}.json 已存在，新檔案後綴', 'b')
        tour_slug = f'{tour_slug}{suffix}'
        out_path = DATA_DIR / f'{tour_slug}.json'

    existing_dancers = build_dancer_map(existing_dancers)

    stations = []
    station_id = 1
    print('\n開始逐站輸入 (城市空白 = 完成):')

    while True:
        print(f'\n--- 第 {station_id} 站 ---')
        city = prompt('城市').strip()
        if not city:
            break

        date_str = prompt('日期 (YYYY-MM-DD)')
        shows = int(prompt('場次數', '1'))

        # Dancers
        print('\n舞蹈員選擇：')
        dancer_ids = select_dancers(existing_dancers, '演出舞蹈員')
        dancer_count = len(dancer_ids)

        puppet = prompt('Puppet 舞蹈員英文名 (沒有請按 Enter)', '')
        puppet = puppet.lower() if puppet else None

        reh_groups = collect_reh_groups(dancer_ids, existing_dancers)

        show_date = datetime.strptime(date_str, '%Y-%m-%d')
        payment_due = show_date + timedelta(days=rates['payment_terms']['client_to_ali_days'])

        s = {
            'id': station_id,
            'city': city,
            'date': date_str,
            'shows': shows,
            'payment_due_date': payment_due.strftime('%Y-%m-%d'),
            'payment_status': 'pending',
            'payment_received': None,
            'dancers_in_show': dancer_ids,
            'puppet_dancer': puppet,
            'dancer_count': dancer_count,
            'reh_groups': reh_groups,
            'notes': prompt('備注 (可留空)', '')
        }
        s = calc_station_totals(s, rates)
        print(f'  ✓ 第{station_id}站 {city} — 報價：HKD ${s["grand_total"]:,}')
        stations.append(s)
        station_id += 1

    if not stations:
        print('沒有輸入任何站次，結束。')
        return

    data = {
        'meta': {
            'company': 'ARTLIKE HONG KONG LIMITED',
            'choreographer': 'Wong So Ting Alison',
            'choreographer_zh': '黃素亭',
            'client': client,
            'client_contact': client_contact,
            'tour_name': tour_name,
            'bank_name': 'HSBC',
            'bank_account': '801-632522-838',
            'email': 'alijai1105@gmail.com',
            'tel': '91283263',
            'address': '1/f, 2A Pak Kong Au, Po Lo Che, Sai Kung, Hong Kong'
        },
        'rates_ref': 'data/rates.json',
        'dancers': existing_dancers,
        'stations': stations
    }

    with open(out_path, 'w', ensure_ascii=False, indent=2) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'\n✓ 資料已儲存：{out_path}')

    export_csvs(data, rates, tour_slug)

    total = sum(s['grand_total'] for s in stations)
    print(f'\n=== 完成 ===')
    print(f'巡迴：{tour_name}')
    print(f'站數：{len(stations)} 站')
    print(f'報價總額：HKD ${total:,}')
    print(f'資料檔：doc/ali-admin/data/{tour_slug}.json')
    print(f'試算表：doc/ali-admin/exports/{tour_slug}/')


if __name__ == '__main__':
    main()
