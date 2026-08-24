import { redirect } from "next/navigation";

import { auth } from "@/auth";
import ChatWindow from "@/components/chat-window";
import DocumentsSidebar from "@/components/documents-sidebar";
import SignOutButton from "@/components/sign-out-button";
import { listDocuments, type DocumentInfo } from "@/lib/backend";

export const dynamic = "force-dynamic";

export default async function ChatPage() {
  const session = await auth();
  if (!session?.user?.id) {
    redirect("/login");
  }

  const username = session.user.id;

  let documents: DocumentInfo[] = [];
  try {
    documents = await listDocuments(username);
  } catch (error) {
    // Backend down or starting up — the sidebar still renders and can retry.
    console.error("Initial document listing failed:", error);
  }

  return (
    <main className="flex h-screen">
      <DocumentsSidebar initialDocuments={documents} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-zinc-800 px-6 py-3">
          <div>
            <p className="text-sm font-semibold text-zinc-100">Adaptive RAG</p>
            <p className="text-xs text-zinc-500">
              Signed in as {username} · queries search your documents first
            </p>
          </div>
          <SignOutButton username={username} />
        </header>
        <ChatWindow />
      </div>
    </main>
  );
}
