# Lakehopper Planner

Planned route with four hops between lakes:

![Screenshot of planned route](planner-four-hops.png)

Browser UI:

![Screenshot of browser UI](browser-ui-II.png)

## Server

Websocket server written in Rust using tokio_tungstenite.

**Run**
```bash
cargo run
```

**Build**

```bash
cargo build
```

**Test**

```bash
cargo test
```

## UI

Plain Javascript single page web app.

**Run**
```bash
cd ui && npm run dev
```

**Build**

```bash
cd ui && npm run build
```

**Test**

No >:(