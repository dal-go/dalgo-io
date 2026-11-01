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
        for adapter in ('mysql', 'supabase', 'turso', 'cloudflare-kv'):
            for runtime in RUNTIMES:
                for capability in CAPABILITIES:
                    self.assertEqual(capability_cell(self.inventory, adapter, runtime, capability)['status'], 'UNVERIFIED')
        self.assertEqual(capability_cell(self.inventory, 'postgrest', 'go', 'read')['status'], 'SUPPORTED')
        self.assertEqual(capability_cell(self.inventory, 'duckdb', 'go', 'write')['status'], 'UNVERIFIED')

    def test_public_source_absence_is_not_an_intrinsic_browser_impossibility(self):
        for adapter in ('mongodb', 'redis', 'duckdb'):
            for runtime in ('ts-browser', 'ts-node'):
                cell = capability_cell(self.inventory, adapter, runtime, 'read')
                self.assertEqual(cell['status'], 'NOT_IMPLEMENTED')
                self.assertIn('unpublished', cell['reason']['en'])
                self.assertEqual(cell['verification'], 'source-only')
        self.assertEqual(capability_cell(self.inventory, 'mongodb', 'go', 'transactions')['status'], 'NOT_IMPLEMENTED')

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
