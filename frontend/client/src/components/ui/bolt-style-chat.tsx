"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Plus,
  Lightbulb,
  Paperclip,
  Image,
  FileCode,
  ChevronDown,
  Check,
  Sparkles,
  Zap,
  Brain,
  Bolt,
  Github,
  SendHorizontal,
} from "lucide-react";
import logo from "@shared/logo.png";

interface Model {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  badge?: string;
}

function FigmaIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M8 24C10.208 24 12 22.208 12 20V16H8C5.792 16 4 17.792 4 20C4 22.208 5.792 24 8 24Z" fill="currentColor" />
      <path d="M4 12C4 9.792 5.792 8 8 8H12V16H8C5.792 16 4 14.208 4 12Z" fill="currentColor" />
      <path d="M4 4C4 1.792 5.792 0 8 0H12V8H8C5.792 8 4 6.208 4 4Z" fill="currentColor" />
      <path d="M12 0H16C18.208 0 20 1.792 20 4C20 6.208 18.208 8 16 8H12V0Z" fill="currentColor" />
      <path d="M20 12C20 14.208 18.208 16 16 16C13.792 16 12 14.208 12 12C12 9.792 13.792 8 16 8C18.208 8 20 9.792 20 12Z" fill="currentColor" />
    </svg>
  );
}

const models: Model[] = [
  {
    id: "solution-architect",
    name: "Solution Architect",
    description: "Balanced design guidance",
    icon: <Zap className="size-4 text-gold-cloud" />,
    badge: "Default",
  },
  {
    id: "cost-optimizer",
    name: "Cost Optimizer",
    description: "Lean infrastructure tradeoffs",
    icon: <Sparkles className="size-4 text-warm-sand" />,
    badge: "Budget",
  },
  {
    id: "scalability-review",
    name: "Scalability Review",
    description: "Growth-oriented thinking",
    icon: <Brain className="size-4 text-bronze-muted" />,
  },
];

function ModelSelector({
  selectedModel = "solution-architect",
  onModelChange,
}: {
  selectedModel?: string;
  onModelChange?: (model: Model) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [selected, setSelected] = useState(
    models.find((model) => model.id === selectedModel) || models[0]
  );

  const handleSelect = (model: Model) => {
    setSelected(model);
    setIsOpen(false);
    onModelChange?.(model);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 rounded-full border border-gold-soft/15 bg-bg-surface-soft/70 px-3 py-1.5 text-xs font-medium text-text-secondary transition-all duration-200 hover:border-gold-soft/35 hover:text-text-primary"
      >
        {selected.icon}
        <span>{selected.name}</span>
        <ChevronDown
          className={`size-3.5 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
        />
      </button>

      {isOpen ? (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute bottom-full left-0 z-50 mb-2 min-w-[240px] overflow-hidden rounded-2xl border border-gold-soft/15 bg-[rgba(17,22,29,0.96)] shadow-[0_24px_80px_rgba(0,0,0,0.55)] backdrop-blur-xl">
            <div className="p-2">
              <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.22em] text-text-muted">
                Select Mode
              </div>
              {models.map((model) => (
                <button
                  key={model.id}
                  onClick={() => handleSelect(model)}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition-all duration-150 ${
                    selected.id === model.id
                      ? "bg-gold-soft/10 text-text-primary"
                      : "text-text-secondary hover:bg-white/4 hover:text-text-primary"
                  }`}
                >
                  <div className="flex-shrink-0">{model.icon}</div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{model.name}</span>
                      {model.badge ? (
                        <span className="rounded-full bg-gold-soft/10 px-1.5 py-0.5 text-[10px] font-medium text-gold-soft">
                          {model.badge}
                        </span>
                      ) : null}
                    </div>
                    <span className="text-[11px] text-text-muted">{model.description}</span>
                  </div>
                  {selected.id === model.id ? (
                    <Check className="size-4 flex-shrink-0 text-gold-cloud" />
                  ) : null}
                </button>
              ))}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}

