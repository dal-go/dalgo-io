import copy
import json
import unittest
from pathlib import Path

from capability_matrix import CAPABILITIES, LABELS, RUNTIMES, STATUSES, capability_cell, evidence_url, load_inventory, ordered_adapters, render_matrix, unique_object, validate_inventory

PATH = Path(__file__).resolve().parents[1] / 'content/site/adapter-status.json'


class CapabilityMatrix(unittest.TestCase):
    def setUp(self):
        self.inventory = load_inventory(PATH)

    def test_original_inventory_and_twenty_distinct_targets_are_preserved(self):
        old = 'algolia appwrite azure-table bigquery clickhouse cloudflare-d1 cosmosdb couchbase couchdb databricks datastore duckdb dynamodb elasticsearch filesystem firebase-rtdb firestore http indexeddb influxdb ingitdb json-files kusto libsql logs memory mongodb mysql namecheap neo4j neptune opensearch openvaultdb oracle pinecone pocketbase postgresql postgrest qdrant rds-data redis redshift snowflake solr spanner sqlite sqlserver timestream typesense'.split()
        ids = {row['id'] for row in self.inventory['adapters']}
        self.assertTrue(set(old) <= ids)
        targets = {item['id']: item['adapterId'] for item in self.inventory['capabilityMatrix']['requestedProviders']}
        self.assertEqual(len(targets), 20)
        self.assertEqual(targets['supabase'], 'supabase')
        self.assertEqual(targets['turso'], 'turso')
        self.assertEqual(targets['redis-resp'], 'redis')
        self.assertNotEqual(targets['cloudflare-kv'], 'cloudflare-d1')
        self.assertNotEqual(targets['upstash-rest'], 'redis')
        self.assertEqual([row['id'] for row in ordered_adapters(self.inventory)][-4:], ['elasticsearch', 'opensearch', 'typesense', 'meilisearch'])

    def test_unknowns_do_not_inherit_legacy_readonly_or_related_hosted_support(self):
        inventory = copy.deepcopy(self.inventory)
        # An explicit KV audit must not become an inferred default for unaudited cells.
        inventory['capabilityMatrix']['overrides'].pop('cloudflare-kv', None)
        for adapter in ('mysql', 'supabase', 'turso', 'cloudflare-kv'):
            for runtime in RUNTIMES:
                for capability in CAPABILITIES:
                    self.assertEqual(capability_cell(inventory, adapter, runtime, capability)['status'], 'UNVERIFIED')
        self.assertEqual(capability_cell(self.inventory, 'postgrest', 'go', 'read')['status'], 'SUPPORTED')
        self.assertEqual(capability_cell(self.inventory, 'duckdb', 'go', 'write')['status'], 'UNVERIFIED')

    def test_public_native_source_keeps_runtime_and_publication_evidence_separate(self):
        matrix = self.inventory['capabilityMatrix']
        adapters = {row['id']: row for row in self.inventory['adapters']}
        for adapter in ('mongodb', 'redis', 'duckdb'):
            for capability in ('read', 'query'):
                cell = capability_cell(self.inventory, adapter, 'ts-node', capability)
                self.assertEqual(cell['status'], 'PARTIAL')
                self.assertEqual(cell['verification'], 'source-only')
                self.assertTrue(all('/d5abba45363b92ac875ad76a9e414dba07e008a5/' in matrix['evidence'][ref]['url'] for ref in cell['evidence']))
                self.assertFalse(any(matrix['evidence'][ref]['kind'] == 'execution' for ref in cell['evidence']))
            typescript = adapters[adapter]['typescript']
            self.assertEqual(typescript['publication'], 'not-verified')
            self.assertTrue(any('Public unmerged source branch' in limit for limit in typescript['limits']))
            for runtime in ('ts-browser', 'ts-node'):
                for capability in ('write', 'transactions', 'schema'):
                    self.assertEqual(capability_cell(self.inventory, adapter, runtime, capability)['status'], 'NOT_IMPLEMENTED')
        for adapter in ('mongodb', 'redis'):
            for capability in ('read', 'query'):
                cell = capability_cell(self.inventory, adapter, 'ts-browser', capability)
                self.assertEqual(cell['status'], 'UNVERIFIED')
                self.assertIn('Public branch source is present', cell['reason']['en'])
                self.assertEqual(cell['verification'], 'source-only')
        browser = capability_cell(self.inventory, 'duckdb', 'ts-browser', 'query')
        self.assertEqual(browser['status'], 'PARTIAL')
        self.assertIn('Local standalone Chromium/WASM', browser['reason']['en'])
        self.assertEqual(browser['verification'], 'source-only')
        redis = capability_cell(self.inventory, 'redis', 'go', 'query')
        self.assertIn('literal-prefix SCAN', redis['reason']['en'])
        self.assertNotIn('No SCAN', redis['reason']['en'])
        self.assertEqual(capability_cell(self.inventory, 'mongodb', 'go', 'transactions')['status'], 'NOT_IMPLEMENTED')

        # Native source additions do not imply execution in another runtime or a release.
        for adapter, runtime in (('cloudflare-kv', 'go'), ('cosmosdb', 'ts-node')):
            for capability in ('read', 'query'):
                cell = capability_cell(self.inventory, adapter, runtime, capability)
                self.assertEqual(cell['status'], 'PARTIAL')
                self.assertEqual(cell['verification'], 'source-only')
                self.assertFalse(any(matrix['evidence'][ref]['kind'] == 'execution' for ref in cell['evidence']))
            language = 'go' if runtime == 'go' else 'typescript'
            self.assertEqual(adapters[adapter][language]['publication'], 'not-verified')
            for capability in ('read', 'query'):
                self.assertEqual(capability_cell(self.inventory, adapter, 'ts-browser', capability)['status'], 'UNVERIFIED')
        self.assertIn('cosmos-ts-native-source', capability_cell(self.inventory, 'cosmosdb', 'ts-node', 'read')['evidence'])
        self.assertEqual(matrix['evidence']['cosmos-ts-native-test']['runtimes'], ['ts-node'])
        self.assertEqual(capability_cell(self.inventory, 'cloudflare-kv', 'go', 'write')['status'], 'NOT_IMPLEMENTED')
        self.assertEqual(capability_cell(self.inventory, 'cloudflare-kv', 'go', 'transactions')['status'], 'UNSUPPORTED')

    def test_snowflake_native_source_does_not_imply_browser_execution_or_release(self):
        matrix = self.inventory['capabilityMatrix']
        row = next(row for row in self.inventory['adapters'] if row['id'] == 'snowflake')
        pins = {
            'go': '726e8a6a5014896749579dd2769a93c65f4f5669',
            'ts-node': '21167ea040d487d442cdcb6534092b7d6ed446a9',
        }
        for runtime, pin in pins.items():
            for capability in ('read', 'query'):
                cell = capability_cell(self.inventory, 'snowflake', runtime, capability)
                self.assertEqual(cell['status'], 'PARTIAL')
                self.assertEqual(cell['verification'], 'source-only')
                for reference in cell['evidence']:
                    evidence = matrix['evidence'][reference]
                    self.assertIn('/' + pin + '/', evidence['url'])
                    self.assertNotEqual(evidence['kind'], 'execution')
            language = 'go' if runtime == 'go' else 'typescript'
            self.assertEqual(row[language]['status'], 'source-only')
            self.assertEqual(row[language]['publication'], 'not-verified')
        self.assertEqual(row['typescript']['package'], '@dal-go/dalgo2snowflake')
        self.assertTrue(row['typescript']['manifest_private'])
        for capability in ('read', 'query'):
            browser = capability_cell(self.inventory, 'snowflake', 'ts-browser', capability)
            self.assertEqual(browser['status'], 'UNVERIFIED')
            self.assertEqual(browser['verification'], 'source-only')
            self.assertIn('pre-abort only', browser['reason']['en'])
        for runtime in RUNTIMES:
            for capability in ('write', 'transactions', 'schema'):
                self.assertEqual(capability_cell(self.inventory, 'snowflake', runtime, capability)['status'], 'NOT_IMPLEMENTED')
        self.assertEqual(matrix['evidence']['snowflake-ts-packed-fixture']['kind'], 'test-source')
        self.assertEqual(matrix['evidence']['snowflake-ts-packed-fixture']['runtimes'], ['ts-node'])
        # A Node protocol fixture must not qualify the browser, even while that
        # browser capability remains explicitly unverified.
        candidate = copy.deepcopy(self.inventory)
        candidate['capabilityMatrix']['overrides']['snowflake']['ts-browser']['read']['evidence'] = ['snowflake-ts-packed-fixture']
        with self.assertRaises(ValueError):
            validate_inventory(candidate)

    def test_schema_is_discovery_and_bigquery_execution_is_synthetic_only(self):
        schema = capability_cell(self.inventory, 'postgrest', 'go', 'schema')
        self.assertEqual(schema['status'], 'PARTIAL')
        self.assertIn('OpenAPI', schema['reason']['en'])
        query = capability_cell(self.inventory, 'bigquery', 'ts-node', 'query')
        self.assertEqual(query['status'], 'PARTIAL')
        self.assertIn('synthetic', query['reason']['en'])
        self.assertIn('unverified', query['reason']['en'])

    def test_status_and_localized_reason_are_closed_contracts(self):
        for status in ('YES', 'readonly', '', None):
            candidate = copy.deepcopy(self.inventory)
            candidate['capabilityMatrix']['overrides']['postgrest']['go']['read']['status'] = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                validate_inventory(candidate)
        for status in ('UNSUPPORTED', 'NOT_IMPLEMENTED', 'PARTIAL'):
            candidate = copy.deepcopy(self.inventory)
            cell = candidate['capabilityMatrix']['overrides']['postgrest']['go']['read']
            cell['status'] = status
            cell['reason']['en'] = '   '
            with self.subTest(status=status), self.assertRaises(ValueError):
                validate_inventory(candidate)

    def test_positive_capabilities_require_source_and_applicable_tests_or_docs(self):
        candidate = copy.deepcopy(self.inventory)
        cell = candidate['capabilityMatrix']['overrides']['postgrest']['go']['read']
        cell['evidence'] = ['postgrest-go-source']
        with self.assertRaises(ValueError):
            validate_inventory(candidate)
        cell['evidence'] = ['bq-node-source', 'bq-node-test']
        with self.assertRaises(ValueError):
            validate_inventory(candidate)

    def test_even_unverified_overrides_cannot_have_dangling_or_fake_execution_evidence(self):
        for references, verification in ((['missing'], 'source-only'), ([], 'executed'), ([], 'invented')):
            candidate = copy.deepcopy(self.inventory)
            cell = candidate['capabilityMatrix']['overrides']['duckdb']['go']['write']
            cell['evidence'] = references
            cell['verification'] = verification
            with self.subTest(references=references, verification=verification), self.assertRaises(ValueError):
                validate_inventory(candidate)

    def test_unknown_ids_and_duplicate_json_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"a":1,"a":2}', object_pairs_hook=unique_object)
        for axis in ('runtime', 'capability', 'adapter'):
            candidate = copy.deepcopy(self.inventory)
            overrides = candidate['capabilityMatrix']['overrides']
            if axis == 'runtime':
                overrides['postgrest']['browser-and-node'] = {}
            elif axis == 'capability':
                overrides['postgrest']['go']['ddl'] = {'status': 'UNVERIFIED'}
            else:
                overrides['unknown'] = {}
            with self.subTest(axis=axis), self.assertRaises(ValueError):
                validate_inventory(candidate)

    def test_bogus_twentieth_provider_cannot_replace_an_actual_requested_provider(self):
        candidate = copy.deepcopy(self.inventory)
        matrix = candidate['capabilityMatrix']
        for item in matrix['requestedProviders']:
            if item['id'] == 'athena':
                item.update(id='bogus', adapterId='bigquery')
        matrix['priority'] = ['bogus' if item == 'athena' else item for item in matrix['priority']]
        with self.assertRaises(ValueError):
            validate_inventory(candidate)

    def test_evidence_urls_are_safe_and_commit_pinned(self):
        for url in ('http://github.com/a/b/blob/' + 'a' * 40 + '/x', 'https://user@github.com/a/b/blob/' + 'a' * 40 + '/x', 'https://github.com.evil/a/b/blob/' + 'a' * 40 + '/x', 'https://github.com/a/b/blob/main/x', 'https://github.com/a/b/blob/' + 'a' * 40 + '/x%GG', 'https://github.com/a/b/blob/' + 'a' * 40 + '/%2e%2e/main/x', 'https://github.com/a/b/blob/' + 'a' * 40 + '/x%0a'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                evidence_url(url)

    def test_native_rows_are_independent_localized_and_have_real_table_headers(self):
        for locale in LABELS:
            page = render_matrix(self.inventory, locale)
            count = len(self.inventory['adapters'])
            self.assertEqual(page.count('<details class="cap-adapter"'), count)
            self.assertEqual(page.count('<caption id='), count)
            self.assertEqual(page.count('class="cap-table-scroll" role="region" tabindex="0"'), count)
            self.assertIn(LABELS[locale]['scroll'], page)
            self.assertIn('<span class="cap-adapter-name">Redis RESP</span>', page)
            self.assertIn('<span class="cap-adapter-name">InfluxDB Cloud</span>', page)
            self.assertEqual(page.count('scope="row"'), count * len(CAPABILITIES))
            self.assertNotIn('<script', page)
            self.assertNotIn('<details name=', page)
            for status in STATUSES:
                self.assertIn(LABELS[locale][status], page)
            self.assertIn(LABELS[locale]['ts-browser'], page)
            self.assertIn(LABELS[locale]['ts-node'], page)
            self.assertIn(LABELS[locale]['schema'], page)
            self.assertIn(LABELS[locale]['publication'], page)


if __name__ == '__main__':
    unittest.main()
