import { MongoClient, type Db } from "mongodb";

const uri = process.env.MONGODB_URI ?? "mongodb://localhost:27017";
const dbName = process.env.MONGODB_DB ?? "vlp-local";

declare global {
  var _mongoClientPromise: Promise<MongoClient> | undefined;
}

export async function getDb(): Promise<Db> {
  if (!global._mongoClientPromise) {
    global._mongoClientPromise = new MongoClient(uri).connect();
  }
  const client = await global._mongoClientPromise;
  return client.db(dbName);
}
