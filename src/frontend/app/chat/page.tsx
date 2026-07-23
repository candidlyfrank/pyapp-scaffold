import type { Metadata } from "next";
import dynamic from "next/dynamic";

const InteractionsWorkspace = dynamic(
  () => import("./components/InteractionsWorkspace"),
);

export const metadata: Metadata = {
  title: "Kimi-style Chat | PyApp Scaffold",
  description: "An isolated, original Kimi-inspired chat interface demonstration.",
};

export default function InteractionsPage() {
  return <InteractionsWorkspace />;
}
