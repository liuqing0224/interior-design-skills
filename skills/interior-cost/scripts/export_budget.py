#!/usr/bin/env python3
"""Author the budget workbook with openpyxl and cache the formula results.

Only openpyxl is required (see requirements.txt); no Node runtime and no
proprietary spreadsheet service. Every derived cell keeps its formula, and the
value the formula evaluates to is written as the cached result so headless
readers (openpyxl data_only, verify_2d.py) see the same numbers.
"""
import argparse
import hashlib
import json
import re
import sys
import time
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from PIL import Image, ImageDraw, ImageFont

MISSING_ROW = '缺少输入'
MISSING_SUMMARY = '缺少计价输入'
ERROR_PATTERN = re.compile(r'#REF!|#DIV/0!|#VALUE!|#NAME\?|#N/A|#NUM!|#NULL!')
SHEET_NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL_NS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
DETAIL_HEADERS = ['编号', '类别', '工作内容', '净量', '单位', '损耗率', '计价量', '单价（元）', '金额（元）', '计量依据']
DETAIL_WIDTHS = {'A': 11, 'B': 11, 'C': 31, 'D': 12, 'E': 9, 'F': 10, 'G': 13, 'H': 15, 'I': 17, 'J': 58}
PREVIEW_FONTS = ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf', '/System/Library/Fonts/PingFang.ttc',
                 '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
                 '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                 '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def round4(value):
    return Decimal(value).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def round2(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def evaluate(items, override=None):
    """Mirror the workbook formulas so cached results come from one code path.

    override is (row_index, rate) applied to column H; a None rate means a blank
    cell and must surface the missing-input text instead of a number.
    """
    rows = []
    for index, item in enumerate(items):
        rate = item['rate']
        if override and override[0] == index:
            rate = override[1]
        qty, waste = item['quantity'], item.get('waste', 0)
        purchase = round4(Decimal(str(qty)) * (Decimal(1) + Decimal(str(waste)))) if is_number(qty) and is_number(waste) else MISSING_ROW
        amount = round2(purchase * Decimal(str(rate))) if isinstance(purchase, Decimal) and is_number(rate) else MISSING_ROW
        rows.append((purchase, amount))
    return rows


def summary_of(items, rows, model):
    complete = all(isinstance(row[1], Decimal) for row in rows)
    total = {}
    total['base'] = sum((row[1] for row in rows), Decimal(0)) if complete else MISSING_SUMMARY
    total['reserve'] = round2(total['base'] * Decimal(str(model['reserve_rate']))) if isinstance(total['base'], Decimal) else MISSING_SUMMARY
    total['total'] = total['base'] + total['reserve'] if isinstance(total['base'], Decimal) and isinstance(total['reserve'], Decimal) else MISSING_SUMMARY
    total['remaining'] = round2(Decimal(str(model['budget_cny'])) - total['total']) if isinstance(total['total'], Decimal) else MISSING_SUMMARY
    categories = {}
    for item, row in zip(items, rows):
        key = item['category']
        if key in categories and not isinstance(categories[key], Decimal):
            continue
        if isinstance(row[1], Decimal):
            categories[key] = categories.get(key, Decimal(0)) + row[1]
        else:
            categories[key] = MISSING_SUMMARY
    return total, categories


def build(model, items, geometry):
    book = Workbook()
    summary = book.active
    summary.title = '预算总览'
    detail = book.create_sheet('工程量计价')
    for sheet in (summary, detail):
        sheet.sheet_view.showGridLines = False
    summary.sheet_properties.tabColor = '435D4E'
    detail.sheet_properties.tabColor = 'AE9472'
    first, last = geometry['first'], geometry['last']
    base_row, reserve_row, total_row, remaining_row = geometry['base'], geometry['reserve'], geometry['total'], geometry['remaining']

    summary['B2'] = '%s 室内设计预算' % model['title']
    summary['B3'] = '%s / %s / CNY' % (model['project_id'], model['revision'])
    summary['B5'], summary['C5'] = '目标总预算', model['budget_cny']
    summary['B6'], summary['C6'] = '预备费率', model['reserve_rate']
    summary['E5'] = '蓝色数字为可调整输入'
    summary['B9'], summary['C9'] = '费用类别', '金额（元）'
    for index, category in enumerate(geometry['categories']):
        row = 10 + index
        summary.cell(row=row, column=2, value=category)
        summary.cell(row=row, column=3, value='=IF(COUNT(\'工程量计价\'!I%d:I%d)=%d,SUMIFS(\'工程量计价\'!$I$%d:$I$%d,\'工程量计价\'!$B$%d:$B$%d,B%d),"%s")'
                     % (first, last, len(items), first, last, first, last, row, MISSING_SUMMARY))
    for row, label in [(base_row, '基础费用合计'), (reserve_row, '预备费'), (total_row, '含预备费总额'), (remaining_row, '预算余量')]:
        summary.cell(row=row, column=2, value=label)
    summary['C%d' % base_row] = '=IF(COUNT(\'工程量计价\'!I%d:I%d)=COUNTA(\'工程量计价\'!A%d:A%d),SUM(\'工程量计价\'!I%d:I%d),"%s")' % (first, last, first, last, first, last, MISSING_SUMMARY)
    summary['C%d' % reserve_row] = '=IF(AND(ISNUMBER(C%d),ISNUMBER(C6)),ROUND(C%d*C6,2),"%s")' % (base_row, base_row, MISSING_SUMMARY)
    summary['C%d' % total_row] = '=IF(COUNT(C%d:C%d)=2,SUM(C%d:C%d),"%s")' % (base_row, reserve_row, base_row, reserve_row, MISSING_SUMMARY)
    summary['C%d' % remaining_row] = '=IF(AND(ISNUMBER(C5),ISNUMBER(C%d)),ROUND(C5-C%d,2),"%s")' % (total_row, total_row, MISSING_SUMMARY)
    linked = sum(1 for item in items if item.get('quantity_rule'))
    summary['E%d' % base_row] = '%d/%d行工程量由模型规则计量；其余为明确输入。' % (linked, len(items))
    summary['E%d' % total_row] = '费用范围以本项目明细为准。'

    detail['A2'] = '工程量、损耗与单价'
    detail['A3'] = '单价为本项目估算输入；净量由当前模型导出，来源和计量口径见J列。'
    for column, header in enumerate(DETAIL_HEADERS, 1):
        detail.cell(row=4, column=column, value=header)
    for offset, item in enumerate(items):
        row = first + offset
        values = [item['id'], item['category'], item['name'], item['quantity'], item['unit'],
                  item.get('waste', 0), None, item['rate'], None, item['basis']]
        for column, value in enumerate(values, 1):
            detail.cell(row=row, column=column, value=value)
        detail.cell(row=row, column=7, value='=IF(COUNT(D%d,F%d)=2,ROUND(D%d*(1+F%d),4),"%s")' % (row, row, row, row, MISSING_ROW))
        detail.cell(row=row, column=9, value='=IF(COUNT(G%d,H%d)=2,ROUND(G%d*H%d,2),"%s")' % (row, row, row, row, MISSING_ROW))

    style(summary, detail, geometry)
    book.calculation.fullCalcOnLoad = True
    return book


def style(summary, detail, geometry):
    first, last = geometry['first'], geometry['last']
    base_row, total_row, remaining_row = geometry['base'], geometry['total'], geometry['remaining']
    header_fill = PatternFill('solid', fgColor='435D4E')
    for row in summary['B2:F%d' % (remaining_row + 1)]:
        for cell in row:
            cell.font = Font(name='Arial', size=11, color='263A30')
    summary['B2'].font = Font(name='Arial', size=16, color='263A30')
    for cell in summary['B3:F3'][0]:
        cell.font = Font(name='Arial', size=10, color='7D8178')
    for column, width in {'B': 26, 'C': 20, 'D': 4, 'E': 64}.items():
        summary.column_dimensions[column].width = width
    for row in range(5, 7):
        summary.row_dimensions[row].height = 26
    for row in range(9, remaining_row + 1):
        summary.row_dimensions[row].height = 27
    for cell in summary['B9:C9'][0]:
        cell.fill = header_fill
        cell.font = Font(name='Arial', size=11, color='FFFFFF', bold=True)
    summary.row_dimensions[9].height = 29
    for cell in summary['C5:C6'][0]:
        cell.font = Font(name='Arial', size=11, color='1D5CBD')
    summary['C5'].number_format = '#,##0.00'
    summary['C6'].number_format = '0.0%'
    for row in range(10, remaining_row + 1):
        summary.cell(row=row, column=3).number_format = '#,##0.00'
    border = Border(top=Side(style='thin', color='AE9472'))
    for column in (2, 3):
        summary.cell(row=base_row, column=column).border = border
        cell = summary.cell(row=total_row, column=column)
        cell.fill = PatternFill('solid', fgColor='E7EBDD')
        cell.font = Font(name='Arial', size=12, bold=True, color='263A30')
    for row in range(5, remaining_row + 1):
        summary.cell(row=row, column=5).font = Font(name='Arial', size=10, color='777B70')
    summary.conditional_formatting.add('C%d' % remaining_row, CellIsRule(
        operator='lessThan', formula=['0'],
        fill=PatternFill('solid', fgColor='F7D8D3'),
        font=Font(color='AE3425', bold=True)))

    for row in detail['A2:J%d' % last]:
        for cell in row:
            cell.font = Font(name='Arial', size=10, color='24382E')
    detail['A2'].font = Font(name='Arial', size=15, color='263A30')
    detail['A3'].font = Font(name='Arial', size=10, color='777B70')
    for cell in detail['A4:J4'][0]:
        cell.fill = header_fill
        cell.font = Font(name='Arial', size=10, color='FFFFFF', bold=True)
    detail.row_dimensions[4].height = 30
    for column, width in DETAIL_WIDTHS.items():
        detail.column_dimensions[column].width = width
    for row in range(first, last + 1):
        detail.row_dimensions[row].height = 32
        detail.cell(row=row, column=10).alignment = Alignment(wrap_text=True, vertical='center')
        detail.cell(row=row, column=4).number_format = '0.0000'
        detail.cell(row=row, column=7).number_format = '0.0000'
        detail.cell(row=row, column=6).number_format = '0.0%'
        for column in (8, 9):
            detail.cell(row=row, column=column).number_format = '#,##0.00'
        for column in (4, 6, 8):
            detail.cell(row=row, column=column).font = Font(name='Arial', size=10, color='1D5CBD')
    detail.freeze_panes = 'D5'


def cached_values(rows, totals, categories, geometry):
    """Cell reference to cached value, per sheet, for every formula cell."""
    values = {'预算总览': {}, '工程量计价': {}}
    for key, cell in geometry['cells'].items():
        values['预算总览'][cell] = totals[key]
    for index, category in enumerate(geometry['categories']):
        values['预算总览']['C%d' % (10 + index)] = categories[category]
    for offset, row in enumerate(rows):
        reference = geometry['first'] + offset
        values['工程量计价']['G%d' % reference] = row[0]
        values['工程量计价']['I%d' % reference] = row[1]
    return values


def sheet_paths(archive):
    workbook = ET.fromstring(archive.read('xl/workbook.xml'))
    rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
    targets = {rel.get('Id'): rel.get('Target') for rel in rels}
    paths = {}
    for sheet in workbook.find(SHEET_NS + 'sheets'):
        target = targets[sheet.get(REL_NS + 'id')].lstrip('/')
        paths[sheet.get('name')] = target if target.startswith('xl/') else 'xl/' + target
    return paths


def inject(path, values):
    """Write cached results into the formula cells openpyxl leaves empty."""
    staging = path.with_name(path.name + '.cache')
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(staging, 'w', zipfile.ZIP_DEFLATED) as target:
        wanted = {sheet_paths(source)[name]: cells for name, cells in values.items()}
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename in wanted:
                text = data.decode('utf-8')
                for reference, value in wanted[item.filename].items():
                    text = replace_cell(text, reference, value)
                data = text.encode('utf-8')
            target.writestr(item, data)
    replace_with_retry(staging, path)


def replace_cell(text, reference, value):
    pattern = re.compile(r'<c r="%s"([^>]*)>(<f>.*?</f>)<v /></c>' % reference, re.S)
    match = pattern.search(text)
    if not match:
        raise ValueError('Formula cell not found for cached value: ' + reference)
    if isinstance(value, Decimal):
        attributes, body = match.group(1), '<v>%s</v></c>' % format(value, 'f')
    else:
        attributes, body = match.group(1) + ' t="str"', '<v>%s</v></c>' % escape(str(value))
    return text[:match.start()] + '<c r="%s"%s>%s%s' % (reference, attributes, match.group(2), body) + text[match.end():]


def check_artifact(path, values, geometry):
    cached = load_workbook(path, data_only=True)
    formulas = load_workbook(path, data_only=False)
    try:
        for sheet, cells in values.items():
            for reference, value in cells.items():
                actual = cached[sheet][reference].value
                if isinstance(value, Decimal):
                    if not is_number(actual) or abs(Decimal(str(actual)) - value) > Decimal('0.000005'):
                        raise ValueError('Cached value differs at %s!%s' % (sheet, reference))
                elif actual != value:
                    raise ValueError('Cached text differs at %s!%s' % (sheet, reference))
        for row in range(geometry['first'], geometry['last'] + 1):
            if formulas['工程量计价']['I%d' % row].data_type != 'f':
                raise ValueError('Missing amount formula at I%d' % row)
    finally:
        cached.close()
        formulas.close()


def scan_errors(path):
    hits = []
    cached = load_workbook(path, data_only=True)
    formulas = load_workbook(path, data_only=False)
    try:
        for sheet in formulas.sheetnames:
            for book, label in ((formulas, 'formula'), (cached, 'value')):
                for row in book[sheet].iter_rows():
                    for cell in row:
                        if isinstance(cell.value, str) and ERROR_PATTERN.search(cell.value):
                            hits.append('%s!%s %s %s' % (sheet, cell.coordinate, label, cell.value))
    finally:
        cached.close()
        formulas.close()
    return hits


def key_range(path, geometry):
    rows = []
    book = load_workbook(path, data_only=True, read_only=True)
    try:
        sheet = book['工程量计价']
        for row in range(geometry['first'], min(geometry['last'], 8) + 1):
            rows.append([sheet.cell(row=row, column=column).value for column in range(1, 11)])
    finally:
        book.close()
    return {'kind': 'table', 'sheet': '工程量计价', 'address': 'A%d:J%d' % (geometry['first'], min(geometry['last'], 8)),
            'rows': len(rows), 'cols': 10, 'values': rows}


def preview_font(size):
    for candidate in PREVIEW_FONTS:
        if not Path(candidate).is_file():
            continue
        try:
            return ImageFont.truetype(candidate, size, index=0)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_table(path, title, headers, rows, widths, right=()):
    small = preview_font(16)
    line = 46
    image = Image.new('RGB', (sum(widths) + 40, 90 + line * (len(rows) + 1)), '#FFFEFA')
    draw = ImageDraw.Draw(image)
    draw.text((20, 18), title, font=preview_font(22), fill='#263A30')
    draw.rectangle([20, 60, 20 + sum(widths), 60 + line], fill='#435D4E')
    for index, header in enumerate(headers):
        draw.text((20 + sum(widths[:index]) + 8, 74), header, font=small, fill='#FFFFFF')
    for row_index, row in enumerate(rows):
        top = 60 + line * (row_index + 1)
        if row_index % 2:
            draw.rectangle([20, top, 20 + sum(widths), top + line], fill='#F4F5F0')
        for index, value in enumerate(row):
            text = str(value)
            limit = widths[index] - 16
            while text and draw.textlength(text, font=small) > limit:
                text = text[:-1]
            left = 20 + sum(widths[:index])
            if index in right:
                draw.text((left + widths[index] - 8 - draw.textlength(text, font=small), top + 14), text, font=small, fill='#24382E')
            else:
                draw.text((left + 8, top + 14), text, font=small, fill='#24382E')
    image.save(path)


def money(value):
    return format(value, ',.2f') if isinstance(value, Decimal) else str(value)


def render_previews(project, model, items, totals, categories, rows):
    """Regenerate the delivery previews from the same numbers the workbook shows."""
    state = project / 'state'
    label = '%s / %s' % (model['project_id'], model['revision'])
    draw_table(state / 'budget-summary-preview.png', '%s 预算总览  %s' % (model['title'], label),
               ['费用类别', '金额（元）'],
               [[key, money(value)] for key, value in categories.items()] +
               [['基础费用合计', money(totals['base'])], ['预备费', money(totals['reserve'])],
                ['含预备费总额', money(totals['total'])], ['预算余量', money(totals['remaining'])]],
               [360, 220], right=(1,))
    body = []
    for index, item in enumerate(items[:4]):
        purchase, amount = rows[index]
        body.append([item['id'], item['category'], item['name'], item['quantity'], item['unit'],
                     item.get('waste', 0), money(purchase), item['rate'], money(amount), item['basis']])
    draw_table(state / 'budget-detail-preview.png', '工程量计价  %s' % label, DETAIL_HEADERS, body,
               [110, 110, 240, 100, 60, 80, 110, 100, 130, 300], right=(3, 5, 6, 7, 8))


def geometry_of(items):
    categories = list(dict.fromkeys(item['category'] for item in items))
    base = max(19, 11 + len(categories))
    return {'categories': categories, 'first': 5, 'last': 4 + len(items), 'base': base,
            'reserve': base + 1, 'total': base + 2, 'remaining': base + 3,
            'cells': {'base': 'C%d' % base, 'reserve': 'C%d' % (base + 1),
                      'total': 'C%d' % (base + 2), 'remaining': 'C%d' % (base + 3)}}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stale_rows(model, items):
    """Rows whose net quantity or unit input no longer matches the model."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'interior-orchestrator/scripts'))
    import project_tools
    stale = []
    for item, row in zip(items, model['budget']):
        try:
            expected = round4(project_tools.quantity_for(model, row))
        except (KeyError, TypeError, ValueError) as exc:
            raise SystemExit('Budget quantity rule is invalid for %s: %s' % (row.get('id'), exc))
        if (item['id'] != row['id'] or item['rate'] != row['rate'] or item.get('waste', 0) != row.get('waste', 0)
                or abs(Decimal(str(item['quantity'])) - expected) > Decimal('0.00005')):
            stale.append(row['id'])
    return stale


def replace_with_retry(staging, path):
    """Windows keeps a just-written workbook locked long enough to fail os.replace."""
    for attempt in range(5):
        try:
            staging.replace(path)
            return
        except PermissionError:
            if attempt == 4:
                staging.unlink(missing_ok=True)
                raise SystemExit('Cannot replace %s; close the workbook in other programs and rerun' % path.name)
            time.sleep(0.2 * (attempt + 1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project', type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    model = json.loads((project / 'model/project.json').read_text(encoding='utf-8'))
    expected = json.loads((project / 'schedules/budget-summary.json').read_text(encoding='utf-8'))
    items = json.loads((project / 'schedules/budget-inputs.json').read_text(encoding='utf-8'))
    if not items:
        raise SystemExit('Budget must contain at least one line')
    if [item['id'] for item in items] != [item['id'] for item in model['budget']]:
        raise SystemExit('schedules/budget-inputs.json does not match model/budget; rerun project_tools.py schedules')
    stale = stale_rows(model, items)
    if stale:
        raise SystemExit('schedules/budget-inputs.json is stale for %s; rerun project_tools.py schedules' % ', '.join(stale[:5]))
    geometry = geometry_of(items)
    rows = evaluate(items)
    totals, categories = summary_of(items, rows, model)
    if abs(Decimal(str(expected['total'])) - totals['total']) > Decimal('0.005'):
        raise SystemExit('Workbook total differs from budget-summary.json; rerun project_tools.py schedules')
    if abs(Decimal(str(expected['remaining'])) - totals['remaining']) > Decimal('0.01'):
        raise SystemExit('Workbook remaining differs from budget-summary.json')
    changed = summary_of(items, evaluate(items, (0, items[0]['rate'] + 10)), model)[0]
    if not isinstance(changed['total'], Decimal) or changed['total'] <= totals['total']:
        raise SystemExit('Raising the first rate must increase the total')
    blank, blank_categories = summary_of(items, evaluate(items, (0, None)), model)
    if blank['total'] != MISSING_SUMMARY or blank_categories[items[0]['category']] != MISSING_SUMMARY:
        raise SystemExit('A blank rate must surface the missing-input text')
    zero = summary_of(items, evaluate(items, (0, 0)), model)[0]['total']
    if not isinstance(zero, Decimal) or zero >= totals['total']:
        raise SystemExit('A zero rate must preserve the row and lower the total')

    values = cached_values(rows, totals, categories, geometry)
    book = build(model, items, geometry)
    output = project / 'schedules' / ('%s_预算.xlsx' % model['title'])
    output.parent.mkdir(parents=True, exist_ok=True)
    book.save(output)
    inject(output, values)
    check_artifact(output, values, geometry)

    errors = scan_errors(output)
    state = project / 'state'
    state.mkdir(parents=True, exist_ok=True)
    (state / 'workbook-error-scan.txt').write_text(json.dumps(
        {'kind': 'notice', 'message': 'Cell search matched %d entries.' % len(errors)}, ensure_ascii=False) + '\n', encoding='utf-8')
    if errors:
        raise SystemExit('Workbook errors detected: ' + '; '.join(errors[:5]))
    (state / 'workbook-key-ranges.txt').write_text(json.dumps(key_range(output, geometry), ensure_ascii=False) + '\n', encoding='utf-8')
    render_previews(project, model, items, totals, categories, rows)
    (state / 'workbook-check.json').write_text(json.dumps({
        'revision': model['revision'], 'total': float(totals['total']), 'remaining': float(totals['remaining']),
        'independentTotal': expected['total'], 'input_change_recalculated': float(changed['total']),
        'missing_input_exposed': True, 'zero_preserved': True, 'restored': True,
        'engine': 'openpyxl', 'cached_values': 'decimal-mirror', 'cells': geometry['cells'],
        'model_sha256': digest(project / 'model/project.json'), 'xlsx_sha256': digest(output)}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'total': float(totals['total']), 'remaining': float(totals['remaining']),
                      'rows': len(items), 'exported': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
