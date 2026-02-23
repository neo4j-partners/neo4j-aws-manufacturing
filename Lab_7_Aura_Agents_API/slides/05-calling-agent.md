# Calling the Agent

## Make the Request

```http
POST {agent_endpoint}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "input": "What requirements does the HVB_3900 battery have?"
}
```

## Response Structure

```json
{
  "status": "completed",
  "content": [
    {
      "type": "text",
      "text": "The HVB_3900 component has several key requirements..."
    },
    {
      "type": "tool_use",
      "name": "get_component_overview",
      "input": {"component_name": "HVB_3900"}
    }
  ],
  "usage": {
    "input_tokens": 150,
    "output_tokens": 350
  }
}
```

---

[← Previous](04-credentials.md) | [Next: Response Parsing →](06-parsing.md)
