"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type Message = {
    role: "user" | "assistant";
    content: string;
};

type AiChatSidebarProps = {
    token: string;
    onBoardUpdate: () => void;
};

export const AiChatSidebar = ({ token, onBoardUpdate }: AiChatSidebarProps) => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = useCallback(async () => {
        const text = input.trim();
        if (!text || isLoading) return;

        const userMessage: Message = { role: "user", content: text };
        setMessages((prev) => [...prev, userMessage]);
        setInput("");
        setIsLoading(true);

        try {
            const data = await api.chatWithAi(token, text);
            const aiMessage: Message = { role: "assistant", content: data.response };
            setMessages((prev) => [...prev, aiMessage]);

            if (data.board_updates && data.board_updates.length > 0) {
                onBoardUpdate();
            }
        } catch {
            const errMessage: Message = {
                role: "assistant",
                content: "Sorry, something went wrong. Please try again.",
            };
            setMessages((prev) => [...prev, errMessage]);
        } finally {
            setIsLoading(false);
        }
    }, [input, isLoading, token, onBoardUpdate]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    if (!isOpen) {
        return (
            <button
                type="button"
                onClick={() => setIsOpen(true)}
                data-testid="ai-chat-toggle"
                className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-[var(--secondary-purple)] text-white shadow-lg transition hover:brightness-110"
                aria-label="Open AI chat"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="h-6 w-6"
                >
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
            </button>
        );
    }

    return (
        <aside
            data-testid="ai-chat-sidebar"
            className="fixed bottom-0 right-0 top-0 z-50 flex w-[400px] flex-col border-l border-[var(--stroke)] bg-white/95 shadow-[-8px_0_30px_rgba(3,33,71,0.08)] backdrop-blur-lg"
        >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[var(--stroke)] px-5 py-4">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                        AI Assistant
                    </p>
                    <p className="mt-1 font-display text-lg font-semibold text-[var(--navy-dark)]">
                        Chat
                    </p>
                </div>
                <button
                    type="button"
                    onClick={() => setIsOpen(false)}
                    data-testid="ai-chat-close"
                    className="flex h-9 w-9 items-center justify-center rounded-full border border-[var(--stroke)] text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--navy-dark)]"
                    aria-label="Close AI chat"
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="h-4 w-4"
                    >
                        <path d="M18 6 6 18M6 6l12 12" />
                    </svg>
                </button>
            </div>

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4">
                {messages.length === 0 && (
                    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
                        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--surface)]">
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth={1.5}
                                className="h-6 w-6 text-[var(--primary-blue)]"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
                                />
                            </svg>
                        </div>
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                            Ask me anything
                        </p>
                        <p className="max-w-[220px] text-xs leading-5 text-[var(--gray-text)]">
                            I can create cards, move them between columns, rename columns, and more.
                        </p>
                    </div>
                )}
                <div className="flex flex-col gap-3">
                    {messages.map((msg, i) => (
                        <div
                            key={i}
                            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                        >
                            <div
                                data-testid={`chat-message-${msg.role}`}
                                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 ${msg.role === "user"
                                        ? "bg-[var(--secondary-purple)] text-white"
                                        : "border border-[var(--stroke)] bg-[var(--surface)] text-[var(--navy-dark)]"
                                    }`}
                            >
                                {msg.content}
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="flex justify-start">
                            <div
                                data-testid="ai-loading"
                                className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--gray-text)]"
                            >
                                Thinking...
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Input */}
            <div className="border-t border-[var(--stroke)] px-5 py-4">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask the AI..."
                        disabled={isLoading}
                        data-testid="ai-chat-input"
                        className="flex-1 rounded-xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm font-medium text-[var(--navy-dark)] outline-none transition placeholder:text-[var(--gray-text)] focus:border-[var(--primary-blue)] disabled:opacity-60"
                    />
                    <button
                        type="button"
                        onClick={handleSend}
                        disabled={isLoading || !input.trim()}
                        data-testid="ai-chat-send"
                        className="flex h-[46px] w-[46px] flex-shrink-0 items-center justify-center rounded-xl bg-[var(--secondary-purple)] text-white transition hover:brightness-110 disabled:opacity-60"
                        aria-label="Send message"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 24 24"
                            fill="currentColor"
                            className="h-5 w-5"
                        >
                            <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
                        </svg>
                    </button>
                </div>
            </div>
        </aside>
    );
};
