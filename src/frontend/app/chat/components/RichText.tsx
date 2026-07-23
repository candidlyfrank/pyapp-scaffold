import { Fragment, type ReactNode } from "react";

import styles from "../interactions.module.css";

const INLINE_PATTERN = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\((?:[^()]|\([^)]*\))+\)|<[^>]+>.*?<\/[^>]+>)/g;

function inline(content: string): ReactNode[] {
  return content.split(INLINE_PATTERN).filter(Boolean).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={index}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={index}>{part.slice(1, -1)}</code>;
    }
    const link = part.match(/^\[([^\]]+)]\((.+)\)$/);
    if (link) {
      if (/^https?:\/\//i.test(link[2])) {
        return <a key={index} href={link[2]} target="_blank" rel="noreferrer">{link[1]}</a>;
      }
      return <span key={index}>{link[1]}</span>;
    }
    if (part.startsWith("<")) return <span key={index}>{part}</span>;
    return <Fragment key={index}>{part}</Fragment>;
  });
}

function normalBlocks(content: string, keyPrefix: string) {
  const lines = content.split("\n");
  const blocks: ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }
    if (line.startsWith("### ")) {
      blocks.push(<h3 key={`${keyPrefix}-${index}`}>{inline(line.slice(4))}</h3>);
      index += 1;
      continue;
    }
    if (line.startsWith("## ")) {
      blocks.push(<h2 key={`${keyPrefix}-${index}`}>{inline(line.slice(3))}</h2>);
      index += 1;
      continue;
    }
    if (/^[-*] /.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^[-*] /.test(lines[index])) {
        items.push(lines[index].slice(2));
        index += 1;
      }
      blocks.push(<ul key={`${keyPrefix}-${index}`}>{items.map((item, itemIndex) => <li key={itemIndex}>{inline(item)}</li>)}</ul>);
      continue;
    }
    if (/^\d+\. /.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\d+\. /.test(lines[index])) {
        items.push(lines[index].replace(/^\d+\. /, ""));
        index += 1;
      }
      blocks.push(<ol key={`${keyPrefix}-${index}`}>{items.map((item, itemIndex) => <li key={itemIndex}>{inline(item)}</li>)}</ol>);
      continue;
    }
    if (line.startsWith("> ")) {
      blocks.push(<blockquote key={`${keyPrefix}-${index}`}>{inline(line.slice(2))}</blockquote>);
      index += 1;
      continue;
    }

    const paragraph = [line];
    index += 1;
    while (index < lines.length && lines[index].trim() && !/^(## |### |[-*] |\d+\. |> )/.test(lines[index])) {
      paragraph.push(lines[index]);
      index += 1;
    }
    blocks.push(<p key={`${keyPrefix}-${index}`}>{inline(paragraph.join(" "))}</p>);
  }
  return blocks;
}

export default function RichText({ content }: { content: string }) {
  const blocks: ReactNode[] = [];
  const codePattern = /```([\w-]+)?\n([\s\S]*?)```/g;
  let cursor = 0;
  let match: RegExpExecArray | null;

  while ((match = codePattern.exec(content)) !== null) {
    blocks.push(...normalBlocks(content.slice(cursor, match.index), `before-${match.index}`));
    blocks.push(
      <pre key={`code-${match.index}`} data-language={match[1] || undefined}>
        <code>{match[2].replace(/\n$/, "")}</code>
      </pre>,
    );
    cursor = match.index + match[0].length;
  }
  blocks.push(...normalBlocks(content.slice(cursor), `after-${cursor}`));

  return <div className={styles.richText}>{blocks}</div>;
}
