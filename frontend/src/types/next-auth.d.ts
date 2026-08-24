import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    user: {
      /** The username, used as the document owner id downstream. */
      id: string;
    } & DefaultSession["user"];
  }
}
