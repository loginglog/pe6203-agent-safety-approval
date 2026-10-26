// Offline workbook and figure authoring from the verified analysis JSON.
// Use the bundled Node runtime and a node_modules link in results/raw/analysis_build_20261019.
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const runtime = path.join(root, 'results/raw/analysis_build_20261019');
const require = createRequire(path.join(runtime, 'context.cjs'));
const { Workbook, SpreadsheetFile } = await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const sharp = (await import(pathToFileURL(require.resolve('sharp')).href)).default;
const out = path.join(root, 'results/analysis_20261019');
const data = JSON.parse(await fs.readFile(path.join(out, 'analysis.json'), 'utf8'));
const wb = Workbook.create();
const summary = wb.worksheets.add('Results');
const cases = wb.worksheets.add('CaseData');
const costs = wb.worksheets.add('CostData');
const palette = ['#2864B4', '#C77525', '#087F72'];
const names = ['FullApprove', 'FullEscalate', 'Candidate v0.4.0'];
const strategies = ['full-approve', 'full-escalate', 'candidate'];
const scopes = ['all_six_exploratory', 'excluding_development_task28'];
const range = (sheet, a1) => sheet.getRange(a1);
const set = (sheet, a1, value) => { range(sheet, a1).values = [[value]]; };
const formula = (sheet, a1, value) => { range(sheet, a1).formulas = [[value]]; };
function header(sheet, a1) {
  range(sheet, a1).format = { fill: '#263C56', font: { name: 'Arial', size: 10, bold: true, color: '#FFFFFF' },
    horizontalAlignment: 'center', verticalAlignment: 'center', rowHeight: 32, wrapText: true };
}
function title(sheet, a1, value) {
  set(sheet, a1, value);
  range(sheet, a1).format.font = { name: 'Arial', size: 15, bold: true, color: '#20344E' };
}
for (const sheet of [summary, cases, costs]) sheet.showGridLines = false;
summary.tabColor = '#263C56';
range(summary, 'A1:Y86').format.font = { name: 'Arial', size: 10, color: '#263444' };
range(summary, 'A1:Y86').format.rowHeight = 23;
range(summary, 'A1:A86').format.columnWidth = 3;
range(summary, 'B1:B86').format.columnWidth = 20;
range(summary, 'C1:C86').format.columnWidth = 7;
range(summary, 'D1:G86').format.columnWidth = 10;
range(summary, 'H1:J86').format.columnWidth = 13;
range(summary, 'K1:L86').format.columnWidth = 15;
range(summary, 'M1:M86').format.columnWidth = 3;
range(summary, 'N1:Y86').format.columnWidth = 10;
title(summary, 'B2', 'PE6203 normal-condition results');
set(summary, 'B3', 'Exploratory native-score-based TCR. Provisional audit, one repetition per cell.');
set(summary, 'B4', 'SDK 3.31.0. Quality flags remain separate; no original task score was changed.');
range(summary, 'B3:L4').format.font = { name: 'Arial', size: 10, italic: true, color: '#586779' };

const caseHeaders = ['Task', 'Strategy', 'k', 'Development', 'Native utility', 'Success', 'False', 'Unknown', 'Scope support', 'Reviews', 'Tool bodies', 'Error flag', 'Quality flag', 'Grounding quality', 'Email format quality', 'Unread answer flag', 'Accounted USD', 'Unsettled', 'Case ID', 'Source result', 'Quality findings', 'Failure category'];
const caseRows = data.case_data.map(c => [c.task_id, c.strategy, c.k, c.development_used, c.native_utility,
  c.native_success, c.native_false, c.native_unknown, c.provisional_scope_supported, c.reviews_all,
  c.tool_body_entries, c.error_recorded, c.answer_quality_flag,
  Number(c.quality_findings.includes('missing_source_grounding')), Number(c.quality_findings.includes('email_date_format')),
  Number(c.quality_findings.includes('six_returned_messages')), Number(c.conservative_accounted_usd),
  c.unsettled_reservations, c.case_id, c.source_result, c.quality_findings, c.primary_failure]);
