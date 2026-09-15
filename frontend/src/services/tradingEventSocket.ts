export interface TradingEventPayload {
  event_id: string;
  event_type: string;
  aggregate_id: string;
  payload: Record<string, unknown>;
}

export type TradingEventHandler = (event: TradingEventPayload) => void;
export type TradingEventStatusHandler = (connected: boolean) => void;

export class TradingEventSocket {
  private socket?: WebSocket;
  private readonly url: string;
  private handler?: TradingEventHandler;
  private statusHandler?: TradingEventStatusHandler;
  private reconnectTimer?: ReturnType<typeof setTimeout>;
  private closed = false;
  private reconnectDelay = 1000;

  constructor(url: string, statusHandler?: TradingEventStatusHandler) {
    this.url = url;
    this.statusHandler = statusHandler;
  }

  connect(handler: TradingEventHandler) {
    this.handler = handler;
    this.closed = false;
    this.open();
  }

  private open() {
    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      this.reconnectDelay = 1000;
      this.statusHandler?.(true);
    };

    this.socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as TradingEventPayload;
      this.handler?.(event);
    };

    this.socket.onerror = () => {
      this.statusHandler?.(false);
    };

    this.socket.onclose = () => {
      this.statusHandler?.(false);
      if (!this.closed) {
        this.reconnectTimer = setTimeout(() => this.open(), this.reconnectDelay);
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
      }
    };
  }

  close() {
    this.closed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.socket?.close();
    this.socket = undefined;
  }
}
