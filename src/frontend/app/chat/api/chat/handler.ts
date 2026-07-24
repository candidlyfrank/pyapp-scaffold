import {
  MAX_MESSAGE_LENGTH,
  MODELS,
  RESPONSE_MODES,
  type Model,
  type ResponseMode,
} from "../../types";

type ChatRequest = {
  message: string;
  model: Model;
  mode: ResponseMode;
};

function json(body: unknown, status = 200) {
  return Response.json(body, { status });
}

function isChatRequest(value: unknown): value is ChatRequest {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;

  return (
    typeof item.message === "string" &&
    item.message.trim().length > 0 &&
    item.message.trim().length <= MAX_MESSAGE_LENGTH &&
    MODELS.includes(item.model as Model) &&
    RESPONSE_MODES.includes(item.mode as ResponseMode)
  );
}

function mockContent(message: string, model: Model, mode: ResponseMode) {
  const normalized = message.toLowerCase();
  const suffix = `\n\n— Generated in **${mode}** mode with \`${model}\``;

  if (/plan|trip|roadmap|schedule/.test(normalized)) {
    return `## A practical plan\n\n1. **Clarify the outcome** and the constraints that matter most.\n2. Break the work into small, verifiable milestones.\n3. Review the result, then refine the highest-impact detail.\n\n> A strong plan stays flexible while keeping the destination clear.${suffix}`;
  }

  if (/code|build|component|api/.test(normalized)) {
    return `## A clean starting point\n\n- Define the smallest useful interface.\n- Keep state close to the interaction that owns it.\n- Add one focused test before each behavior.\n\n\`\`\`ts\nconst nextStep = "make it observable and testable";\n\`\`\`${suffix}`;
  }

  return `## Here’s a thoughtful take\n\nYou asked: **${message.trim()}**\n\nA useful answer starts by separating what is known from what needs exploration. I’d begin with the clearest constraint, test one concrete direction, and use the result to guide the next step.${suffix}`;
}

export async function handleChat(
  request: Request,
  wait: () => Promise<void> = async () => undefined,
) {
  const contentType = request.headers.get("content-type")?.split(";", 1)[0];
  if (contentType !== "application/json") {
    return json({ error: "Content-Type must be application/json." }, 415);
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return json({ error: "Request body must contain valid JSON." }, 400);
  }

  if (!isChatRequest(payload)) {
    return json({ error: "Provide a valid message, model, and mode." }, 400);
  }

  await wait();
  const message = payload.message.trim();

  return json({
    id: crypto.randomUUID(),
    content: mockContent(message, payload.model, payload.mode),
    createdAt: new Date().toISOString(),
  });
}