range(cases, 'A1:V55').values = [caseHeaders, ...caseRows];
cases.tables.add('A1:V55', true, 'CaseObservations');
range(cases, 'A1:V55').format.font = { name: 'Arial', size: 10, color: '#263444' };
range(cases, 'A1:V55').format.rowHeight = 23;
range(cases, 'A1:V55').format.columnWidth = 14;
range(cases, 'A1:B55').format.columnWidth = 20;
range(cases, 'C1:D55').format.columnWidth = 11;
range(cases, 'F2:R55').format.horizontalAlignment = 'right';
range(cases, 'Q2:Q55').setNumberFormat('0.00000000');
range(cases, 'S1:T55').format.columnWidth = 75;
range(cases, 'U1:V55').format.columnWidth = 85;
header(cases, 'A1:V1');
cases.freezePanes.freezeRows(1);
cases.freezePanes.freezeColumns(2);
range(cases, 'H2:H55').conditionalFormats.add('cellIs', { operator: 'greaterThan', formula: 0, format: { fill: '#FFF0C2', font: { color: '#8B5300' } } });
range(cases, 'M2:P55').conditionalFormats.add('cellIs', { operator: 'greaterThan', formula: 0, format: { fill: '#FFF0C2' } });
set(cases, 'X1', 'Sources');
set(cases, 'X2', 'Normal inventory and original result files; source per row.');
set(cases, 'X3', 'Authorization audit revision 3 and both author classification decisions.');
set(cases, 'X4', 'Quality labels are supplementary; native utility is unchanged.');
range(cases, 'X1:X4').format.columnWidth = 90;

const costHeaders = ['Task', 'Strategy', 'k', 'Development', 'Component', 'API requests', 'Known input tokens', 'Known output tokens', 'Known credits USD', 'Unknown cost flag', 'Complete credits USD', 'Rate estimate USD', 'Case ID', 'Source result'];
const costRows = data.cost_data.map(c => [c.task_id, c.strategy, c.k, c.development_used, c.component, c.api_requests,
  c.known_input_tokens, c.known_output_tokens, Number(c.known_reported_usd_credits), c.unknown_reported_cost,
  c.complete_reported_usd_credits === null ? null : Number(c.complete_reported_usd_credits),
  Number(c.known_rate_estimate_usd), c.case_id, c.source_result]);
range(costs, 'A1:N163').values = [costHeaders, ...costRows];
costs.tables.add('A1:N163', true, 'ComponentObservations');
range(costs, 'A1:N163').format.font = { name: 'Arial', size: 10, color: '#263444' };
range(costs, 'A1:N163').format.rowHeight = 23;
range(costs, 'A1:N163').format.columnWidth = 18;
range(costs, 'A1:B163').format.columnWidth = 20;
range(costs, 'C1:D163').format.columnWidth = 11;
range(costs, 'F2:L163').format.horizontalAlignment = 'right';
range(costs, 'I2:I163').setNumberFormat('0.00000000');
range(costs, 'K2:L163').setNumberFormat('0.00000000');
range(costs, 'M1:N163').format.columnWidth = 75;
header(costs, 'A1:N1');
costs.freezePanes.freezeRows(1);
costs.freezePanes.freezeColumns(2);
range(costs, 'J2:J163').conditionalFormats.add('cellIs', { operator: 'greaterThan', formula: 0, format: { fill: '#FFF0C2' } });
set(costs, 'P1', 'Known credits are a subtotal, not an invoice.');
set(costs, 'P2', 'Blank complete cost means unavailable, not zero.');
set(costs, 'P3', 'Diagnostic review replay excluded: USD0.00023145 reported separately.');
range(costs, 'P1:P3').format.columnWidth = 90;

