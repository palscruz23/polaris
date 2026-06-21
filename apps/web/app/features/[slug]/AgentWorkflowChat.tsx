"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type ApiMessage = Message & {
  conversation_id: string;
  sequence_number: number;
  provider: string | null;
  model: string | null;
  created_at: string;
};

type ConversationApiResponse = {
  id: string;
  messages: ApiMessage[];
};

type MessageExchangeApiResponse = {
  user_message: ApiMessage;
  assistant_message: ApiMessage;
  memory_update_status: string;
};

const CONVERSATION_STORAGE_KEY = "open-reliability-conversation-id";

const starterPrompts = [
  {
    label: "Identify repeat failures",
    prompt: "Help me identify repeat failures from my work order history.",
    icon: "trend",
  },
  {
    label: "Review a maintenance strategy",
    prompt: "Review an existing maintenance strategy and identify coverage gaps.",
    icon: "shield",
  },
  {
    label: "Analyse work order data",
    prompt: "Analyse my work order data for bad actors and recurring failure patterns.",
    icon: "document",
  },
  {
    label: "Build a defect elimination plan",
    prompt: "Help me build a defect elimination plan for a recurring equipment issue.",
    icon: "target",
  },
] as const;

function ArrowLeftIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m15 18-6-6 6-6" />
      <path d="M9 12h11" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M21 12a8 8 0 0 1-8 8H7l-4 2 1.3-4A9 9 0 1 1 21 12Z" />
      <path d="M8 12h.01M12 12h.01M16 12h.01" />
    </svg>
  );
}

function AttachmentIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m21.4 11.6-8.9 8.9a6 6 0 0 1-8.5-8.5l9.6-9.6a4 4 0 0 1 5.7 5.7l-9.6 9.6a2 2 0 0 1-2.8-2.8l8.9-8.9" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m22 2-7 20-4-9-9-4Z" />
      <path d="M22 2 11 13" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <rect height="10" rx="1.5" width="10" x="7" y="7" />
    </svg>
  );
}

function ShieldCheckIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

function PromptIcon({ name }: { name: (typeof starterPrompts)[number]["icon"] }) {
  if (name === "trend") {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M3 3v18h18" />
        <path d="m7 15 4-4 3 3 6-7" />
      </svg>
    );
  }

  if (name === "shield") {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
        <path d="m9 12 2 2 4-4" />
      </svg>
    );
  }

  if (name === "document") {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
        <path d="M14 2v6h6M8 13h8M8 17h8" />
      </svg>
    );
  }

  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v4M22 12h-4" />
    </svg>
  );
}

function AgentMark() {
  return (
    <span className="agent-mark" aria-hidden="true">
      <ChatIcon />
    </span>
  );
}

