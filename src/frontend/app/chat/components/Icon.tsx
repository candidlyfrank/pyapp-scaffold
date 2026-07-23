import type { SVGProps } from "react";

export type IconName =
  | "arrow-up"
  | "chevron-down"
  | "clock"
  | "document"
  | "download"
  | "gift"
  | "globe"
  | "help"
  | "menu"
  | "message"
  | "monitor"
  | "panel"
  | "paperclip"
  | "plus"
  | "presentation"
  | "research"
  | "settings"
  | "sheet"
  | "sparkles"
  | "swarm"
  | "terminal"
  | "user"
  | "website"
  | "x";

type IconProps = SVGProps<SVGSVGElement> & { name: IconName };

export default function Icon({ name, ...props }: IconProps) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    strokeWidth: 1.7,
  };

  const paths: Record<IconName, React.ReactNode> = {
    "arrow-up": <><path d="M12 19V5" /><path d="m6.5 10.5 5.5-5.5 5.5 5.5" /></>,
    "chevron-down": <path d="m7 9.5 5 5 5-5" />,
    clock: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></>,
    document: <><path d="M7 3.5h7l4 4v13H7z" /><path d="M14 3.5v4h4M9.5 12h6M9.5 15.5h6" /></>,
    download: <><path d="M12 4v11m0 0 4-4m-4 4-4-4" /><path d="M5 19.5h14" /></>,
    gift: <><path d="M4 10h16v10H4zM3 7h18v3H3zM12 7v13" /><path d="M12 7H8.7a2.2 2.2 0 1 1 2.2-2.2C10.9 6 12 7 12 7Zm0 0h3.3a2.2 2.2 0 1 0-2.2-2.2C13.1 6 12 7 12 7Z" /></>,
    globe: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.5 2.7 3.5 5.7 3.5 9s-1 6.3-3.5 9c-2.5-2.7-3.5-5.7-3.5-9S9.5 5.7 12 3Z" /></>,
    help: <><circle cx="12" cy="12" r="9" /><path d="M9.7 9a2.4 2.4 0 1 1 3.5 2.2c-.9.5-1.2 1-1.2 1.8M12 17h.01" /></>,
    menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
    message: <><path d="M5 5.5h14v11H9l-4 3z" /><path d="M9 9.5h6M9 12.5h4" /></>,
    monitor: <><rect x="3" y="4" width="18" height="13" rx="2" /><path d="M8 21h8M12 17v4" /></>,
    panel: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M8 4v16" /></>,
    paperclip: <path d="m8.5 12.5 6.2-6.2a3 3 0 0 1 4.2 4.2l-8.1 8.1a5 5 0 0 1-7.1-7.1l8-8" />,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    presentation: <><path d="M4 4h16v12H4zM8 20l4-4 4 4M8 9h8" /></>,
    research: <><circle cx="10.5" cy="10.5" r="6" /><path d="m15 15 5 5M10.5 7.5v6M7.5 10.5h6" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19 12a7 7 0 0 0-.1-1l2-1.6-2-3.4-2.4 1a8 8 0 0 0-1.7-1L14.5 3h-5L9 6a8 8 0 0 0-1.7 1L5 6 3 9.4 5 11a7 7 0 0 0 0 2l-2 1.6L5 18l2.3-1a8 8 0 0 0 1.7 1l.5 3h5l.4-3a8 8 0 0 0 1.7-1l2.4 1 2-3.4-2-1.6a7 7 0 0 0 .1-1Z" /></>,
    sheet: <><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M4 10h16M10 4v16M15 10v10M4 15h16" /></>,
    sparkles: <><path d="m12 3 1.3 3.7L17 8l-3.7 1.3L12 13l-1.3-3.7L7 8l3.7-1.3zM18.5 14l.7 2.1 2.1.7-2.1.7-.7 2.1-.7-2.1-2.1-.7 2.1-.7zM5 13l.8 2.2L8 16l-2.2.8L5 19l-.8-2.2L2 16l2.2-.8z" /></>,
    swarm: <><circle cx="6" cy="8" r="2" /><circle cx="18" cy="8" r="2" /><circle cx="12" cy="17" r="2" /><path d="m8 9 3 6m5-6-3 6M8 8h8" /></>,
    terminal: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="m7 9 3 3-3 3M12.5 15H17" /></>,
    user: <><circle cx="12" cy="8" r="4" /><path d="M4.5 21a7.5 7.5 0 0 1 15 0" /></>,
    website: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 9h18M7 6.5h.01M10 6.5h.01" /></>,
    x: <><path d="m6 6 12 12M18 6 6 18" /></>,
  };

  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" {...common} {...props}>
      {paths[name]}
    </svg>
  );
}
