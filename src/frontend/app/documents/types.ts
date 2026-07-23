export type DocumentRecord = {
  id: string;
  filename: string;
  title: string;
  description: string;
  tags: string[];
  contentType: string;
  size: number;
  sha256: string;
  createdAt: string;
  updatedAt: string;
  downloadUrl: string;
};

export type DocumentQuery = {
  q?: string;
  contentType?: string;
  tag?: string;
  ordering?: string;
};

export type DocumentMetadataUpdate = {
  filename?: string;
  title?: string;
  description?: string;
  tags?: string[];
};

export type DocumentErrorPayload = {
  code: string;
  message: string;
  fields?: Record<string, string>;
};

export type UploadResult =
  | { status: "uploaded"; document: DocumentRecord }
  | { status: "error"; error: DocumentErrorPayload };
