import { collection } from '@dalgo/core';

// Load the selected adapter. IndexedDB runs in the browser.
const { IndexedDbDatabase } = await import('@dalgo/indexeddb');
const db = new IndexedDbDatabase({ name: 'dalgo-quickstart' });
const todos = collection<{ title: string; done: boolean }>('todos');

await db.runReadwriteTransaction(async (transaction) => {
  await transaction.set(todos.key('first'), { title: 'Try DALgo', done: false });
});

const page = await db.query(todos.query().where('done', '==', false).limit(20).build());
console.log(page);
await db.close();
