import { handleChat } from "./handler";

export function POST(request: Request) {
  return handleChat(
    request,
    () => new Promise((resolve) => setTimeout(resolve, 700)),
  );
}
