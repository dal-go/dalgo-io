"""Validated, evidence-scoped capability data and native expandable matrix rows."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

RUNTIMES = ('go', 'ts-browser', 'ts-node')
CAPABILITIES = ('read', 'write', 'query', 'transactions', 'schema')
EXPECTED_TARGETS = {identifier: {'redis-resp': 'redis', 'influxdb-cloud': 'influxdb'}.get(identifier, identifier) for identifier in ('supabase', 'dynamodb', 'cosmosdb', 'couchdb', 'convex', 'cloudflare-kv', 'athena', 'snowflake', 'elasticsearch', 'opensearch', 'typesense', 'meilisearch', 'influxdb-cloud', 'turso', 'upstash-rest', 'clickhouse', 'duckdb', 'mongodb', 'redis-resp', 'firestore')}
STATUSES = ('SUPPORTED', 'PARTIAL', 'NOT_IMPLEMENTED', 'UNSUPPORTED', 'UNVERIFIED')
LABELS = {
    'en': {'SUPPORTED': 'Supported', 'PARTIAL': 'Partial', 'NOT_IMPLEMENTED': 'Not implemented', 'UNSUPPORTED': 'Unsupported', 'UNVERIFIED': 'Unverified', 'go': 'Go', 'ts-browser': 'TypeScript · browser', 'ts-node': 'TypeScript · Node.js', 'read': 'Read', 'write': 'Write', 'query': 'Queries', 'transactions': 'Transactions', 'schema': 'Schema discovery', 'adapter': 'Adapter', 'capability': 'Capability', 'evidence': 'Evidence', 'source': 'Source audit', 'execution': 'Executed checks', 'unverified': 'Execution unverified', 'publication': 'Package publication unverified', 'limits': 'Scope and limits', 'expand': 'Expand any rows to compare capabilities. Each row opens independently; keyboard: Tab, then Enter or Space.', 'note': 'Statuses describe the adapter surface at the cited public revisions, not unpublished working trees. Source review, executed checks, package publication and deployed integration are separate. Unknown cells stay unverified. Schema discovery means metadata, not schema mutation or DDL.', 'reason': 'This capability has not been audited for this runtime.', 'source-only': 'Source reviewed; execution unverified', 'executed': 'Executed fixture; see its scope', 'inventory': 'Earlier source inventory', 'requested': 'Requested provider', 'scroll': 'Scroll horizontally to compare all three runtimes. Keyboard: focus the table, then use Left and Right.', 'source-kind': 'Source', 'test-source-kind': 'Test source', 'execution-kind': 'Execution receipt', 'documentation-kind': 'Documentation', 'inventory-audit-kind': 'Inventory audit'},
    'ru': {'SUPPORTED': 'Поддерживается', 'PARTIAL': 'Частично', 'NOT_IMPLEMENTED': 'Не реализовано', 'UNSUPPORTED': 'Не поддерживается', 'UNVERIFIED': 'Не проверено', 'go': 'Go', 'ts-browser': 'TypeScript · браузер', 'ts-node': 'TypeScript · Node.js', 'read': 'Чтение', 'write': 'Запись', 'query': 'Запросы', 'transactions': 'Транзакции', 'schema': 'Метаданные схемы', 'adapter': 'Адаптер', 'capability': 'Возможность', 'evidence': 'Основания', 'source': 'Аудит исходников', 'execution': 'Проверки выполнения', 'unverified': 'Выполнение не проверено', 'publication': 'Публикация пакета не проверена', 'limits': 'Область и ограничения', 'expand': 'Откройте нужные строки для сравнения. Строки раскрываются независимо; клавиатура: Tab, затем Enter или пробел.', 'note': 'Статусы относятся к указанным публичным ревизиям адаптера, а не к неопубликованным рабочим копиям. Аудит кода, проверки выполнения, публикация пакетов и интеграция в приложение — отдельные факты. Неизвестные возможности остаются непроверенными. Метаданные схемы не означают изменение схемы или DDL.', 'reason': 'Возможность для этой среды ещё не проверялась.', 'source-only': 'Код проверен; выполнение не проверено', 'executed': 'Есть проверка фикстуры; см. её область', 'inventory': 'Предыдущий аудит исходников', 'requested': 'Запрошенный провайдер', 'scroll': 'Прокрутите таблицу по горизонтали для сравнения трёх сред. С клавиатуры: выберите таблицу и нажимайте стрелки влево и вправо.', 'source-kind': 'Исходник', 'test-source-kind': 'Исходник теста', 'execution-kind': 'Результат выполнения', 'documentation-kind': 'Документация', 'inventory-audit-kind': 'Аудит состава исходников'},
}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def evidence_url(url: str, kind: str = 'source') -> None:
    if not isinstance(url, str) or any(ord(character) < 33 for character in unquote(url)):
        raise ValueError('Invalid evidence URL')
    if re.search(r'%(?![0-9A-Fa-f]{2})', url):
        raise ValueError('Malformed evidence URL encoding')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'github.com' or parsed.username or parsed.password or parsed.query:
        raise ValueError('Evidence must use credential-free canonical HTTPS GitHub URLs')
    if kind == 'execution':
        valid = re.fullmatch(r'/[^/]+/[^/]+/actions/runs/[0-9]+(?:/job/[0-9]+)?', parsed.path)
    else:
        valid = re.fullmatch(r'/[^/]+/[^/]+/(?:blob|tree)/[0-9a-f]{40}(?:/[^\s]*)?', parsed.path)
    if any(part in ('.', '..') for part in unquote(parsed.path).split('/')) or '\\' in unquote(parsed.path):
        raise ValueError('Invalid evidence path')
    if not valid:
        raise ValueError('Source evidence must pin a full commit; execution evidence must name a run')


def validate_inventory(inventory: dict) -> dict:
    if inventory.get('schemaVersion') != 2 or not isinstance(inventory.get('adapters'), list):
        raise ValueError('Expected capability inventory schemaVersion 2')
    ids = set()
    for row in inventory['adapters']:
        identifier = row.get('id', '')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', identifier) or identifier in ids:
            raise ValueError('Adapter IDs must be unique stable slugs')
        ids.add(identifier)
        if not isinstance(row.get('name'), str) or not row['name'].strip():
            raise ValueError('Adapter requires a name')
        for language in ('go', 'typescript'):
            cell = row.get(language, {})
            for url in cell.get('sources', []) + cell.get('runtime', {}).get('sources', []):
                evidence_url(url)
    matrix = inventory.get('capabilityMatrix', {})
    if matrix.get('defaultStatus') != 'UNVERIFIED' or tuple(matrix.get('runtimes', [])) != RUNTIMES or tuple(matrix.get('capabilities', [])) != CAPABILITIES or tuple(matrix.get('statuses', [])) != STATUSES:
        raise ValueError('Unknown capability matrix contract')
    targets = matrix.get('requestedProviders', [])
    target_ids = [item.get('id') for item in targets]
    if len(targets) != 20 or len(set(target_ids)) != 20 or any(item.get('adapterId') not in ids for item in targets):
        raise ValueError('The full twenty requested providers must map explicitly to inventory rows')
    if {item['id']: item['adapterId'] for item in targets} != EXPECTED_TARGETS:
        raise ValueError('Requested provider IDs and mappings must match the full carried-forward plan')
    priority = matrix.get('priority', [])
    if len(priority) != 20 or set(priority) != set(target_ids):
        raise ValueError('Priority must include each requested provider exactly once')
    if priority[-4:] != ['elasticsearch', 'opensearch', 'typesense', 'meilisearch']:
        raise ValueError('The four search providers remain last')
    registry = matrix.get('evidence', {})
    for identifier, entry in registry.items():
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', identifier):
            raise ValueError('Evidence IDs must be slugs')
        if entry.get('kind') not in ('source', 'test-source', 'documentation', 'inventory-audit', 'execution'):
            raise ValueError('Unknown evidence kind')
        evidence_url(entry.get('url'), entry['kind'])
        if not entry.get('runtimes') or not set(entry['runtimes']) <= set(RUNTIMES):
            raise ValueError('Evidence must declare applicable runtimes')
    for adapter_id, runtime_overrides in matrix.get('overrides', {}).items():
        if adapter_id not in ids or not set(runtime_overrides) <= set(RUNTIMES):
            raise ValueError('Unknown adapter/runtime override')
        for runtime, entries in runtime_overrides.items():
            if not set(entries) <= set(CAPABILITIES):
                raise ValueError('Unknown capability override')
            for capability, cell in entries.items():
                if cell.get('status') not in STATUSES:
                    raise ValueError('Unknown capability status')
                references = cell.get('evidence', [])
                if not isinstance(references, list) or len(references) != len(set(references)):
                    raise ValueError('Evidence references must be a unique list')
                for reference in references:
                    if reference not in registry or runtime not in registry[reference]['runtimes']:
                        raise ValueError('Evidence does not apply to the claimed runtime')
                if cell.get('verification', 'source-only') not in ('source-only', 'executed'):
                    raise ValueError('Unknown verification level')
                kinds = {registry[reference]['kind'] for reference in references}
                if cell.get('verification') == 'executed' and 'execution' not in kinds:
                    raise ValueError('Executed claims require an execution receipt')
                if cell['status'] != 'UNVERIFIED':
                    reason = cell.get('reason', {})
                    if any(not isinstance(reason.get(locale), str) or not reason[locale].strip() for locale in LABELS):
                        raise ValueError('Audited statuses require EN/RU scope or reason')
                    if not references:
                        raise ValueError('Audited statuses require evidence references')
                    if cell['status'] in ('SUPPORTED', 'PARTIAL') and not (kinds & {'source'} and kinds & {'test-source', 'documentation'}):
                        raise ValueError('Positive capabilities require runtime-specific source and tests/docs')

    return inventory


def load_inventory(path: Path) -> dict:
    return validate_inventory(json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object))


def capability_cell(inventory: dict, adapter: str, runtime: str, capability: str) -> dict:
    return inventory['capabilityMatrix'].get('overrides', {}).get(adapter, {}).get(runtime, {}).get(capability, {'status': 'UNVERIFIED'})


def ordered_adapters(inventory: dict) -> list[dict]:
    matrix = inventory['capabilityMatrix']
    requested = {entry['id']: entry['adapterId'] for entry in matrix['requestedProviders']}
    first = [requested[item] for item in matrix['priority'][:-4]]
    last = [requested[item] for item in matrix['priority'][-4:]]
    middle = sorted(row['id'] for row in inventory['adapters'] if row['id'] not in first + last)
    by_id = {row['id']: row for row in inventory['adapters']}
    return [by_id[identifier] for identifier in first + middle + last]


def badge(status: str, locale: str) -> str:
    return f'<span class="cap-status cap-{status.lower().replace("_", "-")}">{LABELS[locale][status]}</span>'


def render_matrix(inventory: dict, locale: str) -> str:
    ui = LABELS[locale]
    escape = html.escape
    registry = inventory['capabilityMatrix']['evidence']
    requested = {item['adapterId']: item for item in inventory['capabilityMatrix']['requestedProviders']}
    rows = []
    for adapter in ordered_adapters(inventory):
        identifier = adapter['id']
        target = requested.get(identifier)
        name = escape(target['name'] if target else adapter['name'])
        summaries = []
        for runtime in RUNTIMES:
            statuses = [capability_cell(inventory, identifier, runtime, capability)['status'] for capability in CAPABILITIES]
            named = [f'{ui[capability]}: {ui[status]}' for capability, status in zip(CAPABILITIES, statuses) if status != 'UNVERIFIED']
            counts = '<br>'.join(named[:3]) if named else ui['UNVERIFIED']
            summaries.append(f'<span class="cap-overview"><span class="cap-runtime-name">{ui[runtime]}</span><span>{counts}</span></span>')
        body_rows = []
        for capability in CAPABILITIES:
            cells = []
            for runtime in RUNTIMES:
                cell = capability_cell(inventory, identifier, runtime, capability)
                reason = escape(cell.get('reason', {}).get(locale, ui['reason']))
                proof = ui['unverified'] if cell['status'] == 'UNVERIFIED' else ui[cell.get('verification', 'source-only')]
                evidence = []
                for reference in cell.get('evidence', []):
                    entry = registry[reference]
                    evidence.append(f'<a href="{escape(entry["url"], quote=True)}">{ui[entry["kind"] + "-kind"]}</a>')
                detail = f'<p lang="en" class="cap-detail">{escape(cell["detail"])}</p>' if locale == 'ru' and cell.get('detail') else ''
                cells.append(f'<td>{badge(cell["status"], locale)}<p class="cap-reason">{reason}</p>{detail}<small class="cap-proof">{proof}</small>' + (f'<p class="cap-evidence">{ui["evidence"]}: {" · ".join(evidence)}</p>' if evidence else '') + '</td>')
            body_rows.append(f'<tr><th scope="row">{ui[capability]}</th>{"".join(cells)}</tr>')
        notes = []
        for language in ('go', 'typescript'):
            sources = adapter.get(language, {}).get('sources', [])
            links = ' · '.join(f'<a href="{escape(url, quote=True)}">{ui["source-kind"]} {index + 1}</a>' for index, url in enumerate(sources))
            if links:
                notes.append(f'<p>{"Go" if language == "go" else "TypeScript"} · {ui["inventory"]}: {links}</p>')
        legacy_limits = []
        for language in ('go', 'typescript'):
            legacy = adapter.get(language, {})
            texts = list(legacy.get('limits', []))
            browser = legacy.get('runtime', {}).get('browser', {})
            texts += [text for text in (browser.get('conditions_and_limits'), browser.get('note')) if text]
            legacy_limits += [f'<li lang="en">{language}: {escape(text)}</li>' for text in texts]
        if legacy_limits:
            notes.append(f'<p>{ui["inventory"]} · {ui["limits"]}</p><ul>{"".join(legacy_limits)}</ul>')
        target = requested.get(identifier)
        if target:
            note = target.get('note', {}).get(locale)
            if note:
                notes.insert(0, f'<p class="cap-target-note">{escape(note)}</p>')
        heads = ''.join(f'<th scope="col">{ui[runtime]}</th>' for runtime in RUNTIMES)
        rows.append(f'<details class="cap-adapter" id="adapter-{identifier}"><summary><span class="cap-adapter-name">{name}</span>{"".join(summaries)}</summary><div class="cap-expanded"><p class="cap-scroll-hint" id="cap-scroll-{identifier}">{ui["scroll"]}</p><div class="cap-table-scroll" role="region" tabindex="0" aria-labelledby="cap-caption-{identifier}" aria-describedby="cap-scroll-{identifier}"><table class="cap-table"><caption id="cap-caption-{identifier}">{name} · {ui["capability"]}</caption><thead><tr><th scope="col">{ui["capability"]}</th>{heads}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div>{"".join(notes)}<p class="cap-publication">{ui["publication"]}</p></div></details>')
    legend = ' '.join(badge(status, locale) for status in STATUSES)
    return f'<header class="section-head"><h1>{"Adapters and capabilities" if locale == "en" else "Адаптеры и возможности"}</h1><p>{ui["note"]}</p></header><p class="cap-legend">{legend}</p><p id="matrix-help">{ui["expand"]}</p><p>{ui["source"]}: <time>{escape(inventory["auditDate"])}</time> · <a href="/adapters/status.json">JSON</a></p><div class="cap-matrix" aria-describedby="matrix-help">{"".join(rows)}</div>'
