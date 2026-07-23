import type { IconName } from "./Icon";
import Icon from "./Icon";
import Composer from "./Composer";
import type { Model, ResponseMode } from "../types";
import styles from "../interactions.module.css";

const capabilities: Array<{ label: string; prompt: string; icon: IconName }> = [
  { label: "Swarm", prompt: "Coordinate a swarm of agents to research a complex topic", icon: "swarm" },
  // { label: "Slides", prompt: "Create a clear slide deck for a new product idea", icon: "presentation" },
  { label: "Deep Research", prompt: "Research the latest thinking on sustainable cities", icon: "research" },
  // { label: "Websites", prompt: "Design a polished website for a creative studio", icon: "website" },
  { label: "Docs", prompt: "Draft a concise project brief with next steps", icon: "document" },
  // { label: "Sheets", prompt: "Build a simple budget and forecast table", icon: "sheet" },
];

type EmptyStateProps = {
  draft: string;
  model: Model;
  mode: ResponseMode;
  isLoading: boolean;
  onDraftChange: (value: string) => void;
  onModelChange: (value: Model) => void;
  onModeChange: (value: ResponseMode) => void;
  onSubmit: (value: string) => void;
};

export default function EmptyState(props: EmptyStateProps) {
  function chooseCapability(prompt: string) {
    props.onDraftChange(prompt);
    document.getElementById("interactions-message")?.focus();
  }

  return (
    <div className={styles.emptyState}>
      <div className={styles.emptyCenter}>
        <h1 className={styles.wordmark}>KIMI</h1>
        <Composer
          value={props.draft}
          model={props.model}
          mode={props.mode}
          disabled={props.isLoading}
          onChange={props.onDraftChange}
          onModelChange={props.onModelChange}
          onModeChange={props.onModeChange}
          onSubmit={props.onSubmit}
        />
        <div className={styles.capabilities} aria-label="Create with Kimi">
          {capabilities.map((capability) => (
            <button type="button" key={capability.label} onClick={() => chooseCapability(capability.prompt)}>
              <Icon name={capability.icon} />
              <span>{capability.label}</span>
            </button>
          ))}
        </div>
      </div>
      <button type="button" className={styles.inspirationBar}>
        <span><Icon name="sparkles" /> Explore inspiration</span>
        <span>Scroll to explore <span aria-hidden="true">⌃</span></span>
      </button>
    </div>
  );
}
