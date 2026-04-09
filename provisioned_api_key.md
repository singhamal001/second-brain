root@vmi2818515:/opt/knowledge-gateway# docker exec -it knowledge-gateway python scripts/provision_client.py --client-code 1234567890 --label codex-rotated
Client provisioned
client_code=1234567890
client_id=d3e70b51-d5bb-4fda-9c43-353ea3c26fd8
api_key=uN30YIbC9ET5nVxKeJggmnSByMEptUPvEoVaScsePX8



curl -i "https://mcp.amaxing.site/mcp" \
  -H "Authorization: Bearer uN30YIbC9ET5nVxKeJggmnSByMEptUPvEoVaScsePX8" \
  -H "X-Client-Code: 1234567890"
  
curl --http1.1 -i "https://mcp.amaxing.site/mcp" \
  -H "Authorization: Bearer uN30YIbC9ET5nVxKeJggmnSByMEptUPvEoVaScsePX8" \
  -H "X-Client-Code: 1234567890"


curl -i -X POST "https://mcp.amaxing.site/mcp" \
  -H "Authorization: Bearer uN30YIbC9ET5nVxKeJggmnSByMEptUPvEoVaScsePX8" \
  -H "X-Client-Code: 1234567890" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

curl --http1.1 -i -X POST "https://mcp.amaxing.site/mcp" \
  -H "Authorization: Bearer uN30YIbC9ET5nVxKeJggmnSByMEptUPvEoVaScsePX8" \
  -H "X-Client-Code: 1234567890" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"init-1","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}'

  curl --http1.1 -i -X POST "https://mcp.amaxing.site/mcp" \
  -H "Authorization: Bearer uN30YIbC9ET5nVxKeJggmnSByMEptUPvEoVaScsePX8" \
  -H "X-Client-Code: 1234567890" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"init-1","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}'

curl --http1.1 -i -X POST "https://mcp.amaxing.site/mcp" \
  -H "Authorization: Bearer uN30YIbC9ET5nVxKeJggmnSByMEptUPvEoVaScsePX8" \
  -H "X-Client-Code: 1234567890" \
  -H "mcp-session-id: df267922216545e8b4f3c20ad3751f0c" \
  -H "mcp-protocol-version: 2025-03-26" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}'

curl --http1.1 -i -X POST "https://mcp.amaxing.site/mcp" \
  -H "Authorization: Bearer uN30YIbC9ET5nVxKeJggmnSByMEptUPvEoVaScsePX8" \
  -H "X-Client-Code: 1234567890" \
  -H "mcp-session-id: df267922216545e8b4f3c20ad3751f0c" \
  -H "mcp-protocol-version: 2025-03-26" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"tools-1","method":"tools/list","params":{}}'