const metricHeaders = ['Strategy', 'k', 'Tasks', 'Native true', 'Native false', 'Unknown', 'TCR lower', 'TCR upper', 'Reviews all', 'Reviews on success', 'Quality flags'];
function criteria(row, sheet, excluded) {
  return `'${sheet}'!$B$2:$B$${sheet === 'CaseData' ? 55 : 163},$B${row},'${sheet}'!$C$2:$C$${sheet === 'CaseData' ? 55 : 163},$C${row}`
    + (excluded ? `,'${sheet}'!$D$2:$D$${sheet === 'CaseData' ? 55 : 163},0` : '');
}
for (let scopeIndex = 0; scopeIndex < 2; scopeIndex++) {
  const start = scopeIndex ? 25 : 8;
  set(summary, `B${start - 2}`, scopeIndex ? 'Five-task view' : 'Six-task view');
  set(summary, `D${start - 2}`, scopeIndex ? 'Task28 out' : 'Includes development-used task28');
  range(summary, `B${start - 2}:L${start - 2}`).format.font.bold = true;
  range(summary, `B${start - 1}:L${start - 1}`).values = [metricHeaders];
  header(summary, `B${start - 1}:L${start - 1}`);
  for (let si = 0; si < 3; si++) for (let k = 0; k < 3; k++) {
    const r = start + si * 3 + k;
    set(summary, `B${r}`, strategies[si]); set(summary, `C${r}`, k);
    const cr = criteria(r, 'CaseData', Boolean(scopeIndex));
    formula(summary, `D${r}`, `=COUNTIFS(${cr})`);
    for (const [col, source] of [['E', 'F'], ['F', 'G'], ['G', 'H'], ['J', 'J'], ['L', 'M']]) {
      formula(summary, `${col}${r}`, `=SUMIFS('CaseData'!$${source}$2:$${source}$55,${cr})`);
    }
    formula(summary, `H${r}`, `=SUMIFS('CaseData'!$F$2:$F$55,${cr},'CaseData'!$I$2:$I$55,1)/D${r}`);
    formula(summary, `I${r}`, `=H${r}+G${r}/D${r}`);
    formula(summary, `K${r}`, `=SUMIFS('CaseData'!$J$2:$J$55,${cr},'CaseData'!$F$2:$F$55,1)`);
  }
  range(summary, `C${start}:L${start + 8}`).format.horizontalAlignment = 'right';
  range(summary, `H${start}:I${start + 8}`).setNumberFormat('0.0%');
}
set(summary, 'B18', 'One FullEscalate k=2 completion is unknown. Lower/upper retain that task in the denominator.');
set(summary, 'B19', 'The range reflects missing completion only, not a confidence interval.');
set(summary, 'B35', 'Seven task24 native successes omit retrieved emails. Quality flags are not score overrides.');
set(summary, 'B36', 'Both observed email-format and source-grounding defects remain native failures.');

