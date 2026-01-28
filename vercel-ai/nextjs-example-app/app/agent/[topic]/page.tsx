"use client";
import Form from "next/form";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

export default function Agent() {
  const { topic } = useParams<{ topic: string }>();
  const [messages, setMessages] = useState<{ content: string; role: string }[]>(
    [],
  );
  const [isConnecting, setIsConnecting] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let offset = 0;
    let evtSource: EventSource;
    const obtainAPIResponse = async () => {
      try {
        evtSource = new EventSource(`/pubsub/${topic}?offset=${offset}`);
        evtSource.onmessage = (event: MessageEvent) => {
          if (event.data && !cancelled) {
            const parsedData = JSON.parse(event.data);
            setMessages((messages) => {
              const newValue = [
                ...messages,
                {
                  content: parsedData.content,
                  role: parsedData.role,
                },
              ];

              offset = newValue.length;
              return newValue;
            });
          }
        };
        evtSource.onopen = () => {
          setTimeout(() => {
            setIsConnecting(false);
          }, 250);
        };
        evtSource.onerror = (error) => {
          console.error("EventSource failed:", error);

          if (evtSource.readyState === EventSource.CLOSED) {
            setTimeout(() => {
              if (!cancelled) {
                obtainAPIResponse();
              }
            }, 1000);
          }
        };
      } catch (error) {}
    };
    obtainAPIResponse();
    return () => {
      evtSource.close();
      cancelled = true;
    };
  }, [topic]);

  const formAction = async (formData: FormData) => {
    if (String(formData.get("message"))) {
      await fetch(`/agent/${topic}/api`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          message: String(formData.get("message")),
        }),
      });
    }
  };

  const isLastMessageFromUser = messages.at(-1)?.role === "user";

  return (
    <div className="min-h-[100vh] max-w-xl w-full mx-auto flex flex-col ">
      <div className="flex-auto py-24 flex flex-col gap-2 items-start px-2">
        {messages.map((message, index) => {
          if (message.role === "user") {
            return (
              <div
                key={index}
                className="ml-auto rounded-xl bg-white border border-gray-200 shadow-xs py-1 px-2 whitespace-pre-line max-w-[80%]"
                ref={(e) => {
                  if (index === messages.length - 1 && e) {
                    document.getElementById("bottom")?.scrollIntoView();
                  }
                }}
              >
                {message.content}{" "}
              </div>
            );
          } else {
            return (
              <pre
                key={index}
                className="py-2 px-3 whitespace-pre-line max-w-[80%] break-words text-sm bg-gray-200/50 rounded-xl border-gray-200 shadow-[inset_0_1px_0px_0px_rgba(0,0,0,0.03)]"
              >
                <code
                  ref={(e) => {
                    if (index === messages.length - 1 && e) {
                      document.getElementById("bottom")?.scrollIntoView();
                    }
                  }}
                >
                  {message.content}{" "}
                </code>
              </pre>
            );
          }
        })}
        {isLastMessageFromUser && (
          <div className="flex items-center gap-1 text-gray-500">
            <Spinner /> Thinking…
          </div>
        )}
        <div id="bottom" className="scroll-mb-24" />
      </div>
      <div className="fixed bottom-0 left-0 right-0 h-36  bg-gradient-to-b from-transparent to-[var(--background)]  " />
      <div className="sticky bottom-4 w-full rounded-lg bg-white  outline-1 -outline-offset-1 outline-gray-300 focus-within:outline-2 focus-within:-outline-offset-2 focus-within:outline-indigo-600 focus-within:shadow-lg">
        <Form className="relative min-h-28" action={formAction}>
          <textarea
            name="message"
            key={String(messages.length === 0 && !isConnecting)}
            aria-label="Write your message"
            placeholder="Write your message"
            className="absolute inset-0 block w-full resize-none bg-transparent px-3 py-1.5 text-base transition-colors duration-2500 delay-250  text-gray-900 placeholder:text-gray-400 focus:outline-0 sm:text-sm/6"
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.metaKey) {
                e.currentTarget.form?.requestSubmit();
              }
            }}
            data-isconnecting={isConnecting}
            defaultValue={
              messages.length === 0 && !isConnecting
                ? `A taxi driver earns $9461 per 1-hour of work.\nIf he works 12 hours a day and in 1 hour\nhe uses 12 liters of petrol with a price  of $134 for 1 liter.\nHow much money does he earn in one day?`
                : ""
            }
          />
          <button className="absolute right-1.5 flex bottom-1.5 items-center rounded-lg bg-indigo-600 px-3 pr-1.5 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600">
            Send{" "}
            <span className="bg-white/20 rounded-md px-1 py-0.5 ml-2 [font-size:80%] font-mono">
              CMD + ⏎
            </span>
          </button>
        </Form>
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-5 w-5"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      ></circle>
      <path
        className=""
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 2.21.895 4.21 2.344 5.657l2.217-2.123z"
      ></path>
    </svg>
  );
}
