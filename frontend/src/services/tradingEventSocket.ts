export interface TradingEventPayload {
  event_id: string;
  event_type: string;
  aggregate_id: string;
  payload: Record<string, unknown>;
}

export type TradingEventHandler = (event: TradingEventPayload) => void;

export class TradingEventSocket {
  private socket?: WebSocket;
  private readonly url: string;
  private handler?: TradingEventHandler;

  constructor(url: string) {
    this.url = url;
  }

  connect(handler: TradingEventHandler) {
    this.handler = handler;
    this.socket = new WebSocket(this.url);
    this.socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as TradingEventPayload;
      this.handler?.(event);
    };
  }

  close() {
    this.socket?.close();
    this.socket = undefined;
  }
}
