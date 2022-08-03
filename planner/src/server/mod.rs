use std::error::Error;

use tokio::net::TcpListener;

use crate::server::handle::handle_tcp_stream;

mod client_msg;
mod common;
mod handle;
mod server_msg;

pub use server_msg::ServerMessage;

pub async fn serve_ui_forever() -> Result<(), Box<dyn Error>> {
    let listener = TcpListener::bind("127.0.0.1:8000").await?;
    loop {
        match listener.accept().await {
            Ok((tcp_stream, _)) => {
                print!("Connection from {}\n", tcp_stream.peer_addr()?);
                match handle_tcp_stream(tcp_stream).await {
                    Ok(()) => (),
                    Err(err) => println!("Error handling TCP stream: {:?}", err),
                }
            }
            Err(err) => println!("Error accepting TCP stream: {:?}", err),
        }
    }
}
