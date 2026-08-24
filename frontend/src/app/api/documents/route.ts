import { NextResponse } from "next/server";

import {
  BackendError,
  listDocuments,
  requireUserId,
  uploadDocument,
} from "@/lib/backend";

export const runtime = "nodejs";
export const maxDuration = 120;

export async function GET() {
  let userId: string;
  try {
    userId = await requireUserId();
  } catch {
    return NextResponse.json({ error: "Not signed in." }, { status: 401 });
  }

  try {
    const documents = await listDocuments(userId);
    return NextResponse.json({ documents });
  } catch (error) {
    if (error instanceof BackendError) {
      return NextResponse.json(
        { error: error.message },
        { status: error.status },
      );
    }
    console.error("Document listing failed:", error);
    return NextResponse.json(
      { error: "Could not reach the document store." },
      { status: 502 },
    );
  }
}

export async function POST(request: Request) {
  let userId: string;
  try {
    userId = await requireUserId();
  } catch {
    return NextResponse.json({ error: "Not signed in." }, { status: 401 });
  }

  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json(
      { error: "Expected multipart form data." },
      { status: 400 },
    );
  }

  const file = formData.get("file");
  const description = String(formData.get("description") ?? "").trim();

  if (!(file instanceof File)) {
    return NextResponse.json({ error: "No file provided." }, { status: 400 });
  }
  const extension = file.name.toLowerCase().split(".").pop();
  if (extension !== "pdf" && extension !== "txt") {
    return NextResponse.json(
      { error: "Only PDF and TXT files are supported." },
      { status: 400 },
    );
  }
  if (!description) {
    return NextResponse.json(
      { error: "Please describe the document before uploading." },
      { status: 400 },
    );
  }

  try {
    const document = await uploadDocument(userId, file, description);
    return NextResponse.json({ document }, { status: 201 });
  } catch (error) {
    if (error instanceof BackendError) {
      return NextResponse.json(
        { error: error.message },
        { status: error.status },
      );
    }
    console.error("Upload proxy failed:", error);
    return NextResponse.json(
      { error: "Upload failed. Is the backend running?" },
      { status: 502 },
    );
  }
}
