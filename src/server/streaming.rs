use super::ChatCompletionChunk;
use axum::response::sse::Event;
use flume::Receiver;
use futures::Stream;
use std::{
    future::Future,
    pin::Pin,
    task::{Context, Poll},
};
use tokio::sync::watch;

#[derive(PartialEq)]
pub enum StreamingStatus {
    Uninitialized,
    Started,
    Interrupted,
    Stopped,
}
pub enum ChatResponse {
    InternalError(String),
    ValidationError(String),
    ModelError(String),
    Chunk(ChatCompletionChunk),
    Done, //finish flag
}

pub struct Streamer {
    pub rx: Receiver<ChatResponse>,
    pub status: StreamingStatus,
    pub disconnect_tx: Option<watch::Sender<bool>>,
    pub pending_recv:
        Option<Pin<Box<dyn Future<Output = Result<ChatResponse, flume::RecvError>> + Send>>>,
}

impl Drop for Streamer {
    fn drop(&mut self) {
        if self.status != StreamingStatus::Stopped {
            if let Some(tx) = self.disconnect_tx.as_ref() {
                let _ = tx.send(true);
            }
        }
    }
}

impl Stream for Streamer {
    type Item = Result<Event, axum::Error>;

    fn poll_next(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        if self.status == StreamingStatus::Stopped {
            return Poll::Ready(None);
        }
        if self.pending_recv.is_none() {
            let rx = self.rx.clone();
            self.pending_recv = Some(Box::pin(async move { rx.recv_async().await }));
        }
        match self
            .pending_recv
            .as_mut()
            .expect("pending recv future should be initialized")
            .as_mut()
            .poll(cx)
        {
            Poll::Ready(Ok(resp)) => {
                self.pending_recv = None;
                match resp {
                    ChatResponse::InternalError(e) => {
                        Poll::Ready(Some(Ok(Event::default().data(e))))
                    }
                    ChatResponse::ValidationError(e) => {
                        Poll::Ready(Some(Ok(Event::default().data(e))))
                    }
                    ChatResponse::ModelError(e) => Poll::Ready(Some(Ok(Event::default().data(e)))),
                    ChatResponse::Chunk(response) => {
                        if self.status != StreamingStatus::Started {
                            self.status = StreamingStatus::Started;
                        }
                        Poll::Ready(Some(Event::default().json_data(response)))
                    }
                    ChatResponse::Done => {
                        self.status = StreamingStatus::Stopped;
                        Poll::Ready(Some(Ok(Event::default().data("[DONE]"))))
                    }
                }
            }
            Poll::Ready(Err(_)) => {
                self.pending_recv = None;
                if self.status == StreamingStatus::Started {
                    self.status = StreamingStatus::Interrupted;
                } else {
                    self.status = StreamingStatus::Stopped;
                }
                Poll::Ready(None)
            }
            Poll::Pending => Poll::Pending,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::server::{ChatChoiceChunk, ChatCompletionChunk, Delta};
    use futures::StreamExt;
    use std::time::Duration;

    fn make_chunk() -> ChatCompletionChunk {
        ChatCompletionChunk {
            id: "seq-0".to_string(),
            object: "chat.completion.chunk",
            created: 0,
            model: "test-model".to_string(),
            choices: vec![ChatChoiceChunk {
                index: 0,
                delta: Delta {
                    role: Some("assistant".to_string()),
                    content: Some("hello".to_string()),
                    reasoning_content: None,
                    tool_calls: None,
                },
                finish_reason: None,
                error: None,
            }],
            usage: None,
        }
    }

    #[tokio::test]
    async fn streamer_wakes_without_keepalive_ticks() {
        let (tx, rx) = flume::unbounded();
        let mut streamer = Streamer {
            rx,
            status: StreamingStatus::Uninitialized,
            disconnect_tx: None,
            pending_recv: None,
        };

        tokio::spawn(async move {
            tokio::time::sleep(Duration::from_millis(10)).await;
            tx.send(ChatResponse::Chunk(make_chunk()))
                .expect("chunk send should succeed");
            tx.send(ChatResponse::Done)
                .expect("done send should succeed");
        });

        let first = streamer
            .next()
            .await
            .expect("stream should yield first event");
        let second = streamer
            .next()
            .await
            .expect("stream should yield done event");

        let first_event = first.expect("first event should be valid");
        let second_event = second.expect("second event should be valid");

        let first_text = first_event.to_string();
        let second_text = second_event.to_string();

        assert!(first_text.contains("hello"));
        assert!(second_text.contains("[DONE]"));
    }
}