function AssistantMessage({ content }: { content: string }) {
  return (
    <div className="agent-message-markdown">
      <ReactMarkdown
        components={{
          a: ({ children, ...props }) => (
            <a {...props} rel="noreferrer" target="_blank">
              {children}
            </a>
          ),
        }}
        remarkPlugins={[remarkGfm]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default function AgentWorkflowChat() {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [attachment, setAttachment] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const composerInputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const requestControllerRef = useRef<AbortController>(null);
  const latestMessageId = messages[messages.length - 1]?.id;

  useEffect(() => {
    const savedConversationId = window.localStorage.getItem(
      CONVERSATION_STORAGE_KEY,
    );

    if (!savedConversationId) {
      return;
    }

    const requestController = new AbortController();

    async function loadConversation() {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/conversations/${savedConversationId}`,
          {
            signal: requestController.signal,
          },
        );

        if (!response.ok) {
          window.localStorage.removeItem(CONVERSATION_STORAGE_KEY);
          return;
        }

        const conversation: ConversationApiResponse = await response.json();
        setConversationId(conversation.id);
        setMessages(
          conversation.messages.map((message) => ({
            id: message.id,
            role: message.role,
            content: message.content,
          })),
        );
      } catch {
        if (!requestController.signal.aborted) {
          window.localStorage.removeItem(CONVERSATION_STORAGE_KEY);
        }
      }
    }

    loadConversation();

    return () => requestController.abort();
  }, []);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    messagesEndRef.current?.scrollIntoView({
      behavior: prefersReducedMotion ? "auto" : "smooth",
      block: "end",
    });
  }, [latestMessageId, isLoading]);

  useEffect(() => {
    if (!isLoading && messages.length > 0) {
      composerInputRef.current?.focus();
    }
  }, [isLoading, messages.length]);

  async function submitMessage(message: string) {
    const trimmedMessage = message.trim();

    if (!trimmedMessage || isLoading) {
      return;
    }

    const temporaryMessageId = `temporary-${messages.length + 1}`;

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: temporaryMessageId,
        role: "user",
        content: trimmedMessage,
      },
    ]);

    setDraft("");
    setAttachment("");
    setIsLoading(true);
    composerInputRef.current?.focus();

    const requestController = new AbortController();
    requestControllerRef.current = requestController;

    try {
      const activeConversationId =
        conversationId ??
        (await createConversation(requestController.signal));
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/conversations/${activeConversationId}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            content: trimmedMessage,
          }),
          signal: requestController.signal,
        },
      );

      if (!response.ok) {
        throw new Error("The Reliability Agent request failed.");
      }

      const data: MessageExchangeApiResponse = await response.json();

      setMessages((currentMessages) => [
        ...currentMessages.map((message) =>
          message.id === temporaryMessageId
            ? {
                id: data.user_message.id,
                role: data.user_message.role,
                content: data.user_message.content,
              }
            : message,
        ),
        {
          id: data.assistant_message.id,
          role: data.assistant_message.role,
          content: data.assistant_message.content,
        },
      ]);
    } catch {
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: `${temporaryMessageId}-error`,
          role: "assistant",
          content: requestController.signal.aborted
            ? "Response stopped."
            : "I could not contact the Reliability Agent. Check that the backend is running.",
        },
      ]);
    } finally {
      requestControllerRef.current = null;
      setIsLoading(false);
    }
  }

  async function createConversation(signal: AbortSignal): Promise<string> {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/conversations`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
        signal,
      },
    );

    if (!response.ok) {
      throw new Error("The conversation could not be created.");
    }

    const conversation: ConversationApiResponse = await response.json();
    setConversationId(conversation.id);
    window.localStorage.setItem(
      CONVERSATION_STORAGE_KEY,
      conversation.id,
    );

    return conversation.id;
  }

  function stopResponse() {
    requestControllerRef.current?.abort();
    composerInputRef.current?.focus();
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitMessage(draft);
  }

  return (
    <main className="agent-chat-shell">
      <header className="agent-chat-header">
        <Link className="agent-chat-back" href="/">
          <ArrowLeftIcon />
          <span>Back to home</span>
        </Link>
        <Link className="agent-chat-brand" href="/">
          Open Reliability
        </Link>
        <h1>Reliability Agent</h1>
        <div className="agent-chat-status" aria-label="Agent online">
          <span aria-hidden="true" />
          Agent online
        </div>
      </header>

      <section
        className={`agent-chat-content ${messages.length ? "has-messages" : ""}`}
        aria-live="polite"
      >
        {messages.length === 0 ? (
          <div className="agent-chat-empty">
            <AgentMark />
            <h2>How can I help with reliability today?</h2>
            <p>
              Ask questions, analyse data, and get expert recommendations from
              the Reliability Agent.
            </p>
            <div className="agent-starter-grid">
              {starterPrompts.map((starter) => (
                <button
                  className="agent-starter-prompt"
                  key={starter.label}
                  onClick={() => setDraft(starter.prompt)}
                  type="button"
                >
                  <PromptIcon name={starter.icon} />
                  <span>{starter.label}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="agent-message-list">
            {messages.map((message) => (
              <article
                className={`agent-message agent-message-${message.role}`}
                key={message.id}
              >
                {message.role === "assistant" ? <AgentMark /> : null}
                <div>
                  <span className="agent-message-role">
                    {message.role === "assistant" ? "Reliability Agent" : "You"}
                  </span>
                  {message.role === "assistant" ? (
                    <AssistantMessage content={message.content} />
                  ) : (
                    <p>{message.content}</p>
                  )}
                </div>
              </article>
            ))}
            {isLoading ? (
              <article
                className="agent-message agent-message-assistant agent-message-thinking"
                role="status"
              >
                <AgentMark />
                <div>
                  <span className="agent-message-role">Reliability Agent</span>
                  <p>Reliability Agent is thinking…</p>
                </div>
              </article>
            ) : null}
            <div
              aria-hidden="true"
              className="agent-message-end"
              ref={messagesEndRef}
            />
          </div>
        )}
      </section>

      <footer className="agent-composer-dock">
        <form
          aria-busy={isLoading}
          className="agent-composer"
          onSubmit={handleSubmit}
        >
          <input
            className="sr-only"
            disabled={isLoading}
            ref={fileInputRef}
            type="file"
            onChange={(event) =>
              setAttachment(event.target.files?.[0]?.name ?? "")
            }
          />
          <button
            aria-label="Attach a file"
            className="agent-composer-action"
            disabled={isLoading}
            onClick={() => fileInputRef.current?.click()}
            type="button"
          >
            <AttachmentIcon />
          </button>
          <div className="agent-composer-input-wrap">
            {attachment ? (
              <span className="agent-attachment-name">{attachment}</span>
            ) : null}
            <textarea
              aria-label="Message the Reliability Agent"
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submitMessage(draft);
                }
              }}
              placeholder="Ask about equipment, failures, maintenance strategies, or reliability data…"
              ref={composerInputRef}
              rows={1}
              value={draft}
            />
          </div>
          <button
            aria-label={isLoading ? "Stop response" : "Send message"}
            className={`agent-send-button ${
              isLoading ? "agent-send-button-stop" : ""
            }`}
            disabled={!isLoading && !draft.trim()}
            onClick={isLoading ? stopResponse : undefined}
            type={isLoading ? "button" : "submit"}
          >
            {isLoading ? <StopIcon /> : <SendIcon />}
          </button>
        </form>
        <p className="agent-composer-note">
          <ShieldCheckIcon />
          Recommendations should be validated against site standards and
          engineering judgement.
        </p>
      </footer>
    </main>
  );
}
