# What You'll Build

## The Knowledge Graph

Your database will contain automotive manufacturing product development data:

| Entity Type | Examples |
|-------------|----------|
| **Products** | R2D2 (autonomous robot vehicle) |
| **Technology Domains** | Electric Powertrain, Chassis, Body, Infotainment |
| **Components** | HVB_3900 (High-Voltage Battery), PDU_1500, ECU_2100 |
| **Requirements** | Engineering specifications (thermal, safety, performance) |
| **Defects & Changes** | Test defects, change proposals with cost/risk |

## Relationships

```
(R2D2)-[:PRODUCT_HAS_DOMAIN]->(Electric Powertrain)
(Electric Powertrain)-[:DOMAIN_HAS_COMPONENT]->(HVB_3900)
(HVB_3900)-[:COMPONENT_HAS_REQ]->(Thermal Management Req)
```

---

[← Previous](01-intro.md) | [Next: Why Graph Databases? →](03-why-graphs.md)