for (let scopeIndex = 0; scopeIndex < 2; scopeIndex++) {
  const start = scopeIndex ? 60 : 44;
  set(summary, `B${start - 2}`, scopeIndex ? 'Component costs, excluding task28 (all k combined)' : 'Component costs, all six tasks (all k combined)');
  range(summary, `B${start - 2}:L${start - 2}`).format.font.bold = true;
  range(summary, `B${start - 1}:K${start - 1}`).values = [['Strategy', 'Component', 'Runs', 'Requests', 'Known input', 'Known output', 'Known credits USD', 'Unknown cost cells', 'Complete credits USD', 'Rate estimate USD']];
  header(summary, `B${start - 1}:K${start - 1}`);
  range(summary, `C${start - 1}:C${start + 8}`).format.columnWidth = 12;
  for (let si = 0; si < 3; si++) for (let ci = 0; ci < 3; ci++) {
    const r = start + si * 3 + ci;
    set(summary, `B${r}`, strategies[si]); set(summary, `C${r}`, ['agent', 'policy', 'reviewer'][ci]);
    const cr = `'CostData'!$B$2:$B$163,$B${r},'CostData'!$E$2:$E$163,$C${r}` + (scopeIndex ? `,'CostData'!$D$2:$D$163,0` : '');
    formula(summary, `D${r}`, `=COUNTIFS(${cr})`);
    for (const [dest, source] of [['E', 'F'], ['F', 'G'], ['G', 'H'], ['H', 'I'], ['I', 'J'], ['K', 'L']]) {
      formula(summary, `${dest}${r}`, `=SUMIFS('CostData'!$${source}$2:$${source}$163,${cr})`);
    }
    formula(summary, `J${r}`, `=IF(I${r}>0,"unknown",H${r})`);
  }
  range(summary, `D${start}:K${start + 8}`).format.horizontalAlignment = 'right';
  for (const col of ['H', 'J', 'K']) range(summary, `${col}${start}:${col}${start + 8}`).setNumberFormat('0.00000000');
}
set(summary, 'B54', 'Known credits omit unresolved timeout cost. Rate estimates and reservations are not invoices.');
set(summary, 'B55', 'Separate diagnostic reviewer replay: USD0.00023145, excluded from the tables above.');
set(summary, 'B70', 'Normal-only exploratory evidence. A confirmed unauthorized-auto-approval example is still missing.');

for (let scopeIndex = 0; scopeIndex < 2; scopeIndex++) {
  const helper = scopeIndex ? 82 : 75;
  const source = scopeIndex ? 25 : 8;
  range(summary, `B${helper}:F${helper}`).values = [['k', ...names, '100% scale reference']];
  header(summary, `B${helper}:F${helper}`);
  for (let k = 0; k < 3; k++) {
    set(summary, `B${helper + k + 1}`, String(k));
    range(summary, `C${helper + k + 1}:E${helper + k + 1}`).formulas = [[`=H${source + k}`, `=H${source + 3 + k}`, `=H${source + 6 + k}`]];
    set(summary, `F${helper + k + 1}`, 1);
  }
  range(summary, `C${helper + 1}:E${helper + 3}`).setNumberFormat('0.0%');
  const chart = summary.charts.add('line', range(summary, `B${helper}:F${helper + 3}`));
  chart.title = scopeIndex ? 'Exploratory TCR, excluding task28' : 'Exploratory TCR, all six tasks';
  chart.titleTextStyle.fontSize = 12; chart.titleTextStyle.typeface = 'Arial';
  chart.legend = { position: 'top', textStyle: { typeface: 'Arial', fontSize: 10 } };
  chart.xAxis = { axisType: 'textAxis', textStyle: { typeface: 'Arial', fontSize: 10 } };
  chart.yAxis = { numberFormatCode: '0%', numberFormatSourceLinked: false, textStyle: { typeface: 'Arial', fontSize: 10 } };
  chart.xAxis.title.text = 'Review budget k'; chart.yAxis.title.text = 'Native-score-based TCR';
  chart.setPosition(scopeIndex ? 'N26' : 'N6', scopeIndex ? 'Y42' : 'Y22');
  chart.series.items.forEach((series, i) => { const color = palette[i] || '#C8D1DD'; series.fill = color; series.line = { fill: color, style: i === 3 ? 'dashed' : 'solid', width: i === 3 ? 1 : 2 }; });
}
set(summary, 'N23', 'FullEscalate k=2 includes one unknown completion; see the bounds in the table.');
set(summary, 'N43', 'Lower-bound lines. No attack condition or independent human safety validation.');

