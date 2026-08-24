import { NextResponse } from "next/server";

import { BackendError, deleteDocument, requireUserId } from "@/lib/backend";

export const runtime = "nodejs";

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ docId: string }> },
) {
  let userId: string;
  try {
    userId = await requireUserId();
  } catch {
    return NextResponse.json({ error: "Not signed in." }, { status: 401 });
  }

  const { docId } = await params;
  if (!docId) {
    return NextResponse.json({ error: "Missing docId." }, { status: 400 });
  }

  try {
    await deleteDocument(userId, docId);
    return NextResponse.json({ deleted: true });
  } catch (error) {
    if (error instanceof BackendError) {
      return NextResponse.json(
        { error: error.message },
        { status: error.status },
      );
    }
    console.error("Delete proxy failed:", error);
    return NextResponse.json(
      { error: "Delete failed. Is the backend running?" },
      { status: 502 },
    );
  }
}