function ChatInput({
  onSend,
  placeholder = "What do you want to build?",
}: {
  onSend?: (message: string) => void;
  placeholder?: string;
}) {
  const [message, setMessage] = useState("");
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [message]);

  const handleSubmit = () => {
    if (!message.trim()) {
      return;
    }
    onSend?.(message);
    setMessage("");
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="relative mx-auto w-full max-w-[720px]">
      <div className="pointer-events-none absolute -inset-[1px] rounded-[28px] bg-gradient-to-b from-gold-soft/20 via-gold-soft/5 to-transparent" />
      <div className="relative rounded-[28px] border border-gold-soft/15 bg-[linear-gradient(180deg,rgba(20,27,36,0.98),rgba(11,15,24,0.98))] shadow-[0_28px_120px_rgba(0,0,0,0.55),0_0_40px_rgba(249,217,171,0.08)]">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="min-h-[86px] max-h-[200px] w-full resize-none bg-transparent px-5 pt-5 pb-3 text-[15px] text-text-primary placeholder:text-text-muted focus:outline-none"
          style={{ height: "86px" }}
        />

        <div className="flex items-center justify-between px-3 pb-3 pt-1">
          <div className="flex items-center gap-2">
            <div className="relative">
              <button
                onClick={() => setShowAttachMenu(!showAttachMenu)}
                className="flex size-9 items-center justify-center rounded-full border border-gold-soft/12 bg-bg-surface-soft/80 text-text-secondary transition-all duration-200 hover:border-gold-soft/30 hover:text-text-primary"
              >
                <Plus className={`size-4 transition-transform duration-200 ${showAttachMenu ? "rotate-45" : ""}`} />
              </button>

              {showAttachMenu ? (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setShowAttachMenu(false)} />
                  <div className="absolute bottom-full left-0 z-50 mb-2 min-w-[190px] overflow-hidden rounded-2xl border border-gold-soft/15 bg-[rgba(17,22,29,0.96)] shadow-[0_24px_80px_rgba(0,0,0,0.55)] backdrop-blur-xl">
                    <div className="p-2">
                      {[
                        { icon: <Paperclip className="size-4" />, label: "Upload file" },
                        { icon: <Image className="size-4" />, label: "Add image" },
                        { icon: <FileCode className="size-4" />, label: "Import code" },
                      ].map((item) => (
                        <button
                          key={item.label}
                          className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-text-secondary transition-all duration-150 hover:bg-white/4 hover:text-text-primary"
                        >
                          {item.icon}
                          <span className="text-sm">{item.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              ) : null}
            </div>
            <ModelSelector />
          </div>

          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1.5 rounded-full px-3 py-2 text-xs font-medium text-text-muted transition-all duration-200 hover:bg-white/4 hover:text-text-primary">
              <Lightbulb className="size-4 text-gold-cloud" />
              <span className="hidden sm:inline">Plan</span>
            </button>
            <button
              onClick={handleSubmit}
              disabled={!message.trim()}
              className="flex items-center gap-2 rounded-full bg-gradient-to-r from-gold-cloud via-gold-soft to-warm-sand px-4 py-2 text-sm font-medium text-bg-main shadow-[0_0_20px_rgba(249,217,171,0.2)] transition-all duration-200 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <span className="hidden sm:inline">Design now</span>
              <SendHorizontal className="size-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function RayBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 select-none overflow-hidden">
      <div className="absolute inset-0 bg-bg-main" />
      <div
        className="absolute left-1/2 h-[1800px] w-[4000px] -translate-x-1/2 sm:w-[6000px]"
        style={{
          background:
            "radial-gradient(circle at center 800px, rgba(228, 187, 150, 0.45) 0%, rgba(228, 187, 150, 0.18) 14%, rgba(42, 67, 83, 0.16) 22%, rgba(7, 9, 13, 0.2) 28%)",
        }}
      />
      <div
        className="absolute left-1/2 top-[175px] h-[1600px] w-[1600px] sm:top-1/2 sm:h-[2865px] sm:w-[3043px]"
        style={{ transform: "translate(-50%) rotate(180deg)" }}
      >
        <div
          className="absolute -mt-[13px] h-full w-full rounded-full"
          style={{
            background:
              "radial-gradient(43.89% 25.74% at 50.02% 97.24%, #11161D 0%, #07090D 100%)",
            border: "16px solid rgba(247, 238, 220, 0.92)",
            transform: "rotate(180deg)",
            zIndex: 5,
          }}
        />
        <div
          className="absolute -mt-[11px] h-full w-full rounded-full bg-bg-main"
          style={{
            border: "23px solid rgba(249, 217, 171, 0.32)",
            transform: "rotate(180deg)",
            zIndex: 4,
          }}
        />
        <div
          className="absolute -mt-[8px] h-full w-full rounded-full bg-bg-main"
          style={{
            border: "23px solid rgba(201, 165, 137, 0.28)",
            transform: "rotate(180deg)",
            zIndex: 3,
          }}
        />
        <div
          className="absolute -mt-[4px] h-full w-full rounded-full bg-bg-main"
          style={{
            border: "23px solid rgba(61, 79, 102, 0.3)",
            transform: "rotate(180deg)",
            zIndex: 2,
          }}
        />
        <div
          className="absolute h-full w-full rounded-full bg-bg-main"
          style={{
            border: "20px solid rgba(228, 187, 150, 0.42)",
            boxShadow: "0 -15px 24.8px rgba(228, 187, 150, 0.18)",
            transform: "rotate(180deg)",
            zIndex: 1,
          }}
        />
      </div>
    </div>
  );
}

function AnnouncementBadge({
  text,
  href = "#",
}: {
  text: string;
  href?: string;
}) {
  const content = (
    <>
      <span
        className="pointer-events-none absolute left-0 right-0 top-0 h-1/2 opacity-70 mix-blend-overlay"
        style={{
          background:
            "radial-gradient(ellipse at center top, rgba(255, 255, 255, 0.12) 0%, transparent 70%)",
        }}
      />
      <span
        className="absolute -top-px left-1/2 h-[2px] w-[100px] -translate-x-1/2 opacity-60"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, rgba(249, 217, 171, 0.9) 20%, rgba(170, 146, 128, 0.85) 50%, rgba(228, 187, 150, 0.85) 80%, transparent 100%)",
        }}
      />
      <Bolt className="relative z-10 size-4 text-gold-soft" />
      <span className="relative z-10 font-medium text-text-primary">{text}</span>
    </>
  );

  const className =
    "relative inline-flex min-h-[40px] items-center gap-2 overflow-hidden rounded-full px-5 py-2 text-sm transition-all duration-300 hover:scale-[1.02] active:scale-[0.98]";
  const style = {
    background:
      "linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03))",
    backdropFilter: "blur(20px) saturate(140%)",
    boxShadow:
      "inset 0 1px rgba(255,255,255,0.16), inset 0 -1px rgba(0,0,0,0.1), 0 8px 32px -8px rgba(0,0,0,0.25), 0 0 0 1px rgba(249,217,171,0.08)",
  };

  return href !== "#" ? (
    <a href={href} target="_blank" rel="noopener noreferrer" className={className} style={style}>
      {content}
    </a>
  ) : (
    <button className={className} style={style}>
      {content}
    </button>
  );
}

