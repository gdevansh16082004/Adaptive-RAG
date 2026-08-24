import { MongoClient } from "mongodb";

/**
 * Shared MongoDB connection for authentication.
 *
 * Points at the same database the FastAPI backend uses so users live
 * alongside documents and chat history. The client promise is cached on the
 * global object to survive Next.js dev-mode module reloads.
 */

const uri = process.env.MONGODB_URI;

if (!uri) {
  throw new Error("MONGODB_URI is not set — add it to frontend/.env.local");
}

declare global {
  // eslint-disable-next-line no-var
  var _mongoClientPromise: Promise<MongoClient> | undefined;
}

const client = new MongoClient(uri);

const clientPromise: Promise<MongoClient> = (global._mongoClientPromise ??=
  client.connect());

export interface UserRecord {
  username: string;
  passwordHash: string;
  createdAt: Date;
}

export async function getUsersCollection() {
  const client = await clientPromise;
  const dbName = process.env.MONGODB_DB_NAME || "adaptive_rag";
  const collection = client.db(dbName).collection<UserRecord>("users");
  await collection.createIndex({ username: 1 }, { unique: true });
  return collection;
}

export async function findUser(username: string): Promise<UserRecord | null> {
  const users = await getUsersCollection();
  return users.findOne({ username });
}

export async function createUser(
  username: string,
  passwordHash: string,
): Promise<void> {
  const users = await getUsersCollection();
  try {
    await users.insertOne({
      username,
      passwordHash,
      createdAt: new Date(),
    });
  } catch (error) {
    if (
      typeof error === "object" &&
      error !== null &&
      (error as { code?: number }).code === 11000
    ) {
      throw new Error("Username is already taken.");
    }
    throw error;
  }
}
