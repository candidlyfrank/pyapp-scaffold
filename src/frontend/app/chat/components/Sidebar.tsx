"use client";

import { useState } from "react";

import styles from "../interactions.module.css";
import DropdownMenu from "./DropdownMenu";
import Icon, { type IconName } from "./Icon";

const primaryNav: Array<{ label: string; icon: IconName; badge?: string }> = [
  { label: "My Kimi", icon: "message" },
  // { label: "Scheduled Tasks", icon: "clock" },
];

const workNav: Array<{ label: string; icon: IconName; badge?: string }> = [
  // { label: "Kimi Work", icon: "monitor", badge: "Beta" },
  // { label: "Kimi Code", icon: "terminal" },
  // { label: "Kimi Claw", icon: "sparkles" },
];

const sampleChats = ["Launch research brief", "A quiet weekend in Kyoto", "Portfolio refresh ideas"];

type SidebarProps = {
  collapsed: boolean;
  onToggle: () => void;
  onNewChat: () => void;
  onSample: (title: string) => void;
  drawer?: boolean;
};

const loggedIn = false;

export default function Sidebar({ collapsed, onToggle, onNewChat, onSample, drawer = false }: SidebarProps) {
  const [language, setLanguage] = useState("English");
  const [help, setHelp] = useState("Help center");
  const [settings, setSettings] = useState("Appearance");

  return (
    <aside className={`${styles.sidebar} ${collapsed ? styles.sidebarCollapsed : ""} ${drawer ? styles.drawerSidebar : ""}`}>
      <div className={styles.sidebarTop}>
        <div className={styles.brandRow}>
          <div className={styles.brandMark} aria-label="Kimi home">K<span>•</span></div>
          {!drawer && (
            <button
              type="button"
              className={styles.sidebarToggle}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              onClick={onToggle}
            >
              <Icon name="panel" />
            </button>
          )}
        </div>
        <button type="button" className={styles.newChat} onClick={onNewChat} aria-label="New Chat">
          <Icon name="plus" />
          <span>New Chat</span>
          <kbd>⌘ K</kbd>
        </button>
        <nav aria-label="Main navigation" className={styles.sidebarNav}>
          {primaryNav.map((item) => (
            <button type="button" key={item.label} title={collapsed ? item.label : undefined}>
              <Icon name={item.icon} /><span>{item.label}</span>
            </button>
          ))}
          <div className={styles.navGroupLabel}><span>•••</span><span>Collapse</span><Icon name="chevron-down" /></div>
          {workNav.map((item) => (
            <button type="button" key={item.label} title={collapsed ? item.label : undefined}>
              <Icon name={item.icon} /><span>{item.label}</span>{item.badge && <small>{item.badge}</small>}
            </button>
          ))}
        </nav>
        <div className={styles.history}>
          <p>Chats</p>
          {sampleChats.map((chat) => (
            <button type="button" key={chat} onClick={() => onSample(chat)} title={collapsed ? chat : undefined}>
              <Icon name="message" /><span>{chat}</span>
            </button>
          ))}
          {loggedIn && (
              <span className={styles.syncHint}>Log in to sync chat history</span>
          )}

        </div>
      </div>
      { loggedIn && (
          <div className={styles.sidebarBottom}>
            <button type="button" className={styles.inviteCard}>
              <Icon name="gift" />
              <span><strong>Invite to Earn</strong><small>Up to 1-year K3 Credits</small></span>
              <span aria-hidden="true">›</span>
            </button>
            <div className={styles.utilityRow}>
              <DropdownMenu label="Language" value={language} options={["English", "中文"]} onChange={setLanguage} />
              <DropdownMenu
                  label="Help"
                  value={help}
                  options={["Help center", "Keyboard shortcuts"]}
                  onChange={setHelp}
                  icon="help"
                  iconOnly
                  align="right"
              />
              <DropdownMenu
                  label="Settings"
                  value={settings}
                  options={["Appearance", "Privacy"]}
                  onChange={setSettings}
                  icon="settings"
                  iconOnly
                  align="right"
              />
            </div>
            <button type="button" className={styles.profileButton}>
              <span className={styles.profileAvatar}><Icon name="user" /></span>
              <span>Log In</span>
              <Icon name="download" />
            </button>
          </div>
      )}
    </aside>
  );
}