function ImportButtons({
  onImport,
}: {
  onImport?: (source: string) => void;
}) {
  return (
    <div className="flex items-center justify-center gap-4">
      <span className="text-sm text-text-muted">or import from</span>
      <div className="flex gap-2">
        {[
          { id: "figma", name: "Figma", icon: <FigmaIcon className="size-4" /> },
          { id: "github", name: "GitHub", icon: <Github className="size-4" /> },
        ].map((option) => (
          <button
            key={option.id}
            onClick={() => onImport?.(option.id)}
            className="flex items-center gap-1.5 rounded-full border border-gold-soft/12 bg-[rgba(12,18,26,0.88)] px-3 py-1.5 text-xs font-medium text-text-secondary transition-all duration-200 hover:border-gold-soft/30 hover:bg-bg-surface hover:text-text-primary"
          >
            {option.icon}
            <span>{option.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

interface BoltStyleChatProps {
  title?: string;
  subtitle?: string;
  announcementText?: string;
  announcementHref?: string;
  placeholder?: string;
  onSend?: (message: string) => void;
  onImport?: (source: string) => void;
  fullBleed?: boolean;
}

export function BoltStyleChat({
  title = "What will you",
  subtitle = "Shape secure, elegant cloud architectures by chatting with AI.",
  announcementText = "Nimbus Architect Workspace",
  announcementHref = "#",
  placeholder = "What do you want to build?",
  onSend,
  onImport,
  fullBleed = false,
}: BoltStyleChatProps) {
  return (
    <div
      className={`relative flex w-full flex-col items-center justify-center overflow-hidden bg-bg-main ${
        fullBleed
          ? "min-h-screen"
          : "min-h-[640px] rounded-[36px] border border-gold-soft/10"
      }`}
    >
      <RayBackground />
      <div className="absolute top-[68px]">
        <AnnouncementBadge text={announcementText} href={announcementHref} />
      </div>

      <div className="absolute left-1/2 top-[66%] flex h-full w-full -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center overflow-hidden px-4 sm:top-1/2">
        <div className="mb-6 text-center">
          <div className="mb-6 flex justify-center">
            <div className="rounded-[28px] border border-gold-soft/15 bg-[rgba(17,22,29,0.82)] p-2 shadow-[0_20px_70px_rgba(0,0,0,0.45),0_0_40px_rgba(249,217,171,0.08)] backdrop-blur-xl">
              <img
                src={logo}
                alt="Nimbus logo"
                className="h-20 w-20 rounded-[22px] object-cover sm:h-24 sm:w-24"
              />
            </div>
          </div>
          <h1 className="mb-1 text-4xl font-bold tracking-tight text-text-primary sm:text-5xl">
            {title}{" "}
            <span className="bg-gradient-to-b from-gold-soft via-gold-cloud to-text-primary bg-clip-text text-transparent italic">
              design
            </span>{" "}
            today?
          </h1>
          <p className="text-base font-semibold text-text-secondary sm:text-lg">
            {subtitle}
          </p>
        </div>

        <div className="mt-2 mb-6 w-full max-w-[760px] sm:mb-8">
          <ChatInput placeholder={placeholder} onSend={onSend} />
        </div>

        <ImportButtons onImport={onImport} />
      </div>
    </div>
  );
}