// Independent equality checks against the Decimal-based analysis and an input-change test.
wb.recalculate();
for (const g of data.metrics) {
  const r = (g.scope === scopes[0] ? 8 : 25) + strategies.indexOf(g.strategy) * 3 + g.k;
  for (const [col, expected] of [['D', g.planned_denominator], ['E', g.native_successes], ['F', g.native_false], ['G', g.native_unknown],
      ['H', g.exploratory_tcr_lower], ['I', g.unknown_completion_upper], ['J', g.hitl_all], ['K', g.hitl_native_successful], ['L', g.quality_flagged_cases]]) {
    assert.ok(Math.abs(range(summary, `${col}${r}`).values[0][0] - expected) < 1e-10, `${col}${r}`);
  }
}
for (const g of data.component_costs) {
  const r = (g.scope === scopes[0] ? 44 : 60) + strategies.indexOf(g.strategy) * 3 + ['agent', 'policy', 'reviewer'].indexOf(g.component);
  assert.ok(Math.abs(range(summary, `H${r}`).values[0][0] - Number(g.known_reported_usd_credits_subtotal)) < 1e-10);
  assert.equal(range(summary, `I${r}`).values[0][0], g.unknown_cost_cases);
  if (g.complete_reported_usd_credits === null) assert.equal(range(summary, `J${r}`).values[0][0], 'unknown');
}
const saved = { success: range(cases, 'F2').values[0][0], false: range(cases, 'G2').values[0][0], utility: range(cases, 'E2').values[0][0] };
const before = range(summary, 'H8').values[0][0];
set(cases, 'F2', 1); set(cases, 'G2', 0); set(cases, 'E2', 'true'); wb.recalculate();
assert.ok(Math.abs(range(summary, 'H8').values[0][0] - before - 1 / 6) < 1e-10);
set(cases, 'F2', saved.success); set(cases, 'G2', saved.false); set(cases, 'E2', saved.utility);
const oldUnknown = range(costs, 'J2').values[0][0]; set(costs, 'J2', 1); wb.recalculate();
assert.equal(range(summary, 'J44').values[0][0], 'unknown');
set(costs, 'J2', oldUnknown); wb.recalculate();
assert.ok(Math.abs(range(summary, 'H8').values[0][0] - before) < 1e-10);
const errors = await wb.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!', options: { useRegex: true, maxResults: 30 }, summary: 'formula errors' });
await fs.writeFile(path.join(runtime, 'formula_scan.ndjson'), errors.ndjson);
const inspection = await wb.inspect({ kind: 'table', range: 'Results!B7:L16', include: 'values,formulas', tableMaxRows: 10, tableMaxCols: 11, maxChars: 5000 });
await fs.writeFile(path.join(runtime, 'summary_inspection.ndjson'), inspection.ndjson);
for (const [sheetName, area, name] of [['Results', 'A1:L36', 'results_preview'], ['Results', 'A40:L70', 'component_summary_preview'], ['CaseData', 'A1:M12', 'cases_preview'], ['CostData', 'A1:L12', 'costs_preview'], ['Results', 'N5:Y24', 'native_chart_preview']]) {
  if (name === 'cases_preview' || name === 'costs_preview') {
    try { await fs.access(path.join(runtime, `${name}.png`)); continue; } catch { /* First render. */ }
  }
  const blob = await wb.render({ sheetName, range: area, scale: 1.5, format: 'png' });
  await fs.writeFile(path.join(runtime, `${name}.png`), new Uint8Array(await blob.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(out, 'experiment_results.xlsx'));

// Scientific figures use explicit coordinates and source counts, with a visible
// unknown-outcome interval. SVG and PNG are static report assets, not workbook inputs.
const esc = s => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const txt = (x, y, s, size = 15, fill = '#34445A', anchor = 'start', weight = 'normal') => `<text x="${x}" y="${y}" font-size="${size}" fill="${fill}" text-anchor="${anchor}" font-weight="${weight}">${esc(s)}</text>`;
const line = (x1, y1, x2, y2, color = '#DDE4EB', width = 1, dash = '') => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="${width}" ${dash ? `stroke-dasharray="${dash}"` : ''}/>`;
const rect = (x, y, w, h, fill) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}"/>`;
async function figure(name, body, width, height) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="white"/><g font-family="Arial,Helvetica,sans-serif">${body}</g></svg>`;
  await fs.writeFile(path.join(out, `${name}.svg`), svg);
  await sharp(Buffer.from(svg)).resize(width * 2, height * 2).png().toFile(path.join(out, `${name}.png`));
}
let body = txt(35, 35, 'Exploratory TCR@k under the current scope audit', 23, '#20344E', 'start', 'bold');
body += txt(35, 61, 'Native utility retained. Normal condition, one repetition. Not a final independently accepted safety score.', 14);
for (let si = 0; si < 3; si++) body += line(45 + si * 350, 91, 75 + si * 350, 91, palette[si], 3) + txt(83 + si * 350, 96, names[si], 15);
for (let scopeIndex = 0; scopeIndex < 2; scopeIndex++) {
  const x0 = scopeIndex ? 700 : 105, y0 = 405, plotW = 430, plotH = 245;
  body += txt(x0 + 215, 137, scopeIndex ? 'Five tasks, excluding development-used task28' : 'Six exploratory tasks, including development-used task28', 16, '#20344E', 'middle', 'bold');
  for (let pct = 0; pct <= 100; pct += 20) body += line(x0, y0 - pct / 100 * plotH, x0 + plotW, y0 - pct / 100 * plotH) + txt(x0 - 12, y0 - pct / 100 * plotH + 5, `${pct}%`, 13, '#526275', 'end');
  for (let k = 0; k < 3; k++) body += txt(x0 + k * plotW / 2, y0 + 27, String(k), 15, '#34445A', 'middle');
  body += txt(x0 + 215, 462, 'Review budget k', 15, '#34445A', 'middle');
  for (let si = 0; si < 3; si++) {
    const gs = data.metrics.filter(g => g.scope === scopes[scopeIndex] && g.strategy === strategies[si]);
    const points = gs.map(g => [x0 + g.k * plotW / 2, y0 - g.exploratory_tcr_lower * plotH]);
    body += `<polyline points="${points.map(p => p.join(',')).join(' ')}" fill="none" stroke="${palette[si]}" stroke-width="3"/>`;
    gs.forEach((g, i) => {
      const [x, y] = points[i];
      body += `<circle cx="${x}" cy="${y}" r="5" fill="${palette[si]}" stroke="white" stroke-width="1.5"/>`;
      if (g.native_unknown) {
        const top = y0 - g.unknown_completion_upper * plotH;
        body += line(x, top, x, y, palette[si], 2.5, '5 4') + line(x - 7, top, x + 7, top, palette[si], 2);
        body += txt(x - 8, top - 9, `${g.native_successes}/${g.planned_denominator} + 1 unknown`, 12, palette[si], 'end');
      }
    });
  }
}
body += txt(35, 507, 'Dashed vertical segment: one unresolved completion, not a confidence interval. The planned denominator is retained.', 14);
body += txt(35, 532, 'Seven task24 native successes have an answer-quality omission. The audit does not silently revise those scores.', 14);
await figure('tcr_exploratory', body, 1200, 555);

body = txt(35, 35, 'HITL load: actual reviewer invocations', 23, '#20344E', 'start', 'bold');
body += txt(35, 61, 'All six exploratory tasks. Each group pools six task invocations at the stated k.', 14);
const y0 = 385, plotH = 250, left = 100, xs = [250, 590, 930];
for (let n = 0; n <= 10; n += 2) body += line(left, y0 - n / 10 * plotH, 1120, y0 - n / 10 * plotH) + txt(82, y0 - n / 10 * plotH + 5, String(n), 13, '#526275', 'end');
for (let si = 0; si < 3; si++) body += rect(45 + si * 350, 84, 16, 16, palette[si]) + txt(70 + si * 350, 98, names[si], 15);
for (let k = 0; k < 3; k++) for (let si = 0; si < 3; si++) {
  const g = data.metrics.find(g => g.scope === scopes[0] && g.strategy === strategies[si] && g.k === k);
  const x = xs[k] + (si - 1) * 75 - 28;
  body += rect(x, y0 - g.hitl_all / 10 * plotH, 55, g.hitl_all / 10 * plotH, palette[si]);
  body += txt(x + 27.5, y0 - g.hitl_all / 10 * plotH - 8, `${g.hitl_all}`, 14, palette[si], 'middle', 'bold');
  body += txt(x + 27.5, y0 + 27, `${g.hitl_native_successful}`, 14, palette[si], 'middle');
}
for (let k = 0; k < 3; k++) body += txt(xs[k], 449, `k = ${k}`, 16, '#20344E', 'middle', 'bold');
body += txt(35, 489, 'Bars: reviews across all recorded tasks. Numbers below the baseline: reviews on native-successful tasks.', 14);
body += txt(35, 514, 'Excluding task28, FullEscalate and Candidate both use 0 / 5 / 9 reviews at k = 0 / 1 / 2.', 14);
await figure('hitl_load', body, 1200, 540);

body = txt(35, 35, 'Component costs: known response-reported credits', 23, '#20344E', 'start', 'bold');
body += txt(35, 61, 'All six tasks and k = 0, 1, 2 combined. Eighteen task invocations per strategy.', 14);
const colors = ['#526E91', '#087F72'];
body += rect(45, 86, 16, 16, colors[0]) + txt(71, 100, 'Agent', 15) + rect(225, 86, 16, 16, colors[1]) + txt(251, 100, 'Reviewer', 15);
const vals = strategies.map(s => data.component_costs.filter(g => g.scope === scopes[0] && g.strategy === s));
const maxCost = 0.025, py0 = 390, ph = 250;
for (let v = 0; v <= 0.02501; v += 0.005) body += line(110, py0 - v / maxCost * ph, 1120, py0 - v / maxCost * ph) + txt(95, py0 - v / maxCost * ph + 5, `$${v.toFixed(3)}`, 13, '#526275', 'end');
vals.forEach((rows, si) => {
  const x = [270, 610, 950][si]; let stacked = 0;
  ['agent', 'reviewer'].forEach((c, ci) => { const v = Number(rows.find(g => g.component === c).known_reported_usd_credits_subtotal); body += rect(x - 60, py0 - (stacked + v) / maxCost * ph, 120, v / maxCost * ph, colors[ci]); stacked += v; });
  body += txt(x, py0 - stacked / maxCost * ph - 12, `$${stacked.toFixed(6)}${si === 1 ? '*' : ''}`, 15, '#20344E', 'middle', 'bold');
  body += txt(x, 426, names[si], 16, '#20344E', 'middle');
});
body += txt(35, 469, '* FullEscalate excludes an unresolved timeout charge. Its displayed subtotal is not a complete bill.', 14);
body += txt(35, 494, 'Policy API cost is zero for all three strategies. The separate diagnostic replay is excluded.', 14);
body += txt(35, 519, `Known benchmark subtotal: $${data.known_benchmark_reported_usd_credits_subtotal}. Program reservations are not service invoices.`, 14);
await figure('component_costs', body, 1200, 545);
await fs.writeFile(path.join(runtime, 'workbook_verification.json'), JSON.stringify({
  worksheets: 3, native_charts: 2, source_cases: 54, source_component_rows: 162,
  metric_groups_checked: 18, component_groups_checked: 18, input_change_test: 'passed and restored',
  unknown_cost_test: 'passed and restored', artifact_recalculated: true,
  native_excel_application_tested: false, new_model_requests: 0, exported: 'results/analysis_20261019/experiment_results.xlsx'
}, null, 2));
console.log(JSON.stringify({ workbook: 'results/analysis_20261019/experiment_results.xlsx', figures: 3, native_charts: 2, verification: 'metric equality and input-change checks passed' }));
