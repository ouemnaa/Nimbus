"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
    ImageIcon,
    FileUp,
    Figma,
    MonitorIcon,
    CircleUserRound,
    ArrowUpIcon,
    Paperclip,
    PlusIcon,
} from "lucide-react";

interface UseAutoResizeTextareaProps {
    minHeight: number;
    maxHeight?: number;
}

function useAutoResizeTextarea({
    minHeight,
    maxHeight,
}: UseAutoResizeTextareaProps) {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const adjustHeight = useCallback(
        (reset?: boolean) => {
            const textarea = textareaRef.current;
            if (!textarea) return;

            if (reset) {
                textarea.style.height = `${minHeight}px`;
                return;
            }

            textarea.style.height = `${minHeight}px`;
            const newHeight = Math.max(
                minHeight,
                Math.min(
                    textarea.scrollHeight,
                    maxHeight ?? Number.POSITIVE_INFINITY
                )
            );
            textarea.style.height = `${newHeight}px`;
        },
        [minHeight, maxHeight]
    );

    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = `${minHeight}px`;
        }
    }, [minHeight]);

    useEffect(() => {
        const handleResize = () => adjustHeight();
        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
    }, [adjustHeight]);

    return { textareaRef, adjustHeight };
}

interface VercelV0ChatProps {
    onSubmit?: (value: string) => void;
    placeholder?: string;
    title?: string;
}

export function VercelV0Chat({
    onSubmit,
    placeholder = "Describe your infrastructure requirements...",
    title = "What are you building?",
}: VercelV0ChatProps) {
    const [value, setValue] = useState("");
    const [isFocused, setIsFocused] = useState(false);
    const { textareaRef, adjustHeight } = useAutoResizeTextarea({
        minHeight: 60,
        maxHeight: 200,
    });

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (value.trim()) {
                onSubmit?.(value);
                setValue("");
                adjustHeight(true);
            }
        }
    };

    const handleSendClick = () => {
        if (value.trim()) {
            onSubmit?.(value);
            setValue("");
            adjustHeight(true);
        }
    };

    return (
        <div className="flex flex-col items-center w-full max-w-4xl mx-auto p-2 space-y-6">
            {title && (
              <h1 className="text-4xl font-bold text-foreground">
                {title}
              </h1>
            )}

            <div className="w-full">
                <div className={cn(
                  "relative bg-gradient-to-b from-[#182232] to-[#101724] rounded-2xl border transition-all duration-300 shadow-[0_16px_60px_rgba(0,0,0,0.65),0_0_40px_rgba(249,217,171,0.08)] overflow-hidden",
                  isFocused ? "border-gold-soft/60 shadow-[0_20px_70px_rgba(0,0,0,0.8),0_0_50px_rgba(249,217,171,0.22)]" : "border-gold-soft/30"
                )}>
                    <div className="overflow-y-auto">
                        <Textarea
                            ref={textareaRef}
                            value={value}
                            onChange={(e) => {
                              setValue(e.target.value);
                              adjustHeight();
                            }}
                            onKeyDown={handleKeyDown}
                            onFocus={() => setIsFocused(true)}
                            onBlur={() => setIsFocused(false)}
                            placeholder={placeholder}
                            className={cn(
                                "w-full px-5 py-4",
                                "resize-none",
                                "bg-[#0C121D]",
                                "border-none",
                                "text-[#F7EEDC] text-base leading-relaxed font-normal",
                                "focus:outline-none",
                                "focus-visible:ring-0 focus-visible:ring-offset-0",
                                "placeholder:text-[#A8A195] placeholder:text-sm placeholder:font-normal",
                                "min-h-[70px]"
                            )}
                            style={{
                              overflow: "hidden",
                            }}
                        />
                    </div>

                    <div className="flex items-center justify-between px-4 py-3 bg-[#121A28] border-t border-gold-soft/15">
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                className="group px-3 py-1.5 hover:bg-gold-soft/15 rounded-lg transition-all duration-200 flex items-center gap-1.5 text-xs text-[#C9BFAF] hover:text-gold-soft border border-transparent hover:border-gold-soft/20"
                            >
                                <Paperclip className="w-4 h-4 text-gold-cloud group-hover:text-gold-soft transition-colors" />
                                <span>Attach</span>
                            </button>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                type="button"
                                className="px-3 py-1.5 rounded-lg text-xs font-medium text-[#F7EEDC] transition-all duration-200 border border-gold-soft/25 hover:border-gold-soft/50 hover:bg-gold-soft/15 hover:text-gold-soft flex items-center justify-between gap-1.5 bg-[#182232]"
                            >
                                <PlusIcon className="w-3.5 h-3.5 text-gold-cloud" />
                                Project
                            </button>
                            <button
                                type="button"
                                onClick={handleSendClick}
                                className={cn(
                                    "p-2 rounded-lg text-sm transition-all duration-200 border flex items-center justify-center",
                                    value.trim()
                                        ? "bg-gradient-to-br from-gold-cloud via-gold-soft to-deep-ochre text-bg-main hover:shadow-[0_0_20px_rgba(249,217,171,0.4)] border-transparent"
                                        : "text-text-muted border-gold-soft/20 bg-[#182232]"
                                )}
                            >
                                <ArrowUpIcon
                                    className={cn(
                                        "w-4 h-4",
                                        value.trim()
                                            ? "text-bg-main font-bold"
                                            : "text-text-muted"
                                    )}
                                />
                                <span className="sr-only">Send</span>
                            </button>
                        </div>
                    </div>
                </div>

                <div className="flex items-center justify-center gap-3 mt-6 flex-wrap">
                    <ActionButton
                        icon={<ImageIcon className="w-4 h-4 text-gold-cloud" />}
                        label="Clone a Screenshot"
                    />
                    <ActionButton
                        icon={<Figma className="w-4 h-4 text-gold-cloud" />}
                        label="Import from Figma"
                    />
                    <ActionButton
                        icon={<FileUp className="w-4 h-4 text-gold-cloud" />}
                        label="Upload a Project"
                    />
                    <ActionButton
                        icon={<MonitorIcon className="w-4 h-4 text-gold-cloud" />}
                        label="Landing Page"
                    />
                    <ActionButton
                        icon={<CircleUserRound className="w-4 h-4 text-gold-cloud" />}
                        label="Sign Up Form"
                    />
                </div>
            </div>
        </div>
    );
}

interface ActionButtonProps {
    icon: React.ReactNode;
    label: string;
}

function ActionButton({ icon, label }: ActionButtonProps) {
    return (
        <button
            type="button"
            className="flex items-center gap-2 px-4 py-2 bg-[#182232] hover:bg-[#202C40] rounded-full border border-gold-soft/25 hover:border-gold-soft/55 text-[#F7EEDC] hover:text-gold-soft transition-all duration-200 shadow-md shadow-black/40 hover:shadow-[0_0_20px_rgba(249,217,171,0.15)]"
        >
            {icon}
            <span className="text-xs font-medium">{label}</span>
        </button>
    );
}

